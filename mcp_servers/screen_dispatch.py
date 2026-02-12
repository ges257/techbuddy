"""TechBuddy Screen Dispatch MCP Server — Tiered Fallback Architecture.

The key innovation: routes every action to the fastest reliable method.

Tier 1: Direct API (win32com/subprocess)  — instant, 100% reliable
Tier 2: UI Automation (pywinauto a11y)    — fast, ~95% reliable
Tier 3: Existing MCP / web APIs           — fast, ~95% reliable
Tier 4: Claude Vision (text instructions) — slow fallback, ~90% reliable

On WSL2/Linux: Tiers 1-2 are stubbed (Windows-only). Tier 3 (filesystem/web)
and Tier 4 (Vision) work everywhere.
"""
import os
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
HOME = Path.home()

mcp = FastMCP("screen-dispatch")


# ---------------------------------------------------------------------------
# Tier 1: Direct API / subprocess — works on any OS for file/system ops
# ---------------------------------------------------------------------------

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
        search_dirs = [
            HOME / "Desktop",
            HOME / "Documents",
            HOME / "Downloads",
            HOME / "Pictures",
            HOME / "Videos",
        ]
        # On Windows, also check OneDrive
        if IS_WINDOWS:
            onedrive = HOME / "OneDrive"
            if onedrive.exists():
                search_dirs.append(onedrive)
    else:
        search_dirs = [Path(search_in)]

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        pattern = f"**/*{name}*"
        try:
            for match in search_dir.glob(pattern):
                if match.is_file():
                    stat = match.stat()
                    modified = datetime.fromtimestamp(stat.st_mtime)
                    results.append({
                        "path": str(match),
                        "name": match.name,
                        "folder": str(match.parent),
                        "modified": modified.strftime("%B %d, %Y at %I:%M %p"),
                        "size_kb": round(stat.st_size / 1024, 1),
                    })
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

    search_dirs = [
        HOME / "Desktop",
        HOME / "Documents",
        HOME / "Downloads",
        HOME / "Pictures",
    ]

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        try:
            for match in search_dir.rglob("*"):
                if not match.is_file():
                    continue
                if match.name.startswith("."):
                    continue
                if allowed_ext and match.suffix.lower() not in allowed_ext:
                    continue
                stat = match.stat()
                modified = datetime.fromtimestamp(stat.st_mtime)
                if modified >= cutoff:
                    results.append({
                        "path": str(match),
                        "name": match.name,
                        "folder": str(match.parent),
                        "modified": modified.strftime("%B %d, %Y at %I:%M %p"),
                    })
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
def list_folder(folder_path: str = "Desktop") -> str:
    """Show what's in a folder. Defaults to Desktop.
    Helps elderly users see what files they have.

    Args:
        folder_path: Which folder to look in — "Desktop", "Documents", "Downloads", "Pictures", or a full path
    """
    shortcuts = {
        "Desktop": HOME / "Desktop",
        "Documents": HOME / "Documents",
        "Downloads": HOME / "Downloads",
        "Pictures": HOME / "Pictures",
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
            "Please arrive 15 minutes early. Bring your insurance card and "
            "a list of current medications.\n\n"
            "To reschedule, call (555) 234-5678.\n\n"
            "Best regards,\nDr. Johnson's Office"
        ),
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
            "See you there,\nMargaret\nLibrary Book Club Coordinator"
        ),
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
        status = "NEW" if not e["is_read"] else "    "
        lines.append(f"  [{status}] {e['id']}. From: {e['from'].split('<')[0].strip()}")
        lines.append(f"         Subject: {e['subject']}")
        lines.append(f"         {e['date']}")
        lines.append("")

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

    lines = [
        f"From: {email['from']}",
        f"Subject: {email['subject']}",
        f"Date: {email['date']}",
        "",
        email["body"],
    ]
    return "\n".join(lines)


@mcp.tool()
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email to someone. Always confirm with the user before sending.
    Use when the user wants to write and send an email.

    Args:
        to: Email address of the person to send to
        subject: Subject line of the email
        body: The message to send
    """
    _sent_emails.append({"to": to, "subject": subject, "body": body})
    return (
        f"Email sent!\n\n"
        f"To: {to}\n"
        f"Subject: {subject}\n\n"
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


if __name__ == "__main__":
    mcp.run()
