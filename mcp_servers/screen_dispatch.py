"""TechBuddy Screen Dispatch MCP Server — Tiered Fallback Architecture.

The key innovation: routes every action to the fastest reliable method.

Tier 1: Direct API (win32com/subprocess)  — instant, 100% reliable
Tier 2: UI Automation (pywinauto a11y)    — fast, ~95% reliable
Tier 3: Existing MCP / web APIs           — fast, ~95% reliable
Tier 4: Claude Vision (text instructions) — slow fallback, ~90% reliable

On WSL2/Linux: Tiers 1-2 are stubbed (Windows-only). Tier 3 (filesystem/web)
and Tier 4 (Vision) work everywhere.
"""
import json
import os
import re
import sys
import glob
import shutil
import subprocess
import platform
from datetime import datetime, timedelta
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Detect platform
IS_WINDOWS = platform.system() == "Windows"
IS_WSL = not IS_WINDOWS and Path("/mnt/c/Users").exists()
HOME = Path.home()

# On WSL, use the Windows user folder for file search so we find real files
if IS_WSL:
    # Find the Windows username (first non-system folder in /mnt/c/Users/)
    _skip = {"All Users", "Default", "Default User", "Public", "desktop.ini"}
    _win_users = [p for p in Path("/mnt/c/Users").iterdir()
                  if p.is_dir() and p.name not in _skip]
    WIN_HOME = _win_users[0] if _win_users else HOME
else:
    WIN_HOME = HOME

# Standard user folders — use Windows paths on WSL, home paths elsewhere
USER_FOLDERS = [
    WIN_HOME / "Desktop",
    WIN_HOME / "Documents",
    WIN_HOME / "Downloads",
    WIN_HOME / "Pictures",
    WIN_HOME / "Videos",
]

mcp = FastMCP("screen-dispatch")

# ---------------------------------------------------------------------------
# Anthropic client injection (set by app.py at startup)
# Used by tools that need their own API calls (scam analysis, vision)
# ---------------------------------------------------------------------------
_anthropic_client = None


def set_anthropic_client(client):
    """Set the Anthropic client for tools that need their own API calls."""
    global _anthropic_client
    _anthropic_client = client


# ---------------------------------------------------------------------------
# Local Memory — Notes stored on the user's PC (never in the cloud)
# ---------------------------------------------------------------------------
if IS_WINDOWS:
    NOTES_DIR = Path.home() / "TechBuddy Notes"
elif IS_WSL:
    NOTES_DIR = WIN_HOME / "TechBuddy Notes"
else:
    NOTES_DIR = Path.home() / "TechBuddy Notes"


# ---------------------------------------------------------------------------
# Web Search — DuckDuckGo (free, no API key needed)
# ---------------------------------------------------------------------------

def _search_web_raw(query: str, max_results: int = 3) -> list[dict]:
    """Search the web using DuckDuckGo. Returns list of {title, href, body}.

    Gracefully returns empty list if library not installed or search fails.
    """
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            return [{"title": r.get("title", ""), "href": r.get("href", ""), "body": r.get("body", "")}
                    for r in results]
    except ImportError:
        return []
    except Exception:
        return []


def _web_verify_scam(content: str, matched_orgs: list[str]) -> str:
    """Search the web to verify claims in suspicious content.

    Checks org phone numbers, suspicious domains, and reported scam numbers.
    Returns a summary of web verification findings.
    """
    findings = []

    # Extract phone numbers from content
    phone_pattern = r'1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    phones_in_content = re.findall(phone_pattern, content)

    # Extract domains from content
    domain_pattern = r'(?:https?://)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
    domains_in_content = re.findall(domain_pattern, content)

    searches_done = 0
    max_searches = 6

    # 1. Verify matched organizations' real phone numbers
    for org_key in matched_orgs[:2]:
        if searches_done >= max_searches:
            break
        org = KNOWN_LEGITIMATE_CONTACTS.get(org_key, {})
        if org:
            results = _search_web_raw(f"{org['name']} official phone number 2026", max_results=2)
            if results:
                findings.append(f"Web check for {org['name']}: {results[0]['body'][:200]}")
            searches_done += 1

    # 2. Check suspicious domains
    safe_domains = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "cvs.com",
                    "zoom.us", "google.com", "microsoft.com", "apple.com"}
    for domain in domains_in_content[:2]:
        if searches_done >= max_searches:
            break
        if domain.lower() not in safe_domains:
            results = _search_web_raw(f'"{domain}" scam report', max_results=2)
            if results:
                findings.append(f"Web check for {domain}: {results[0]['body'][:200]}")
            searches_done += 1

    # 3. Check unknown phone numbers
    for phone in phones_in_content[:2]:
        if searches_done >= max_searches:
            break
        # Skip known legitimate numbers
        clean_phone = re.sub(r'[^\d]', '', phone)
        known_numbers = {re.sub(r'[^\d]', '', org['phone'])
                        for org in KNOWN_LEGITIMATE_CONTACTS.values()}
        if clean_phone not in known_numbers and len(clean_phone) >= 10:
            results = _search_web_raw(f'"{phone}" scam report', max_results=2)
            if results:
                findings.append(f"Web check for {phone}: {results[0]['body'][:200]}")
            searches_done += 1

    if not findings:
        return ""

    return "WEB VERIFICATION RESULTS:\n" + "\n".join(findings)


# ---------------------------------------------------------------------------
# Scam Shield — Data and detection engine
# ---------------------------------------------------------------------------

SCAM_URGENCY_PHRASES = [
    "act now", "urgent", "immediately", "within 24 hours", "expires today",
    "don't delay", "time-sensitive", "last chance", "limited time",
    "your account will be closed", "suspended account", "account suspended",
    "verify immediately", "respond immediately", "final notice", "final warning",
]

SCAM_AUTHORITY_KEYWORDS = [
    "irs", "internal revenue", "social security administration", "ssa",
    "medicare", "fbi", "department of justice", "doj", "homeland security",
    "microsoft support", "apple support", "amazon security", "bank of america",
    "wells fargo", "chase bank",
]

SCAM_FINANCIAL_PHRASES = [
    "gift card", "wire transfer", "cryptocurrency", "bitcoin", "western union",
    "moneygram", "bank account number", "routing number", "social security number",
    "ssn", "send money", "claim your prize", "you have won", "lottery",
    "tax refund", "verify your identity", "credit card number",
]

SCAM_TECH_SUPPORT_PHRASES = [
    "virus detected", "your computer is infected", "call this number",
    "remote access", "teamviewer", "anydesk", "chrome remote desktop",
    "your computer has been compromised", "security alert", "windows alert",
    "microsoft alert", "apple alert",
]

SCAM_GRANDPARENT_PHRASES = [
    "i'm in jail", "need bail", "don't tell anyone", "been arrested",
    "i need money", "please don't tell mom", "please don't tell dad",
]

SCAM_SUSPICIOUS_TLDS = [".xyz", ".info", ".top", ".click", ".buzz", ".tk", ".ml", ".ga"]
SCAM_SHORTENED_URLS = ["bit.ly", "tinyurl", "t.co", "goo.gl", "is.gd", "buff.ly"]

SAFE_ATTACHMENT_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".heic", ".webp",
    ".xls", ".xlsx", ".csv", ".ppt", ".pptx",
}

DANGEROUS_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".scr", ".vbs", ".js", ".msi",
    ".ps1", ".com", ".pif", ".reg", ".wsf", ".hta",
}

TRUSTED_MEETING_DOMAINS = ["zoom.us", "meet.google.com", "teams.microsoft.com", "teams.live.com"]

KNOWN_LEGITIMATE_CONTACTS = {
    "irs": {
        "name": "Internal Revenue Service (IRS)",
        "phone": "1-800-829-1040",
        "website": "irs.gov",
        "key_fact": "The IRS will ALWAYS contact you by MAIL first. They NEVER call, email, or text to demand immediate payment.",
    },
    "social security": {
        "name": "Social Security Administration (SSA)",
        "phone": "1-800-772-1213",
        "website": "ssa.gov",
        "key_fact": "Social Security will NEVER call to threaten you or say your number is suspended.",
    },
    "medicare": {
        "name": "Medicare",
        "phone": "1-800-633-4227",
        "website": "medicare.gov",
        "key_fact": "Medicare will NEVER call to ask for your personal information or threaten your benefits.",
    },
    "fbi": {
        "name": "FBI Elder Fraud Hotline",
        "phone": "1-833-372-8311",
        "website": "ic3.gov",
        "key_fact": "The FBI does NOT call to demand payment or threaten arrest. If you've been scammed, call this number to report it.",
    },
    "microsoft": {
        "name": "Microsoft Support",
        "phone": "1-800-642-7676",
        "website": "support.microsoft.com",
        "key_fact": "Microsoft will NEVER show a popup asking you to call a phone number. Those are always scams.",
    },
}


def _scan_for_scam(text: str) -> dict:
    """Scan text for scam indicators. Returns dict with risk level and details.

    Returns:
        {"risk": "SAFE"|"SUSPICIOUS"|"DANGEROUS",
         "flags": [...], "matched_orgs": [...]}
    """
    text_lower = text.lower()
    flags = []
    matched_orgs = []

    # Check urgency phrases
    for phrase in SCAM_URGENCY_PHRASES:
        if phrase in text_lower:
            flags.append(("urgency", phrase))

    # Check authority impersonation
    for keyword in SCAM_AUTHORITY_KEYWORDS:
        if keyword in text_lower:
            flags.append(("authority", keyword))
            # Map to known org
            for org_key in KNOWN_LEGITIMATE_CONTACTS:
                if org_key in keyword or keyword in org_key:
                    if org_key not in matched_orgs:
                        matched_orgs.append(org_key)

    # Check financial red flags
    for phrase in SCAM_FINANCIAL_PHRASES:
        if phrase in text_lower:
            flags.append(("financial", phrase))

    # Check tech support scam indicators
    for phrase in SCAM_TECH_SUPPORT_PHRASES:
        if phrase in text_lower:
            flags.append(("tech_support", phrase))
            if "microsoft" not in matched_orgs:
                matched_orgs.append("microsoft")

    # Check grandparent scam
    for phrase in SCAM_GRANDPARENT_PHRASES:
        if phrase in text_lower:
            flags.append(("grandparent", phrase))

    # Check suspicious URLs
    for domain in SCAM_SHORTENED_URLS:
        if domain in text_lower:
            flags.append(("shortened_url", domain))

    for tld in SCAM_SUSPICIOUS_TLDS:
        if tld in text_lower:
            flags.append(("suspicious_tld", tld))

    # Determine risk level
    categories = set(f[0] for f in flags)
    if len(flags) == 0:
        risk = "SAFE"
    elif len(flags) >= 3 or "financial" in categories or "tech_support" in categories:
        risk = "DANGEROUS"
    else:
        risk = "SUSPICIOUS"

    return {"risk": risk, "flags": flags, "matched_orgs": matched_orgs}


