#!/usr/bin/env python3
"""TechBuddy Pre-Flight Check — verify all prerequisites before manual testing."""

import os
import platform
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    DESKTOP = Path.home() / "Desktop"
else:
    # WSL — find first real Windows user
    _skip = {"Public", "Default", "Default User", "All Users", "desktop.ini"}
    _win_users = [p for p in Path("/mnt/c/Users").iterdir()
                  if p.is_dir() and p.name not in _skip] if Path("/mnt/c/Users").exists() else []
    WIN_HOME = _win_users[0] if _win_users else Path.home()
    DESKTOP = WIN_HOME / "Desktop"


def check_env_file():
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return ("FAIL", f".env not found at {env_path}")
    content = env_path.read_text()
    if "ANTHROPIC_API_KEY" not in content:
        return ("FAIL", ".env missing ANTHROPIC_API_KEY")
    for line in content.splitlines():
        if line.startswith("ANTHROPIC_API_KEY="):
            key = line.split("=", 1)[1].strip().strip('"').strip("'")
            if key.startswith("sk-ant-") and len(key) > 20:
                return ("PASS", f"API key found ({key[:12]}...)")
            if len(key) > 10:
                return ("WARN", f"API key present but unusual format: {key[:12]}...")
            return ("FAIL", "API key looks empty or too short")
    return ("FAIL", "ANTHROPIC_API_KEY line found but no value")


def check_python_deps():
    missing = []
    for pkg, import_name in [
        ("flask", "flask"),
        ("anthropic", "anthropic"),
        ("python-dotenv", "dotenv"),
        ("Pillow", "PIL"),
        ("mcp", "mcp"),
    ]:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pkg)
    # ddgs has a renamed package
    try:
        from ddgs import DDGS  # noqa: F401
    except ImportError:
        try:
            from duckduckgo_search import DDGS  # noqa: F401
        except ImportError:
            missing.append("ddgs")
    if missing:
        return ("FAIL", f"Missing: {', '.join(missing)}. Run: pip install {' '.join(missing)}")
    return ("PASS", "All required packages installed")


def check_flask_running():
    try:
        import urllib.request
        req = urllib.request.urlopen("http://localhost:5000/", timeout=5)
        if req.status == 200:
            return ("PASS", "Flask responding on localhost:5000")
        return ("WARN", f"Flask returned status {req.status}")
    except Exception as e:
        return ("FAIL", f"Flask not responding on localhost:5000 — start it first")


def check_kokoro_tts():
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:5050/", timeout=3)
        return ("PASS", "Kokoro TTS responding on port 5050")
    except Exception:
        return ("WARN", "Kokoro TTS not on port 5050 (browser TTS fallback will be used)")


def check_demo_files():
    grocery = DESKTOP / "Grocery List.txt"
    if grocery.exists():
        return ("PASS", f"Demo files found at {DESKTOP}")
    return ("WARN", f"Grocery List.txt not found at {DESKTOP}. Run: python tests/setup_demo_files.py")


def check_macincloud():
    env_path = PROJECT_ROOT / ".env"
    phone_url = None
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("PHONE_SERVER_URL="):
                phone_url = line.split("=", 1)[1].strip().strip('"')
    if not phone_url:
        return ("WARN", "PHONE_SERVER_URL not set — iPhone tests will be skipped")
    try:
        import urllib.request
        urllib.request.urlopen(phone_url + "/health", timeout=10)
        return ("PASS", f"MacinCloud responding at {phone_url}")
    except Exception:
        return ("WARN", f"MacinCloud not responding at {phone_url} — iPhone tests will be skipped")


def check_screen_resolution():
    if IS_WINDOWS:
        try:
            import ctypes
            user32 = ctypes.windll.user32
            w = user32.GetSystemMetrics(0)
            h = user32.GetSystemMetrics(1)
            if w >= 1920 and h >= 1080:
                return ("PASS", f"Screen resolution: {w}x{h}")
            return ("WARN", f"Resolution {w}x{h} — recommend 1920x1080 for demo recording")
        except Exception:
            return ("WARN", "Could not detect screen resolution")
    return ("WARN", "Screen resolution check only available on Windows")


def check_pytest():
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=line"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT), timeout=120
        )
        output = result.stdout + result.stderr
        match = re.search(r"(\d+) passed", output)
        count = match.group(1) if match else "?"
        if result.returncode == 0:
            return ("PASS", f"pytest: {count} tests passed")
        else:
            # Show last few lines of output on failure
            lines = output.strip().splitlines()
            tail = "\n".join(lines[-3:])
            return ("FAIL", f"pytest failed ({count} passed):\n    {tail}")
    except subprocess.TimeoutExpired:
        return ("FAIL", "pytest timed out after 120 seconds")
    except Exception as e:
        return ("FAIL", f"pytest error: {e}")


def main():
    checks = [
        ("Environment (.env)", check_env_file),
        ("Python Dependencies", check_python_deps),
        ("Flask App (port 5000)", check_flask_running),
        ("Kokoro TTS (port 5050)", check_kokoro_tts),
        ("Demo Files (Desktop)", check_demo_files),
        ("MacinCloud (iPhone)", check_macincloud),
        ("Screen Resolution", check_screen_resolution),
        ("Automated Tests (pytest)", check_pytest),
    ]

    print()
    print("=" * 60)
    print("  TechBuddy Pre-Flight Check")
    print("=" * 60)
    print()

    results = []
    for name, func in checks:
        print(f"  Checking {name}...", end=" ", flush=True)
        try:
            status, msg = func()
        except Exception as e:
            status, msg = "FAIL", f"Check crashed: {e}"
        results.append((name, status, msg))
        icon = {"PASS": "OK", "WARN": "!!", "FAIL": "XX"}[status]
        print(f"[{icon}] {msg}")

    passes = sum(1 for _, s, _ in results if s == "PASS")
    warns = sum(1 for _, s, _ in results if s == "WARN")
    fails = sum(1 for _, s, _ in results if s == "FAIL")

    print()
    print("=" * 60)
    print(f"  Results: {passes} passed, {warns} warnings, {fails} failed")
    if fails > 0:
        print("  STATUS: NOT READY — fix failures above before testing")
    elif warns > 0:
        print("  STATUS: READY (with optional items missing)")
    else:
        print("  STATUS: ALL CLEAR — ready for testing!")
    print("=" * 60)
    print()

    sys.exit(1 if fails > 0 else 0)


if __name__ == "__main__":
    main()