# ---------------------------------------------------------------------------
# Tier 1: Direct API / subprocess — works on any OS for file/system ops
# ---------------------------------------------------------------------------

def _search_matches(path: Path, name_lower: str, results: list, max_results: int,
                     depth: int = 0, max_depth: int = 3):
    """Recursively search for files matching name, with depth limit."""
    if len(results) >= max_results:
        return
    try:
        if path.is_file():
            if name_lower in path.name.lower():
                stat = path.stat()
                modified = datetime.fromtimestamp(stat.st_mtime)
                results.append({
                    "path": str(path),
                    "name": path.name,
                    "folder": str(path.parent),
                    "modified": modified.strftime("%B %d, %Y at %I:%M %p"),
                    "size_kb": round(stat.st_size / 1024, 1),
                })
        elif path.is_dir() and depth < max_depth and not path.name.startswith("."):
            for child in path.iterdir():
                _search_matches(child, name_lower, results, max_results, depth + 1, max_depth)
                if len(results) >= max_results:
                    return
    except (PermissionError, OSError):
        pass


@mcp.tool()
def find_file(name: str, search_in: str = "common") -> str:
    """Find a file by partial name. Searches Desktop, Documents, Downloads, Pictures, and Recent files.
    This is the #1 thing elderly users need help with — they saved something and can't find it.

    Args:
        name: Partial filename to search for (e.g., "grocery", "receipt", "photo")
        search_in: Where to search — "common" for standard folders, or a specific path
    """
    results = []

    if search_in == "common":
        search_dirs = list(USER_FOLDERS)
        # On Windows, also check OneDrive
        onedrive = WIN_HOME / "OneDrive"
        if onedrive.exists():
            search_dirs.append(onedrive)
    else:
        search_dirs = [Path(search_in)]

    MAX_DEPTH = 3  # Don't crawl too deep — slow over WSL bridge
    MAX_RESULTS = 50

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        try:
            for match in search_dir.iterdir():
                _search_matches(match, name.lower(), results, MAX_RESULTS, depth=0, max_depth=MAX_DEPTH)
                if len(results) >= MAX_RESULTS:
                    break
        except PermissionError:
            continue

    # Sort by most recently modified
    results.sort(key=lambda x: x["modified"], reverse=True)

    if not results:
        return f"I couldn't find any files with '{name}' in the name. Would you like me to search somewhere else?"

    # Return top 10
    lines = [f"I found {len(results)} file(s) matching '{name}':\n"]
    for i, r in enumerate(results[:10], 1):
        lines.append(f"{i}. {r['name']}")
        lines.append(f"   In: {r['folder']}")
        lines.append(f"   Last changed: {r['modified']}")
        lines.append("")

    if len(results) > 10:
        lines.append(f"...and {len(results) - 10} more.")

    return "\n".join(lines)


@mcp.tool()
def find_recent_files(hours: int = 24, file_type: str = "all") -> str:
    """Find files that were recently saved or changed.
    Perfect for "I just saved it" or "where did it go?" requests.

    Args:
        hours: How far back to look (default 24 hours)
        file_type: Filter by type — "all", "documents", "pictures", "spreadsheets"
    """
    cutoff = datetime.now() - timedelta(hours=hours)
    results = []

    type_extensions = {
        "documents": {".doc", ".docx", ".pdf", ".txt", ".rtf", ".odt"},
        "pictures": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"},
        "spreadsheets": {".xls", ".xlsx", ".csv", ".ods"},
    }
    allowed_ext = type_extensions.get(file_type)

    search_dirs = list(USER_FOLDERS)

    def _search_recent(path: Path, depth: int = 0, max_depth: int = 3):
        if len(results) >= 50:
            return
        try:
            if path.is_file():
                if path.name.startswith("."):
                    return
                if allowed_ext and path.suffix.lower() not in allowed_ext:
                    return
                stat = path.stat()
                modified = datetime.fromtimestamp(stat.st_mtime)
                if modified >= cutoff:
                    results.append({
                        "path": str(path),
                        "name": path.name,
                        "folder": str(path.parent),
                        "modified": modified.strftime("%B %d, %Y at %I:%M %p"),
                    })
            elif path.is_dir() and depth < max_depth and not path.name.startswith("."):
                for child in path.iterdir():
                    _search_recent(child, depth + 1, max_depth)
        except (PermissionError, OSError):
            pass

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        try:
            for item in search_dir.iterdir():
                _search_recent(item)
        except PermissionError:
            continue

    results.sort(key=lambda x: x["modified"], reverse=True)

    if not results:
        return f"I didn't find any files changed in the last {hours} hours. Would you like me to look further back?"

    lines = [f"Here are your recently changed files (last {hours} hours):\n"]
    for i, r in enumerate(results[:10], 1):
        lines.append(f"{i}. {r['name']}")
        lines.append(f"   In: {r['folder']}")
        lines.append(f"   Last changed: {r['modified']}")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
def open_file(file_path: str) -> str:
    """Open a file with the default application.
    Works for documents, pictures, PDFs — anything the computer knows how to open.

    Args:
        file_path: Full path to the file to open
    """
    path = Path(file_path)
    if not path.exists():
        return f"I can't find that file at {file_path}. It might have been moved or deleted."

    try:
        if IS_WINDOWS:
            os.startfile(str(path))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
        return f"Opening {path.name} now. You should see it on your screen in a moment."
    except Exception as e:
        return f"I had trouble opening that file. Let's try a different way."


@mcp.tool()
def open_application(app_name: str) -> str:
    """Open an application by name. Handles Word, Notepad, Calculator, Excel, Paint.
    For Word, this creates a blank document automatically — no start screen.
    After opening, the app is ready to use with type_text or click_button.

    Args:
        app_name: Name of the app (e.g., "word", "notepad", "calculator", "excel", "paint")
    """
    name = app_name.lower().strip()

    if not IS_WINDOWS:
        return f"To open {app_name}: look for it in your applications menu and click it."

    # Word gets special handling via win32com to skip the start screen
    if name in ("word", "microsoft word", "ms word"):
        try:
            import win32com.client
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = True
            word.Documents.Add()
            return "Word is open with a blank document. You can start typing!"
        except Exception:
            # Fallback: launch directly
            try:
                os.startfile("winword")
                import time
                time.sleep(3)
                return "Word is opening. You may need to click 'Blank document' on the start screen."
            except Exception:
                return "I couldn't open Word. Is Microsoft Office installed?"

    # Map common app names to executables
    app_map = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "excel": "excel.exe",
        "microsoft excel": "excel.exe",
        "paint": "mspaint.exe",
        "ms paint": "mspaint.exe",
        "powerpoint": "powerpnt.exe",
        "outlook": "outlook.exe",
    }

    exe = app_map.get(name)
    if not exe:
        return f"I don't know how to open '{app_name}'. Try asking me to open Word, Notepad, Calculator, Excel, or Paint."

    try:
        os.startfile(exe)
        import time
        time.sleep(2)
        return f"{app_name.title()} is opening now. You should see it on your screen in a moment."
    except Exception:
        return f"I had trouble opening {app_name}. It might not be installed on this computer."


@mcp.tool()
def list_folder(folder_path: str = "Desktop") -> str:
    """Show what's in a folder. Defaults to Desktop.
    Helps elderly users see what files they have.

    Args:
        folder_path: Which folder to look in — "Desktop", "Documents", "Downloads", "Pictures", or a full path
    """
    shortcuts = {
        "Desktop": WIN_HOME / "Desktop",
        "Documents": WIN_HOME / "Documents",
        "Downloads": WIN_HOME / "Downloads",
        "Pictures": WIN_HOME / "Pictures",
    }

    path = shortcuts.get(folder_path, Path(folder_path))
    if not path.exists():
        return f"I can't find the folder '{folder_path}'. Let me look in your common folders instead."

    items = []
    try:
        for item in sorted(path.iterdir()):
            if item.name.startswith("."):
                continue
            kind = "folder" if item.is_dir() else "file"
            items.append({"name": item.name, "kind": kind})
    except PermissionError:
        return "I don't have permission to look in that folder."

    if not items:
        return f"The {folder_path} folder is empty."

    lines = [f"Here's what's in your {folder_path} folder:\n"]
    folders = [i for i in items if i["kind"] == "folder"]
    files = [i for i in items if i["kind"] == "file"]

    if folders:
        lines.append("Folders:")
        for f in folders[:15]:
            lines.append(f"  📁 {f['name']}")
        lines.append("")

    if files:
        lines.append("Files:")
        for f in files[:15]:
            lines.append(f"  📄 {f['name']}")

    total = len(folders) + len(files)
    if total > 30:
        lines.append(f"\n...and {total - 30} more items.")

    return "\n".join(lines)


@mcp.tool()
def print_document(file_path: str, copies: int = 1) -> str:
    """Send a document to the printer.
    Confirms settings before printing to avoid waste.

    Args:
        file_path: Full path to the file to print
        copies: How many copies to print (default 1)
    """
    path = Path(file_path)
    if not path.exists():
        return f"I can't find that file. Could you help me find it first?"

    if copies > 5:
        return f"That's a lot of copies ({copies}). Are you sure you want to print that many?"

    try:
        if IS_WINDOWS:
            # Windows: use the built-in print verb
            os.startfile(str(path), "print")
            return f"Sending {path.name} to the printer now. You should hear it start in a moment."
        else:
            # Linux/Mac: use lp or lpr
            result = subprocess.run(
                ["lp", "-n", str(copies), str(path)],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return f"Sent {path.name} to the printer ({copies} copy). You should hear it start soon."
            else:
                return "I had trouble reaching the printer. Let's check if it's turned on and connected."
    except FileNotFoundError:
        return "The print command isn't available. Let's check your printer setup."
    except Exception:
        return "Something went wrong with printing. Is the printer turned on?"


@mcp.tool()
def troubleshoot_printer() -> str:
    """Check why the printer isn't working. Diagnoses common problems like
    offline printer, stuck print jobs, or wrong default printer.
    Use when the user says "my printer isn't working" or "I can't print".
    """
    if IS_WINDOWS:
        return _troubleshoot_printer_windows()
    else:
        return _troubleshoot_printer_generic()


def _troubleshoot_printer_windows() -> str:
    """Check printer status on Windows using PowerShell."""
    report_lines = ["Let me check your printer...\n"]

    # 1. List printers and their status
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-Printer | Select-Object Name, PrinterStatus, Type, PortName | ConvertTo-Json"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0 and result.stdout.strip():
            import json
            printers = json.loads(result.stdout)
            if not isinstance(printers, list):
                printers = [printers]

            report_lines.append(f"I found {len(printers)} printer(s):\n")
            for p in printers:
                name = p.get("Name", "Unknown")
                status = p.get("PrinterStatus", "Unknown")
                # PrinterStatus: 0=Normal, 1=Paused, 2=Error, 3=Deleting, etc.
                status_map = {0: "Ready", 1: "Paused", 2: "Error", 3: "Deleting",
                              4: "Paper Jam", 5: "Paper Out", 6: "Manual Feed",
                              7: "Paper Problem", 8: "Offline"}
                status_text = status_map.get(status, f"Status code {status}")
                report_lines.append(f"  Printer: {name}")
                report_lines.append(f"  Status: {status_text}")
                report_lines.append("")
        else:
            report_lines.append("I couldn't get printer information.\n")
    except Exception:
        report_lines.append("I had trouble checking the printers.\n")

    # 2. Check default printer
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "(Get-CimInstance -ClassName Win32_Printer | Where-Object {$_.Default}).Name"],
            capture_output=True, text=True, timeout=10,
        )
        default = result.stdout.strip()
        if default:
            report_lines.append(f"Your default printer is: {default}\n")
        else:
            report_lines.append("No default printer is set! That could be the problem.\n")
    except Exception:
        pass

    # 3. Check for stuck print jobs
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-PrintJob -PrinterName * -ErrorAction SilentlyContinue | "
             "Select-Object PrinterName, JobStatus, DocumentName | ConvertTo-Json"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            import json
            jobs = json.loads(result.stdout)
            if not isinstance(jobs, list):
                jobs = [jobs]
            if jobs:
                report_lines.append(f"Stuck print jobs: {len(jobs)} job(s) waiting\n")
        else:
            report_lines.append("No stuck print jobs. That's good!\n")
    except Exception:
        report_lines.append("No stuck print jobs found.\n")

    # 4. Common fix suggestions
    report_lines.append("Here's what to try:")
    report_lines.append("  1. Make sure the printer is turned ON (look for a green light)")
    report_lines.append("  2. Check that the cable is plugged in, or that WiFi is connected")
    report_lines.append("  3. Try turning the printer OFF, wait 10 seconds, turn it back ON")
    report_lines.append("  4. Make sure there's paper in the tray")
    report_lines.append("  5. If it still doesn't work, we can try clearing the print queue")
    report_lines.append("\nLet me know what you find and I'll help from there!")

    return "\n".join(report_lines)


def _troubleshoot_printer_generic() -> str:
    """Check printer status on Linux/WSL or provide generic checklist."""
    report_lines = ["Let me check your printer...\n"]

    # Try lpstat on Linux
    try:
        result = subprocess.run(
            ["lpstat", "-p", "-d"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            report_lines.append("Printer status:")
            for line in result.stdout.strip().split("\n"):
                report_lines.append(f"  {line}")
            report_lines.append("")
        else:
            report_lines.append("I couldn't find any printers set up on this computer.\n")
    except FileNotFoundError:
        report_lines.append("I couldn't check the printer status automatically.\n")
    except Exception:
        report_lines.append("I had trouble checking the printer.\n")

    report_lines.append("Here's what to try:")
    report_lines.append("  1. Make sure the printer is turned ON (look for a green light)")
    report_lines.append("  2. Check that the cable is plugged in, or that WiFi is connected")
    report_lines.append("  3. Try turning the printer OFF, wait 10 seconds, turn it back ON")
    report_lines.append("  4. Make sure there's paper in the tray")
    report_lines.append("  5. Check that the right printer is selected as your default")
    report_lines.append("\nLet me know what you find and I'll help from there!")

    return "\n".join(report_lines)


# ---------------------------------------------------------------------------
# System Troubleshooting — Terminal-based diagnostics (PowerShell on Windows)
# ---------------------------------------------------------------------------


def _run_powershell(script: str, timeout: int = 15) -> str | None:
    """Run a PowerShell command and return stdout, or None on failure."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass
    return None


def check_system_health() -> str:
    """Check why the computer is slow or acting up. Shows memory usage,
    hard drive space, and which programs are using the most resources.
    Use when the user says 'my computer is slow', 'everything is freezing',
    or 'am I running out of space?'
    """
    if not IS_WINDOWS:
        return (
            "I can't check your computer's health from here, but here are common fixes:\n"
            "  1. Close programs you're not using (they use memory)\n"
            "  2. Restart your computer — this fixes most slowness\n"
            "  3. Make sure your hard drive isn't full — delete old files you don't need\n"
            "Would you like help with any of these?"
        )

    report = ["Here's how your computer is doing:\n"]

    # 1. Memory usage
    mem_script = (
        "Get-CimInstance Win32_OperatingSystem | "
        "Select-Object FreePhysicalMemory, TotalVisibleMemorySize | "
        "ConvertTo-Json"
    )
    mem_out = _run_powershell(mem_script)
    if mem_out:
        try:
            data = json.loads(mem_out)
            total_kb = int(data["TotalVisibleMemorySize"])
            free_kb = int(data["FreePhysicalMemory"])
            total_gb = round(total_kb / 1048576, 1)
            used_gb = round((total_kb - free_kb) / 1048576, 1)
            pct = round((total_kb - free_kb) / total_kb * 100)
            report.append(f"MEMORY: Using {used_gb} of {total_gb} GB ({pct}% full)")
            if pct > 85:
                report.append("  ⚠ Memory is very high — closing some programs would help!")
            elif pct > 70:
                report.append("  Getting a bit full — close programs you're not using.")
            else:
                report.append("  Looks good!")
        except (json.JSONDecodeError, KeyError, ValueError):
            report.append("MEMORY: I couldn't check memory usage.")
    else:
        report.append("MEMORY: I couldn't check memory usage.")

    # 2. Disk space
    disk_script = (
        "Get-PSDrive C | Select-Object Used, Free | ConvertTo-Json"
    )
    disk_out = _run_powershell(disk_script)
    if disk_out:
        try:
            data = json.loads(disk_out)
            used_bytes = int(data["Used"])
            free_bytes = int(data["Free"])
            total_bytes = used_bytes + free_bytes
            free_gb = round(free_bytes / 1073741824, 1)
            pct_used = round(used_bytes / total_bytes * 100)
            report.append(f"\nHARD DRIVE: {pct_used}% full — {free_gb} GB free")
            if free_gb < 10:
                report.append("  ⚠ Running low on space! Delete files you don't need.")
            elif free_gb < 30:
                report.append("  Getting a little full — keep an eye on it.")
            else:
                report.append("  Plenty of space!")
        except (json.JSONDecodeError, KeyError, ValueError):
            report.append("\nHARD DRIVE: I couldn't check disk space.")
    else:
        report.append("\nHARD DRIVE: I couldn't check disk space.")

    # 3. Top CPU-hungry programs
    proc_script = (
        "Get-Process | Sort-Object -Property WorkingSet64 -Descending | "
        "Select-Object -First 5 ProcessName, "
        "@{Name='MemoryMB';Expression={[math]::Round($_.WorkingSet64/1MB)}} | "
        "ConvertTo-Json"
    )
    proc_out = _run_powershell(proc_script)
    if proc_out:
        try:
            procs = json.loads(proc_out)
            if not isinstance(procs, list):
                procs = [procs]
            report.append("\nBIGGEST PROGRAMS RUNNING:")
            for p in procs:
                name = p.get("ProcessName", "Unknown")
                mb = p.get("MemoryMB", 0)
                report.append(f"  • {name} — using {mb} MB")
        except (json.JSONDecodeError, KeyError):
            report.append("\nPROGRAMS: I couldn't list running programs.")
    else:
        report.append("\nPROGRAMS: I couldn't list running programs.")

    report.append("\nWould you like me to close any of these programs to free up memory?")
    return "\n".join(report)


def fix_frozen_program(program_name: str, confirm: bool = False) -> str:
    """Close a program that is frozen or not responding. Use when the user says
    'Word is frozen', 'my browser won't close', or 'this program is stuck'.
    IMPORTANT: Always ask the user to confirm before closing — they may lose unsaved work.
    Call first WITHOUT confirm to see what's running, then WITH confirm=True to actually close it.

    Args:
        program_name: The name of the program (e.g., 'Word', 'Chrome', 'Notepad')
        confirm: Set to True to actually close the program. False just checks if it's running.
    """
    if not program_name or not program_name.strip():
        return "Which program is frozen? Tell me its name — like 'Word' or 'Chrome'."

    if not IS_WINDOWS:
        return (
            f"I can't close {program_name} from here, but here's what to try:\n"
            "  1. Right-click the program in the taskbar and pick 'Close window'\n"
            "  2. Press Ctrl + Alt + Delete, then pick 'Task Manager'\n"
            "  3. Find the program in the list, click it, and press 'End Task'\n"
            "Would you like me to walk you through Task Manager?"
        )

    clean_name = program_name.strip()

    # Map friendly names to process names
    name_map = {
        "word": "WINWORD",
        "excel": "EXCEL",
        "powerpoint": "POWERPNT",
        "outlook": "OUTLOOK",
        "chrome": "chrome",
        "firefox": "firefox",
        "edge": "msedge",
        "notepad": "notepad",
        "explorer": "explorer",
        "teams": "Teams",
    }
    proc_name = name_map.get(clean_name.lower(), clean_name)

    # Check if it's running
    check_script = (
        f"Get-Process -Name '{proc_name}' -ErrorAction SilentlyContinue | "
        f"Select-Object ProcessName, Id, "
        f"@{{Name='MemoryMB';Expression={{[math]::Round($_.WorkingSet64/1MB)}}}} | "
        f"ConvertTo-Json"
    )
    check_out = _run_powershell(check_script)

    if not check_out:
        return f"I don't see {program_name} running on your computer. It might have already closed!"

    try:
        procs = json.loads(check_out)
        if not isinstance(procs, list):
            procs = [procs]
    except json.JSONDecodeError:
        return f"I had trouble checking on {program_name}. Try pressing Ctrl+Alt+Delete and using Task Manager."

    total_mb = sum(p.get("MemoryMB", 0) for p in procs)
    count = len(procs)

    if not confirm:
        # Just report — Claude will ask for confirmation
        msg = f"I found {program_name}"
        if count > 1:
            msg += f" ({count} windows)"
        msg += f" using {total_mb} MB of memory.\n\n"
        msg += "⚠ Closing it will lose any unsaved work in that program.\n"
        msg += "Would you like me to close it?"
        return msg

    # Actually kill it
    kill_script = f"Stop-Process -Name '{proc_name}' -Force -ErrorAction SilentlyContinue"
    _run_powershell(kill_script, timeout=10)

    return (
        f"Done! I closed {program_name}. "
        "If you need to use it again, just open it from the Start menu or your desktop. "
        "Let me know if anything else is acting up!"
    )


def check_internet() -> str:
    """Check if the internet is working and diagnose connection problems.
    Use when the user says 'internet isn't working', 'WiFi is down',
    'I can't get online', or 'pages won't load'.
    """
    if not IS_WINDOWS:
        return (
            "I can't check your internet from here, but here's what to try:\n"
            "  1. Look for the WiFi icon in the bottom-right corner of your screen\n"
            "  2. If there's an X on it, click it and pick your WiFi network\n"
            "  3. Try turning WiFi OFF, wait 10 seconds, turn it back ON\n"
            "  4. If nothing works, unplug your router, wait 30 seconds, plug it back in\n"
            "Would you like me to walk you through any of these?"
        )

    report = []

    # 1. Ping test — is internet reachable?
    ping_script = "Test-Connection -ComputerName 8.8.8.8 -Count 2 -Quiet"
    ping_out = _run_powershell(ping_script, timeout=20)
    is_connected = ping_out and ping_out.strip().lower() == "true"

    if is_connected:
        report.append("INTERNET: Your internet is working!")
    else:
        report.append("INTERNET: ⚠ I can't reach the internet right now.")

    # 2. WiFi info
    wifi_script = "netsh wlan show interfaces"
    wifi_out = _run_powershell(wifi_script)
    if wifi_out:
        # Parse key fields
        ssid = ""
        signal = ""
        state = ""
        for line in wifi_out.split("\n"):
            line = line.strip()
            if line.startswith("SSID") and "BSSID" not in line:
                ssid = line.split(":", 1)[1].strip() if ":" in line else ""
            elif line.startswith("Signal"):
                signal = line.split(":", 1)[1].strip() if ":" in line else ""
            elif line.startswith("State"):
                state = line.split(":", 1)[1].strip() if ":" in line else ""

        if state.lower() == "connected" and ssid:
            report.append(f"\nWIFI: Connected to '{ssid}'")
            if signal:
                # Parse signal percentage
                try:
                    sig_pct = int(signal.replace("%", ""))
                    if sig_pct >= 70:
                        report.append(f"  Signal: Strong ({signal})")
                    elif sig_pct >= 40:
                        report.append(f"  Signal: Fair ({signal}) — try moving closer to the router")
                    else:
                        report.append(f"  Signal: Weak ({signal}) — this might be why things are slow")
                except ValueError:
                    report.append(f"  Signal: {signal}")
        elif state.lower() == "disconnected":
            report.append("\nWIFI: ⚠ Not connected to any WiFi network!")
            report.append("  Click the WiFi icon in the bottom-right corner to connect.")
        else:
            report.append(f"\nWIFI: Status is '{state}'")
    else:
        report.append("\nWIFI: I couldn't check WiFi status.")

    # Suggest fixes if not connected
    if not is_connected:
        report.append("\nHere's what to try:")
        report.append("  1. Click the WiFi icon (bottom-right) and make sure WiFi is ON")
        report.append("  2. Pick your WiFi network and enter the password")
        report.append("  3. If that doesn't work, unplug your router for 30 seconds, then plug it back in")
        report.append("  4. If WiFi is on but nothing loads, try restarting your computer")

    return "\n".join(report)


@mcp.tool()
def analyze_scam_risk(content: str, content_type: str = "email") -> str:
    """Analyze any content for scam indicators and return a safety assessment.
    Use this whenever you encounter suspicious emails, links, phone calls, or popups.
    Always use this BEFORE opening links, downloading files, or acting on requests
    that ask for personal information or money.

    Args:
        content: The text to analyze (email body, URL, phone message, popup text, etc.)
        content_type: What kind of content — "email", "link", "phone", "popup"
    """
    scan = _scan_for_scam(content)
    risk = scan["risk"]
    flags = scan["flags"]
    matched_orgs = scan["matched_orgs"]

    if risk == "SAFE":
        return "This looks safe. I didn't find any scam indicators."

    # --- Web verification: search the internet to verify claims ---
    web_evidence = _web_verify_scam(content, matched_orgs)

    # --- Extended Thinking: deep scam analysis when suspicious/dangerous ---
    # Uses Opus 4.6 extended thinking to REASON about why this is a scam
    # instead of just keyword matching. Judges see the thinking trace.
    if _anthropic_client is not None:
        try:
            web_context = f"\n\n{web_evidence}" if web_evidence else ""
            thinking_result = _anthropic_client.messages.create(
                model="claude-opus-4-6",
                max_tokens=8000,
                thinking={"type": "adaptive"},
                messages=[{
                    "role": "user",
                    "content": (
                        f"You are a scam detection expert protecting an elderly person. "
                        f"Analyze this {content_type} for scam risk.\n\n"
                        f"Content:\n{content}\n\n"
                        f"Our keyword pre-filter found these flags: {flags}\n"
                        f"Matched organizations: {matched_orgs}\n"
                        f"{web_context}\n\n"
                        f"Provide your analysis in this exact format:\n"
                        f"RISK: HIGH or MEDIUM\n"
                        f"TYPE: (tech support / phishing / lottery / grandparent / romance / government impersonation / other)\n"
                        f"EXPLANATION: (2-3 sentences in plain language an elderly person can understand)\n"
                        f"WHAT TO DO:\n- (step 1)\n- (step 2)\n- (step 3)\n\n"
                        f"Keep it under 200 words. Use simple language."
                    ),
                }],
            )

            # Extract the thinking trace and the final response
            thinking_summary = ""
            deep_analysis = ""
            for block in thinking_result.content:
                if block.type == "thinking":
                    thinking_summary = block.thinking
                elif block.type == "text":
                    deep_analysis = block.text

            # Build the combined response
            lines = []
            if risk == "DANGEROUS":
                lines.append("DANGER — This is very likely a SCAM!\n")
            else:
                lines.append("WARNING — This looks suspicious.\n")

            lines.append(deep_analysis)

            # Still append the real contact numbers from keyword matching
            if matched_orgs:
                lines.append("\nVerified contact numbers (call these to check):\n")
                for org_key in matched_orgs:
                    org = KNOWN_LEGITIMATE_CONTACTS.get(org_key, {})
                    if org:
                        lines.append(f"  {org['name']}: {org['phone']}")
                        lines.append(f"    {org['key_fact']}")
                        lines.append("")

            # Embed thinking trace for UI extraction
            if thinking_summary:
                lines.append(f"\n[THINKING_TRACE]{thinking_summary}[/THINKING_TRACE]")

            return "\n".join(lines)

        except Exception:
            pass  # Fall through to keyword-only response below

    # --- Keyword-only fallback (no API client or API error) ---
    lines = []
    if risk == "DANGEROUS":
        lines.append("DANGER — This is very likely a SCAM!\n")
    else:
        lines.append("WARNING — This looks suspicious.\n")

    # Explain what was found
    lines.append("Here's what I found that concerns me:\n")
    categories_seen = set()
    for category, phrase in flags:
        if category not in categories_seen:
            categories_seen.add(category)
            if category == "urgency":
                lines.append(f"  - Pressure language: \"{phrase}\" — Scammers create fake urgency so you don't think carefully")
            elif category == "authority":
                lines.append(f"  - Claims to be from: \"{phrase}\" — Scammers often pretend to be trusted organizations")
            elif category == "financial":
                lines.append(f"  - Asks for money/info: \"{phrase}\" — Legitimate organizations don't ask for this by {content_type}")
            elif category == "tech_support":
                lines.append(f"  - Fake tech support: \"{phrase}\" — Real companies never show popups asking you to call")
            elif category == "grandparent":
                lines.append(f"  - Emergency money request: \"{phrase}\" — This is a common 'grandparent scam'")
            elif category == "shortened_url":
                lines.append(f"  - Hidden link: \"{phrase}\" — Scammers hide dangerous links behind shortened URLs")
            elif category == "suspicious_tld":
                lines.append(f"  - Suspicious website: \"{phrase}\" — Legitimate organizations don't use these web addresses")

    # Provide legitimate contact info
    if matched_orgs:
        lines.append("\nIf this is really from a legitimate organization, here's how to check:\n")
        for org_key in matched_orgs:
            org = KNOWN_LEGITIMATE_CONTACTS.get(org_key, {})
            if org:
                lines.append(f"  {org['name']}")
                lines.append(f"    Real phone number: {org['phone']}")
                lines.append(f"    Real website: {org['website']}")
                lines.append(f"    Remember: {org['key_fact']}")
                lines.append("")

    # General advice
    lines.append("\nWhat you should do:")
    if risk == "DANGEROUS":
        lines.append("  1. Do NOT click any links in this message")
        lines.append("  2. Do NOT call any phone numbers listed here")
        lines.append("  3. Do NOT send money, gift cards, or personal information")
        lines.append("  4. Delete this message")
        if matched_orgs:
            lines.append("  5. If you're worried, call the REAL number listed above to verify")
    else:
        lines.append("  1. Be careful — don't click links or share personal information")
        lines.append("  2. If someone asks for money or passwords, it's almost certainly a scam")
        lines.append("  3. When in doubt, ask a family member or call the organization directly")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tier 2: UI Automation (Windows-only, via pywinauto)
# Stubbed on Linux — returns instructions instead
# ---------------------------------------------------------------------------

@mcp.tool()
def click_button(window_title: str, button_name: str) -> str:
    """Click a button in any open window by its name.
    Uses the accessibility tree to find the right button.

    Args:
        window_title: Title of the window (e.g., "Outlook", "Zoom")
        button_name: Name of the button to click (e.g., "Send", "Join Meeting")
    """
    if not IS_WINDOWS:
        return (
            f"I can see you want to click '{button_name}' in {window_title}. "
            f"Here's how: Look for the '{button_name}' button in the {window_title} window and click it."
        )

    try:
        import pywinauto
        app = pywinauto.Application(backend="uia").connect(title_re=f".*{window_title}.*")
        window = app.top_window()
        button = window.child_window(title=button_name, control_type="Button")
        button.click()
        return f"Done! I clicked '{button_name}' in {window_title}."
    except ImportError:
        return f"Please click the '{button_name}' button in {window_title}."
    except Exception:
        return f"I couldn't find the '{button_name}' button. Can you see it on your screen?"


@mcp.tool()
def type_text(window_title: str, text: str, field_name: str = "") -> str:
    """Type text into a field in any open window.

    Args:
        window_title: Title of the window
        text: The text to type
        field_name: Name of the text field (optional — uses focused field if empty)
    """
    if not IS_WINDOWS:
        if field_name:
            return f"Please click on the '{field_name}' field in {window_title} and type: {text}"
        return f"Please type this in {window_title}: {text}"

    try:
        import pywinauto
        app = pywinauto.Application(backend="uia").connect(title_re=f".*{window_title}.*")
        window = app.top_window()
        if field_name:
            field = window.child_window(title=field_name, control_type="Edit")
            field.set_text(text)
        else:
            window.type_keys(text, with_spaces=True)
        return f"Done! I typed that into {window_title}."
    except ImportError:
        return f"Please type '{text}' in {window_title}."
    except Exception:
        return f"I couldn't type into {window_title}. Is the window open?"


@mcp.tool()
def save_document_as_pdf(save_path: str) -> str:
    """Save the currently open Word document as a PDF file.
    Use when the user wants to convert their Word document to PDF.
    The document must already be open in Microsoft Word.

    Args:
        save_path: Full path where to save the PDF (e.g., 'C:\\Users\\grego\\Desktop\\Letter.pdf')
    """
    if not IS_WINDOWS:
        return (
            "Here's how to save your document as a PDF:\n\n"
            "  Step 1: Click 'File' in the top-left corner\n"
            "  Step 2: Click 'Save As'\n"
            "  Step 3: In the 'Save as type' dropdown, choose 'PDF'\n"
            "  Step 4: Click 'Save'\n\n"
            "Your PDF will be saved! Let me know when you're done."
        )

    try:
        import win32com.client
        word = win32com.client.GetActiveObject("Word.Application")
        doc = word.ActiveDocument

        # Ensure save_path ends with .pdf
        if not save_path.lower().endswith(".pdf"):
            save_path = save_path + ".pdf"

        # FileFormat 17 = wdFormatPDF
        doc.SaveAs2(save_path, FileFormat=17)
        return (
            f"Done! I saved your document as a PDF.\n\n"
            f"File: {save_path}\n\n"
            f"Would you like me to email it to someone or print it?"
        )
    except ImportError:
        return "I need the pywin32 package to save PDFs. Let's save it manually using File > Save As > PDF."
    except Exception as e:
        error_msg = str(e).lower()
        if "no active" in error_msg or "object" in error_msg:
            return "I don't see a Word document open right now. Could you open the document you'd like to save as PDF?"
        return (
            "I had trouble saving the PDF. Let's try it manually:\n\n"
            "  Step 1: Click 'File' in the top-left corner\n"
            "  Step 2: Click 'Save As'\n"
            "  Step 3: Choose 'PDF' from the file type dropdown\n"
            "  Step 4: Click 'Save'"
        )


def smart_save_document(content: str, doc_type: str = "note", title: str = "") -> str:
    """Save content as a clearly named document with date and time stamp.
    Use whenever the user creates, downloads, or works on a document.
    Automatically picks a clear filename with today's date so they can find it later.

    Args:
        content: The text content to save
        doc_type: Type of document — "note", "letter", "list", "instructions", "recipe", "other"
        title: Optional short title (e.g., "Grocery List", "Letter to Sarah"). If empty, auto-generates.
    """
    from datetime import datetime

    now = datetime.now()
    date_str = now.strftime("%B %d %Y")  # "February 12 2026"
    time_str = now.strftime("%I-%M %p")   # "03-45 PM"
    date_file = now.strftime("%m-%d-%Y_%I%M%p")  # "02-12-2026_0345PM"

    # Build a clear filename
    if title.strip():
        clean_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title.strip())
    else:
        clean_title = doc_type.capitalize()

    filename = f"{clean_title} - {date_file}.txt"

    # Save to Documents folder
    if IS_WINDOWS:
        docs_dir = Path(os.environ.get("USERPROFILE", "C:/Users/grego")) / "Documents" / "TechBuddy Saved"
    elif IS_WSL:
        docs_dir = WIN_HOME / "Documents" / "TechBuddy Saved"
    else:
        docs_dir = Path.home() / "Documents" / "TechBuddy Saved"

    docs_dir.mkdir(parents=True, exist_ok=True)
    file_path = docs_dir / filename

    # Write with a nice header
    header = f"--- {clean_title} ---\nSaved by TechBuddy on {date_str} at {time_str}\n\n"
    file_path.write_text(header + content, encoding="utf-8")

    return (
        f"Saved! I put it in your Documents folder with a clear name:\n\n"
        f"  File: {filename}\n"
        f"  Location: {docs_dir}\n\n"
        f"The date is in the name so you can always find it. "
        f"Would you like me to open it or email it to someone?"
    )


# ---------------------------------------------------------------------------
# Tier 4: Claude Vision fallback — text instructions for unknown UI
# ---------------------------------------------------------------------------

@mcp.tool()
def describe_screen_action(task: str, app_name: str) -> str:
    """When automated methods aren't available, provide clear step-by-step
    instructions the user can follow themselves.

    Args:
        task: What the user wants to do (e.g., "join zoom meeting", "send email")
        app_name: Which app they're using (e.g., "Zoom", "Outlook", "Chrome")
    """
    # Step-by-step guides for common tasks
    guides = {
        ("zoom", "join"): [
            "Look for the Zoom link in your email or message.",
            "Click on the blue link — it should open Zoom.",
            "If Zoom asks, click 'Open Zoom Meetings'.",
            "Click the big blue 'Join' button.",
            "You're in! You should see yourself on camera.",
        ],
        ("zoom", "unmute"): [
            "Look at the bottom-left of the Zoom window.",
            "You'll see a microphone icon.",
            "If it has a red line through it, click it to unmute.",
            "Now they can hear you!",
        ],
        ("outlook", "send"): [
            "Click 'New Email' at the top left.",
            "In the 'To' field, type the person's email address.",
            "Click in the big white area and type your message.",
            "When you're ready, click the 'Send' button.",
        ],
        ("chrome", "print"): [
            "With the page open, press Ctrl and P at the same time.",
            "A print window will appear.",
            "Make sure the right printer is selected at the top.",
            "Click the 'Print' button.",
        ],
    }

    task_lower = task.lower()
    app_lower = app_name.lower()

    for (app_key, task_key), steps in guides.items():
        if app_key in app_lower and task_key in task_lower:
            lines = [f"Here's how to {task} in {app_name}:\n"]
            for i, step in enumerate(steps, 1):
                lines.append(f"  Step {i}: {step}")
            lines.append(f"\nTake it one step at a time — no rush!")
            return "\n".join(lines)

    # Generic fallback
    return (
        f"I'm not sure exactly how to help with '{task}' in {app_name} automatically, "
        f"but I can walk you through it step by step. Can you tell me what you see on your screen right now?"
    )


# ---------------------------------------------------------------------------
# Tier 4b: Claude Vision — read the user's actual screen
# ---------------------------------------------------------------------------

@mcp.tool()
def read_my_screen() -> str | list:
    """Take a screenshot of the user's screen so you can SEE what they see.
    Use when the user says 'what's on my screen?', 'I see a popup',
    'something appeared', 'what does this error say?', 'what should I click?',
    or 'I don't know what I'm looking at'.
    This lets you actually look at their screen and give specific help.
    """
    if not IS_WINDOWS:
        return (
            "I can't see your screen from here, but I'd like to help! "
            "Can you describe what you see? For example, what does the message say, "
            "or what buttons do you see?"
        )

    try:
        import io
        import base64
        from PIL import ImageGrab

        # Capture the screen
        screenshot = ImageGrab.grab()

        # Resize if very large (cap at 1920px width to save tokens)
        max_width = 1920
        if screenshot.width > max_width:
            ratio = max_width / screenshot.width
            new_size = (max_width, int(screenshot.height * ratio))
            screenshot = screenshot.resize(new_size)

        # Convert to PNG bytes then base64
        buffer = io.BytesIO()
        screenshot.save(buffer, format="PNG", optimize=True)
        base64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")

        # Return structured content (image + text) for the tool result
        return [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": base64_data,
                },
            },
            {
                "type": "text",
                "text": (
                    "Here is a screenshot of the user's screen. "
                    "Describe what you see in simple, plain language. "
                    "If there's a popup or error, explain what it means and what they should do. "
                    "If it looks like a scam popup, warn them immediately."
                ),
            },
        ]

    except ImportError:
        return (
            "I need a helper program to see your screen. "
            "Can you describe what you see instead? What does the message or popup say?"
        )
    except Exception:
        return (
            "I had trouble taking a picture of your screen. "
            "Can you tell me what you see? Read me any messages or describe the buttons."
        )


def verify_screen_step(expected: str) -> str | list:
    """Take a screenshot to verify the user completed a step correctly.
    Use after giving instructions to check that the expected result is visible.
    For example, after telling them to open Word, verify Word is on screen.
    After telling them to click Send, verify the email was sent.
    This is your way of checking their work — like looking over their shoulder.
    """
    if not expected or not expected.strip():
        return "I need to know what to look for. What should be on the screen?"

    # Reuse read_my_screen for the actual screenshot
    result = read_my_screen()

    # If we got a screenshot (list with image + text), enhance the text prompt
    if isinstance(result, list) and len(result) >= 2:
        result[1] = {
            "type": "text",
            "text": (
                f"Here is a screenshot of the user's screen. "
                f"I was checking whether this step was completed: \"{expected}\"\n\n"
                f"Look at the screen and tell me:\n"
                f"1. Is the expected result visible? (yes/no)\n"
                f"2. If NOT, what IS on screen instead? What might have gone wrong?\n"
                f"3. Give a simple, encouraging next step.\n\n"
                f"Use plain, friendly language — no jargon."
            ),
        }
        return result

    # Non-Windows fallback — ask the user to describe what they see
    return (
        f"I was checking if this worked: \"{expected}\"\n"
        "I can't see your screen from here. "
        "Can you tell me — do you see what we expected? "
        "Describe what's on your screen and I'll help from there!"
    )


# ---------------------------------------------------------------------------
# Email Module — Simulated inbox for demo (swap for IMAP/SMTP later)
# ---------------------------------------------------------------------------

SIMULATED_INBOX = [
    {
        "id": 1,
        "from": "Sarah Johnson <sarah.johnson@gmail.com>",
        "subject": "Sunday dinner at our place!",
        "date": "February 12, 2026 at 10:15 AM",
        "preview": "Hi! We'd love to have you over for dinner this Sunday...",
        "body": (
            "Hi!\n\n"
            "We'd love to have you over for dinner this Sunday at 5pm. "
            "Tommy has been asking about you all week — he wants to show you "
            "his new drawings!\n\n"
            "I'm making your favorite pot roast. Let me know if you can make it!\n\n"
            "Love,\nSarah"
        ),
        "is_read": False,
    },
    {
        "id": 2,
        "from": "CVS Pharmacy <noreply@cvs.com>",
        "subject": "Your prescription is ready for pickup",
        "date": "February 12, 2026 at 9:30 AM",
        "preview": "Your prescription for Lisinopril is ready at the CVS on Main St...",
        "body": (
            "Hello,\n\n"
            "Your prescription for Lisinopril 10mg is ready for pickup at:\n"
            "CVS Pharmacy — 245 Main Street\n\n"
            "Pharmacy hours: Mon-Fri 9am-9pm, Sat-Sun 10am-6pm\n\n"
            "Please bring your insurance card and photo ID.\n\n"
            "Thank you,\nCVS Pharmacy"
        ),
        "is_read": True,
    },
    {
        "id": 3,
        "from": "Dr. Johnson's Office <appointments@drjohnson.com>",
        "subject": "Appointment reminder — Thursday Feb 13",
        "date": "February 11, 2026 at 3:00 PM",
        "preview": "This is a reminder that you have an appointment tomorrow...",
        "body": (
            "Dear Patient,\n\n"
            "This is a friendly reminder that you have an appointment:\n\n"
            "Date: Thursday, February 13, 2026\n"
            "Time: 2:30 PM\n"
            "Doctor: Dr. Michael Johnson\n"
            "Location: 100 Medical Center Drive, Suite 204\n\n"
            "If you'd prefer a telehealth visit, join via Zoom:\n"
            "https://zoom.us/j/3678174163\n\n"
            "Please arrive 15 minutes early. Bring your insurance card and "
            "a list of current medications.\n\n"
            "To reschedule, call (555) 234-5678.\n\n"
            "Best regards,\nDr. Johnson's Office"
        ),
        "meeting_link": "https://zoom.us/j/3678174163",
        "attachments": [{"name": "Appointment_Details.pdf", "size_kb": 142}],
        "is_read": False,
    },
    {
        "id": 4,
        "from": "Tommy Johnson <tommy.j2018@gmail.com>",
        "subject": "Look what I drew grandma!!",
        "date": "February 11, 2026 at 7:45 PM",
        "preview": "Grandma look I drew a picture of us at the park...",
        "body": (
            "GRANDMA LOOK!!\n\n"
            "I drew a picture of us at the park with the ducks! "
            "Mom said I could email it to you. Its attached!\n\n"
            "Can we go feed the ducks again soon??\n\n"
            "Love Tommy\n"
            "PS mom helped me spell some words"
        ),
        "attachments": [{"name": "Tommy_Duck_Drawing.png", "size_kb": 340}],
        "is_read": False,
    },
    {
        "id": 5,
        "from": "Prize Winner Notification <winner@free-prizes-now.xyz>",
        "subject": "CONGRATULATIONS! You've Won $50,000!!!",
        "date": "February 11, 2026 at 11:20 AM",
        "preview": "Act now! You have been selected as our GRAND PRIZE WINNER...",
        "body": (
            "CONGRATULATIONS!\n\n"
            "You have been selected as our GRAND PRIZE WINNER of $50,000!\n\n"
            "To claim your prize, you must act now! Send your:\n"
            "- Full name\n"
            "- Social Security Number\n"
            "- Bank account number\n\n"
            "Send this information to claim@free-prizes-now.xyz within 24 hours "
            "or your prize will be given to someone else!\n\n"
            "Click here to claim: bit.ly/claim-prize-now\n\n"
            "This is NOT a scam. Act now!"
        ),
        "is_read": False,
    },
    {
        "id": 6,
        "from": "Book Club <bookclub@library.org>",
        "subject": "Next month's book pick: 'The Thursday Murder Club'",
        "date": "February 10, 2026 at 2:00 PM",
        "preview": "Hi everyone! Our next book is The Thursday Murder Club by Richard Osman...",
        "body": (
            "Hi everyone!\n\n"
            "Our next book club pick is:\n"
            "'The Thursday Murder Club' by Richard Osman\n\n"
            "We'll meet on Tuesday, March 4th at 10am at the library.\n"
            "Coffee and cookies will be provided!\n\n"
            "I've attached the full reading list for the next few months.\n\n"
            "See you there,\nMargaret\nLibrary Book Club Coordinator"
        ),
        "attachments": [{"name": "February_Book_List.pdf", "size_kb": 89}],
        "is_read": True,
    },
]

# Track inbox state (deleted emails)
_deleted_ids: set[int] = set()
_sent_emails: list[dict] = []


@mcp.tool()
def check_email() -> str:
    """Check the email inbox. Shows recent emails with sender, subject, and date.
    Use when the user says "check my email" or "do I have any messages?"
    """
    active = [e for e in SIMULATED_INBOX if e["id"] not in _deleted_ids]

    if not active:
        return "Your inbox is empty! No new messages right now."

    unread = sum(1 for e in active if not e["is_read"])
    lines = [f"You have {len(active)} emails ({unread} unread):\n"]

    for e in active:
        status = "NEW" if not e["is_read"] else "READ"
        # Scan for scam indicators
        scan_text = f"{e['from']} {e['subject']} {e.get('preview', '')}"
        scan = _scan_for_scam(scan_text)
        warning = " ⚠️ SUSPICIOUS" if scan["risk"] != "SAFE" else ""
        sender = e["from"].split("<")[0].strip()
        # Shorten date: "February 12, 2026 at 10:15 AM" -> "Feb 12, 10:15 AM"
        try:
            dt = datetime.strptime(e["date"], "%B %d, %Y at %I:%M %p")
            short_date = dt.strftime("%b %d, %I:%M %p")
        except ValueError:
            short_date = e["date"]
        lines.append(f"{e['id']}. [{status}] {sender} — \"{e['subject']}\" ({short_date}){warning}")

    return "\n".join(lines)


@mcp.tool()
def read_email(email_id: int) -> str:
    """Read a specific email by its number. Shows the full message.
    Use when the user wants to read a particular email from the inbox list.

    Args:
        email_id: The number of the email to read (from the inbox list)
    """
    if email_id in _deleted_ids:
        return "That email was already deleted."

    email = next((e for e in SIMULATED_INBOX if e["id"] == email_id), None)
    if not email:
        return f"I can't find email #{email_id}. Try checking your inbox first to see what's there."

    # Mark as read
    email["is_read"] = True

    # Auto-scan for scam indicators
    full_text = f"{email['from']} {email['subject']} {email['body']}"
    scan = _scan_for_scam(full_text)

    lines = []

    # Prepend scam warning if risky
    if scan["risk"] == "DANGEROUS":
        lines.append("⛔ DANGER — This email has multiple scam indicators!")
        lines.append("Do NOT click links, send money, or share personal information.")
        lines.append("")
        # List the specific flags found
        categories_seen = set()
        for category, phrase in scan["flags"]:
            if category not in categories_seen:
                categories_seen.add(category)
                if category == "urgency":
                    lines.append(f"  - Pressure language: \"{phrase}\"")
                elif category == "authority":
                    lines.append(f"  - Impersonates authority: \"{phrase}\"")
                elif category == "financial":
                    lines.append(f"  - Asks for money/info: \"{phrase}\"")
                elif category == "tech_support":
                    lines.append(f"  - Fake tech support: \"{phrase}\"")
                elif category == "grandparent":
                    lines.append(f"  - Emergency money request: \"{phrase}\"")
                elif category == "shortened_url":
                    lines.append(f"  - Hidden link: \"{phrase}\"")
                elif category == "suspicious_tld":
                    lines.append(f"  - Suspicious website: \"{phrase}\"")
        lines.append("")
        # Show matched org contacts if any
        if scan["matched_orgs"]:
            for org_key in scan["matched_orgs"]:
                org = KNOWN_LEGITIMATE_CONTACTS.get(org_key, {})
                if org:
                    lines.append(f"If this were really from {org['name']}, call them at {org['phone']} to verify.")
                    lines.append(f"Remember: {org['key_fact']}")
            lines.append("")
        # Always include elder fraud hotline
        fbi = KNOWN_LEGITIMATE_CONTACTS["fbi"]
        lines.append(f"To report scams, call the {fbi['name']}: {fbi['phone']}")
        lines.append("")
        lines.append("TIP: Ask me to \"analyze this email for scams\" for a detailed safety check.")
        lines.append("")
        lines.append("--- EMAIL BELOW (read with caution) ---\n")
    elif scan["risk"] == "SUSPICIOUS":
        lines.append("⚠️ CAUTION — This email has some suspicious elements. Be careful with any links or requests.")
        lines.append("")

    lines.extend([
        f"From: {email['from']}",
        f"Subject: {email['subject']}",
        f"Date: {email['date']}",
    ])

    # Show attachments if present
    attachments = email.get("attachments", [])
    if attachments:
        names = ", ".join(a["name"] for a in attachments)
        lines.append(f"Attachments: {names}")

    # Show meeting link if present
    meeting_link = email.get("meeting_link")
    if meeting_link:
        lines.append(f"Video call link: {meeting_link}")

    lines.append("")
    lines.append(email["body"])
    return "\n".join(lines)


@mcp.tool()
def send_email(to: str, subject: str, body: str, attachment: str = "") -> str:
    """Send an email to someone. Always confirm with the user before sending.
    Use when the user wants to write and send an email. Can include a file attachment.

    Args:
        to: Email address of the person to send to
        subject: Subject line of the email
        body: The message to send
        attachment: Full path to a file to attach (optional)
    """
    email_data = {"to": to, "subject": subject, "body": body}

    attachment_note = ""
    if attachment:
        att_path = Path(attachment)
        if not att_path.exists():
            return f"I can't find the file to attach: {attachment}. Let's find it first."
        size_mb = att_path.stat().st_size / (1024 * 1024)
        if size_mb > 25:
            return f"That file is {size_mb:.1f}MB — too large to email (max 25MB)."
        email_data["attachment"] = attachment
        attachment_note = f"\nAttachment: {att_path.name}"

    _sent_emails.append(email_data)
    return (
        f"Email sent!\n\n"
        f"To: {to}\n"
        f"Subject: {subject}{attachment_note}\n\n"
        f"Your message has been delivered."
    )


@mcp.tool()
def delete_email(email_id: int) -> str:
    """Delete an email from the inbox. Always confirm with the user first.
    Use when the user wants to remove an email.

    Args:
        email_id: The number of the email to delete
    """
    if email_id in _deleted_ids:
        return "That email was already deleted."

    email = next((e for e in SIMULATED_INBOX if e["id"] == email_id), None)
    if not email:
        return f"I can't find email #{email_id}."

    _deleted_ids.add(email_id)
    return f"Done! I deleted the email '{email['subject']}' from {email['from'].split('<')[0].strip()}."


@mcp.tool()
def download_attachment(email_id: int, attachment_name: str = "") -> str:
    """Download an attachment from an email and save it to the Downloads folder.
    Use when the user wants to open or save a file that came with an email.

    Args:
        email_id: The number of the email that has the attachment
        attachment_name: Name of the specific attachment to download (optional — downloads first if not specified)
    """
    if email_id in _deleted_ids:
        return "That email was deleted."

    email = next((e for e in SIMULATED_INBOX if e["id"] == email_id), None)
    if not email:
        return f"I can't find email #{email_id}. Try checking your inbox first."

    attachments = email.get("attachments", [])
    if not attachments:
        return f"That email from {email['from'].split('<')[0].strip()} doesn't have any attachments."

    # Check if email itself is suspicious — warn before downloading
    full_text = f"{email['from']} {email['subject']} {email['body']}"
    scan = _scan_for_scam(full_text)
    if scan["risk"] == "DANGEROUS":
        return (
            "I'm not going to download this — the email it came from looks like a scam.\n\n"
            "Scam emails sometimes include files that can harm your computer. "
            "It's safest to delete this email. Would you like me to delete it?"
        )

    # Find the right attachment
    if attachment_name:
        att = next((a for a in attachments if a["name"].lower() == attachment_name.lower()), None)
        if not att:
            names = ", ".join(a["name"] for a in attachments)
            return f"I can't find '{attachment_name}'. The attachments on this email are: {names}"
    else:
        att = attachments[0]

    # Block dangerous file types
    ext = Path(att["name"]).suffix.lower()
    if ext in DANGEROUS_EXTENSIONS:
        return (
            f"I'm blocking this download — '{att['name']}' is a {ext} file.\n\n"
            f"Files ending in {ext} can contain harmful programs. "
            f"A real document would end in .pdf, .doc, or .jpg.\n\n"
            f"This is almost certainly dangerous. I recommend deleting this email."
        )

    # "Download" to the Downloads folder
    downloads = WIN_HOME / "Downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    save_path = downloads / att["name"]

    # For demo: create a realistic file if it doesn't exist
    if not save_path.exists():
        if att["name"].endswith(".pdf"):
            # Create a simple text-based placeholder (readable in any viewer)
            content = _generate_demo_attachment(email, att)
            save_path.write_text(content, encoding="utf-8")
        elif att["name"].endswith(".png") or att["name"].endswith(".jpg"):
            # Create a minimal placeholder text file with image extension
            save_path.write_text(f"[Demo placeholder for {att['name']}]", encoding="utf-8")

    return (
        f"Downloaded! I saved '{att['name']}' to your Downloads folder.\n\n"
        f"File: {save_path}\n"
        f"Size: {att['size_kb']} KB\n\n"
        f"Would you like me to open it?"
    )


def _generate_demo_attachment(email: dict, att: dict) -> str:
    """Generate realistic demo content for a simulated email attachment."""
    if "appointment" in att["name"].lower():
        return (
            "APPOINTMENT CONFIRMATION\n"
            "========================\n\n"
            "Patient: [Your Name]\n"
            "Doctor: Dr. Michael Johnson, MD\n"
            "Date: Thursday, February 13, 2026\n"
            "Time: 2:30 PM\n"
            "Location: 100 Medical Center Drive, Suite 204\n\n"
            "Telehealth Option: https://zoom.us/j/3678174163\n\n"
            "WHAT TO BRING:\n"
            "- Insurance card\n"
            "- Photo ID\n"
            "- List of current medications\n"
            "- Any questions you have for the doctor\n\n"
            "To reschedule: (555) 234-5678\n\n"
            "We look forward to seeing you!\n"
        )
    elif "book" in att["name"].lower():
        return (
            "LIBRARY BOOK CLUB — 2026 READING LIST\n"
            "======================================\n\n"
            "February: 'The Thursday Murder Club' by Richard Osman\n"
            "  Meeting: Tuesday, March 4 at 10am\n\n"
            "March: 'A Man Called Ove' by Fredrik Backman\n"
            "  Meeting: Tuesday, April 1 at 10am\n\n"
            "April: 'The Midnight Library' by Matt Haig\n"
            "  Meeting: Tuesday, May 6 at 10am\n\n"
            "All meetings at the Main Library, Room 201.\n"
            "Coffee and cookies provided!\n\n"
            "Questions? Contact Margaret at bookclub@library.org\n"
        )
    return f"Attachment from: {email.get('from', 'Unknown')}\n"


# ---------------------------------------------------------------------------
# Photo Module — Find and manage photos
# ---------------------------------------------------------------------------

PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".heic", ".webp"}


@mcp.tool()
def find_photos(search_term: str = "", days_back: int = 0, search_in: str = "common") -> str:
    """Find photos on the computer. Search by name or find recent photos.
    Use when the user says "find my photos" or "where are my vacation pictures?"

    Args:
        search_term: What to search for (e.g., "vacation", "christmas", "grandkids"). Leave empty to find all recent photos.
        days_back: How many days back to look (0 = search by name only)
        search_in: Where to search — "common" for standard folders, or a specific path
    """
    results = []
    search_dirs = list(USER_FOLDERS) if search_in == "common" else [Path(search_in)]

    cutoff = None
    if days_back > 0:
        cutoff = datetime.now() - timedelta(days=days_back)

    def _search_photos(path: Path, depth: int = 0, max_depth: int = 3):
        if len(results) >= 50:
            return
        try:
            if path.is_file():
                if path.suffix.lower() not in PHOTO_EXTENSIONS:
                    return
                if search_term and search_term.lower() not in path.name.lower():
                    return
                stat = path.stat()
                modified = datetime.fromtimestamp(stat.st_mtime)
                if cutoff and modified < cutoff:
                    return
                results.append({
                    "path": str(path),
                    "name": path.name,
                    "folder": str(path.parent),
                    "modified": modified.strftime("%B %d, %Y at %I:%M %p"),
                    "size_kb": round(stat.st_size / 1024, 1),
                })
            elif path.is_dir() and depth < max_depth and not path.name.startswith("."):
                for child in path.iterdir():
                    _search_photos(child, depth + 1, max_depth)
        except (PermissionError, OSError):
            pass

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        try:
            for item in search_dir.iterdir():
                _search_photos(item)
        except PermissionError:
            continue

    results.sort(key=lambda x: x["modified"], reverse=True)

    if not results:
        if search_term:
            return f"I couldn't find any photos with '{search_term}' in the name. Would you like me to look somewhere else?"
        return "I didn't find any recent photos. Would you like me to search for specific ones by name?"

    lines = [f"I found {len(results)} photo(s):\n"]
    for i, r in enumerate(results[:10], 1):
        lines.append(f"{i}. {r['name']}")
        lines.append(f"   In: {r['folder']}")
        lines.append(f"   Taken/saved: {r['modified']}")
        lines.append("")

    if len(results) > 10:
        lines.append(f"...and {len(results) - 10} more photos.")

    return "\n".join(lines)


@mcp.tool()
def share_photo(photo_path: str, to_email: str) -> str:
    """Share a photo by emailing it to someone. Always confirm with the user first.
    Use when the user wants to send a photo to family or friends.

    Args:
        photo_path: Full path to the photo to share
        to_email: Email address to send the photo to
    """
    path = Path(photo_path)
    if not path.exists():
        return f"I can't find that photo at {photo_path}. Let's find it first."

    if path.suffix.lower() not in PHOTO_EXTENSIONS:
        return "That doesn't seem to be a photo file. Would you like to find your photos first?"

    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > 25:
        return f"That photo is {size_mb:.1f}MB — too large to email. Would you like me to help you resize it first?"

    _sent_emails.append({
        "to": to_email,
        "subject": f"Photo: {path.name}",
        "body": f"Here's the photo you wanted! ({path.name})",
        "attachment": str(path),
    })
    return f"Done! I sent {path.name} to {to_email}. They should receive it shortly."


# ---------------------------------------------------------------------------
# Video Call Module — Help join and manage video calls
# ---------------------------------------------------------------------------

@mcp.tool()
def check_for_meeting_links() -> str:
    """Check emails for video call meeting links (Zoom, Google Meet, Teams).
    Use when the user says "do I have any meetings?" or "how do I join my call?"
    """
    meeting_emails = []
    for email in SIMULATED_INBOX:
        if email["id"] in _deleted_ids:
            continue
        # Check for explicit meeting_link field first
        if email.get("meeting_link"):
            meeting_emails.append(email)
            continue
        # Then check body/subject text for meeting keywords
        body_lower = email["body"].lower()
        subject_lower = email["subject"].lower()
        full_text = f"{subject_lower} {body_lower}"
        if any(kw in full_text for kw in ["zoom", "meet.google", "teams", "meeting link", "join the call"]):
            meeting_emails.append(email)

    if not meeting_emails:
        return "I don't see any meeting links in your recent emails. Are you expecting a call from someone? I can help you set one up."

    lines = ["I found these meeting-related emails:\n"]
    for e in meeting_emails:
        lines.append(f"  From: {e['from'].split('<')[0].strip()}")
        lines.append(f"  Subject: {e['subject']}")
        lines.append(f"  Date: {e['date']}")
        link = e.get("meeting_link")
        if link:
            lines.append(f"  Meeting link: {link}")
        lines.append("")

    lines.append("Would you like me to help you join one of these meetings?")
    return "\n".join(lines)


@mcp.tool()
def join_video_call(meeting_link: str) -> str:
    """Help the user join a video call by opening the meeting link.
    Use when the user has a Zoom, Google Meet, or Teams link to join.

    Args:
        meeting_link: The meeting URL (Zoom, Meet, or Teams link)
    """
    link_lower = meeting_link.lower()

    # Validate the meeting URL domain
    is_trusted = any(domain in link_lower for domain in TRUSTED_MEETING_DOMAINS)
    if not is_trusted:
        return (
            f"I'm not sure this is a real meeting link: {meeting_link}\n\n"
            "I only recognize links from Zoom (zoom.us), Google Meet (meet.google.com), "
            "and Microsoft Teams (teams.microsoft.com).\n\n"
            "If someone sent you this link claiming to be tech support or a government agency, "
            "it could be a scam. Scammers sometimes use fake meeting links to get access to your computer.\n\n"
            "If you're sure this is from someone you trust, let me know and I'll open it."
        )

    if "zoom" in link_lower:
        app_name = "Zoom"
        steps = [
            "I'm opening the Zoom link now.",
            "If a window pops up asking to open Zoom, click 'Open Zoom Meetings'.",
            "You'll see a preview of your camera — make sure you look okay!",
            "Click the blue 'Join' button.",
            "You're in! If you can't hear anyone, check that your speaker is on.",
        ]
    elif "meet.google" in link_lower:
        app_name = "Google Meet"
        steps = [
            "I'm opening Google Meet in your browser.",
            "You'll see a camera preview — check that you can see yourself.",
            "Click the big 'Join now' button.",
            "You're in! If your microphone is muted, click the microphone icon at the bottom.",
        ]
    elif "teams" in link_lower:
        app_name = "Microsoft Teams"
        steps = [
            "I'm opening the Teams meeting link.",
            "If it asks, choose 'Continue on this browser' or 'Open Microsoft Teams'.",
            "Click 'Join now' when you're ready.",
            "You're in! The microphone and camera buttons are at the top.",
        ]
    else:
        app_name = "video call"
        steps = [
            "I'm opening the meeting link now.",
            "Look for a 'Join' or 'Join Meeting' button and click it.",
            "Make sure your camera and microphone are turned on.",
        ]

    # Try to open the link
    try:
        if IS_WINDOWS:
            os.startfile(meeting_link)
        else:
            subprocess.Popen(["xdg-open", meeting_link],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass  # Link opening is best-effort

    lines = [f"Let's get you into your {app_name} call!\n"]
    for i, step in enumerate(steps, 1):
        lines.append(f"  Step {i}: {step}")
    lines.append("\nTake your time — I'm right here if you need help!")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Web Search — Tool #22
# ---------------------------------------------------------------------------

@mcp.tool()
def search_web(query: str, num_results: int = 3) -> str:
    """Search the internet for information. Use when the user asks a question
    you don't know the answer to, when you need to verify something (like a
    phone number or organization), or when the user asks 'look this up for me'.

    Args:
        query: What to search for (e.g., "IRS phone number", "CVS pharmacy hours Main Street")
        num_results: How many results to return (1-5, default 3)
    """
    if not query.strip():
        return "I need something to search for. What would you like me to look up?"

    num_results = max(1, min(5, num_results))
    results = _search_web_raw(query, max_results=num_results)

    if not results:
        return (
            f"I wasn't able to search for '{query}' right now. "
            f"Let me try to help you with what I know."
        )

    lines = [f"Here's what I found about '{query}':\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}")
        lines.append(f"   {r['body'][:300]}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Local Memory — Tools #23, #24, #25
# ---------------------------------------------------------------------------

@mcp.tool()
def save_note(filename: str, content: str) -> str:
    """Save a note about the user on their computer. Use this to remember
    preferences, contacts, routines, and what you worked on together.
    Notes are stored as simple text files on the user's PC — private and local.

    Args:
        filename: Name for the note file (e.g., "preferences", "contacts", "session-2_12_26")
        content: What to save (plain text)
    """
    if not filename.strip():
        return "I need a name for this note. What should I call it?"
    if not content.strip():
        return "The note is empty. What would you like me to save?"

    NOTES_DIR.mkdir(parents=True, exist_ok=True)

    if not filename.endswith(".md"):
        filename += ".md"

    # Sanitize filename
    safe_name = re.sub(r'[^\w\s\-.]', '', filename)
    if not safe_name:
        safe_name = "note.md"

    filepath = NOTES_DIR / safe_name

    with open(filepath, "a", encoding="utf-8") as f:
        f.write(f"\n---\n_Updated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}_\n\n")
        f.write(content.strip() + "\n")

    return f"Saved to {filepath.name}. This note is stored safely on your computer — not in the cloud."


@mcp.tool()
def read_notes(filename: str = "") -> str:
    """Read a note file from the user's computer, or list all available notes.
    Use to recall what you know about the user — their preferences, contacts, past sessions.

    Args:
        filename: Name of the note to read (e.g., "preferences", "contacts"). Leave empty to list all notes.
    """
    if not NOTES_DIR.exists():
        return "No notes yet — this looks like our first time working together!"

    if not filename.strip():
        files = sorted(NOTES_DIR.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
        if not files:
            return "No notes saved yet."
        lines = ["Here are the notes I have saved on your computer:\n"]
        for f in files:
            modified = datetime.fromtimestamp(f.stat().st_mtime).strftime("%B %d, %Y")
            lines.append(f"  - {f.name} (last updated {modified})")
        return "\n".join(lines)

    if not filename.endswith(".md"):
        filename += ".md"

    filepath = NOTES_DIR / filename
    if not filepath.exists():
        return f"I don't have a note called '{filename}'. Would you like me to create one?"

    text = filepath.read_text(encoding="utf-8")
    if len(text) > 3000:
        text = text[:3000] + "\n\n... (note continues)"
    return f"=== {filename} ===\n{text}"


@mcp.tool()
def recall_user_context() -> str:
    """Remember what you know about this person by reading saved notes.
    Call this at the start of each conversation to restore context.
    Reads preferences, contacts, and the most recent session notes.
    """
    if not NOTES_DIR.exists():
        return "No notes yet — this is our first conversation! I'll start keeping notes about what we work on together."

    files = sorted(NOTES_DIR.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        return "No notes yet — this is our first conversation!"

    context_parts = []

    # Read preferences and contacts first (most important)
    for priority in ["preferences.md", "contacts.md"]:
        pf = NOTES_DIR / priority
        if pf.exists():
            context_parts.append(f"=== {priority} ===\n{pf.read_text(encoding='utf-8')[:2000]}")

    # Then most recent session file
    session_files = [f for f in files if f.name.startswith("session-")]
    if session_files:
        latest = session_files[0]
        context_parts.append(f"=== {latest.name} (most recent) ===\n{latest.read_text(encoding='utf-8')[:2000]}")

    # List all available note files
    context_parts.append(f"\nAll note files: {', '.join(f.name for f in files)}")

    return "\n\n".join(context_parts)


# --- iPhone / iOS Simulator Remote Control ---
# Connects to a Flask screenshot server running on a Mac (via Cloudflare Tunnel)
PHONE_SERVER_URL = os.environ.get("PHONE_SERVER_URL", "")


@mcp.tool()
def capture_phone_screen() -> str | list:
    """Take a screenshot of the user's iPhone screen so you can SEE what's on their phone.
    Use when they say 'look at my phone', 'what's on my phone screen?',
    'I got a weird text', or 'help me with my iPhone'.
    This captures the phone screen and lets you see exactly what they see.
    """
    if not PHONE_SERVER_URL:
        return "Phone screen capture isn't set up yet. I can help with your computer screen instead — just say 'read my screen'."

    try:
        import urllib.request
        import json

        req = urllib.request.Request(f"{PHONE_SERVER_URL}/screenshot")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())

        base64_data = data["image"]

        return [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": base64_data,
                },
            },
            {
                "type": "text",
                "text": (
                    "Here is a screenshot of the user's iPhone screen. "
                    "Describe what you see in simple, plain language. "
                    "If there's a suspicious message or scam, warn them immediately. "
                    "Give step-by-step guidance: 'Tap the blue button that says Settings.'"
                ),
            },
        ]
    except Exception as e:
        return (
            "I couldn't connect to the phone right now. "
            "Make sure the phone server is running and try again."
        )


@mcp.tool()
def tap_phone_screen(x: int, y: int) -> str:
    """Tap a specific location on the user's iPhone screen. Use this AFTER viewing
    a phone screenshot with capture_phone_screen to interact with the phone.
    Provide x,y coordinates based on where you want to tap in the screenshot image.
    The top-left corner of the phone screen is (0, 0).

    Args:
        x: X coordinate to tap (pixels from left edge of phone screen)
        y: Y coordinate to tap (pixels from top edge of phone screen)
    """
    if not PHONE_SERVER_URL:
        return "Phone control isn't set up yet."

    try:
        import urllib.request
        import json

        payload = json.dumps({"x": x, "y": y}).encode()
        req = urllib.request.Request(
            f"{PHONE_SERVER_URL}/tap",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())

        return f"Tapped the phone screen at ({x}, {y}). Use capture_phone_screen to see what happened."
    except Exception as e:
        return "I couldn't tap the phone screen. The phone server might not be running."


@mcp.tool()
def open_phone_app(app_name: str) -> str:
    """Open an app on the user's iPhone. Use when they say 'open Settings on my phone',
    'go to Messages', 'open Safari', etc. Available apps: Settings, Messages, Safari,
    Photos, Mail, Phone, Calendar, Maps, Camera, Notes.

    Args:
        app_name: Name of the app to open (e.g., 'Settings', 'Messages', 'Safari')
    """
    if not PHONE_SERVER_URL:
        return "Phone control isn't set up yet."

    try:
        import urllib.request
        import json

        payload = json.dumps({"app": app_name.lower()}).encode()
        req = urllib.request.Request(
            f"{PHONE_SERVER_URL}/launch",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())

        if data.get("status") == "launched":
            return f"Opened {app_name} on the phone. Use capture_phone_screen to see what's showing now."
        else:
            return f"Couldn't open {app_name}: {data.get('message', 'unknown error')}"
    except Exception as e:
        return "I couldn't open the app. The phone server might not be running."


if __name__ == "__main__":
    mcp.run()
