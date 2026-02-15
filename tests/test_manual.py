#!/usr/bin/env python3
"""TechBuddy Manual Test Runner — interactive 50-scenario QA checklist."""

import json
import sys
from datetime import datetime
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent / "results"

# ---------------------------------------------------------------------------
# All 50 test scenarios from the submission plan (sections 1B-1K)
# ---------------------------------------------------------------------------
SCENARIOS = [
    # --- Core Chat (1B) ---
    {"id": 1, "category": "Core Chat",
     "action": "Type: 'Hello, I need help today'",
     "expected": "Warm greeting, avatar animates, TTS speaks",
     "notes": "Check avatar bobbing, mouth moving, TTS audio plays"},
    {"id": 2, "category": "Core Chat",
     "action": "Click Speak button, say something",
     "expected": "Transcribed text appears, response comes back",
     "notes": "Web Speech API — needs microphone permission"},
    {"id": 3, "category": "Core Chat",
     "action": "Click Replay button on a message",
     "expected": "Re-speaks that specific message",
     "notes": "Per-message replay button below each assistant message"},
    {"id": 4, "category": "Core Chat",
     "action": "Click Speed: Normal to toggle to Slow",
     "expected": "Changes to 0.7x, verify slower speech",
     "notes": "Button text should change to 'Speed: Slow'"},
    {"id": 5, "category": "Core Chat",
     "action": "Click Sound: On to toggle Off",
     "expected": "TTS stops, next response is silent",
     "notes": "Button text should change to 'Sound: Off'"},
    {"id": 6, "category": "Core Chat",
     "action": "Send 5+ messages rapidly",
     "expected": "No crashes, history compaction works, cookie under 4KB",
     "notes": "Check browser console for errors"},

    # --- Email (1C) ---
    {"id": 7, "category": "Email",
     "action": "Type: 'check my email'",
     "expected": "Shows 6 emails, email #5 flagged SUSPICIOUS",
     "notes": "Inbox from SIMULATED_INBOX in screen_dispatch.py"},
    {"id": 8, "category": "Email",
     "action": "Type: 'read email 1'",
     "expected": "Shows Sarah's dinner invitation, marked as read",
     "notes": "Should mention pot roast and Tommy"},
    {"id": 9, "category": "Email",
     "action": "Type: 'read email 3'",
     "expected": "Shows Dr. Johnson with Zoom link + PDF attachment",
     "notes": "Should show zoom.us link and Appointment_Details.pdf"},
    {"id": 10, "category": "Email",
     "action": "Type: 'read email 5'",
     "expected": "SCAM DETECTION FIRES — DANGER header, thinking trace, real IRS/SSA numbers",
     "notes": "THE BIG DEMO MOMENT — verify thinking trace collapsible appears"},
    {"id": 11, "category": "Email",
     "action": "Type: 'download the attachment from email 3'",
     "expected": "Saves Appointment_Details.pdf to Downloads",
     "notes": ""},
    {"id": 12, "category": "Email",
     "action": "Type: 'download the attachment from email 5'",
     "expected": "BLOCKED — refuses to download from scam email",
     "notes": "Scam email should not allow attachment download"},
    {"id": 13, "category": "Email",
     "action": "Type: 'send email to sarah at sarah.johnson@gmail.com saying I'll be there Sunday'",
     "expected": "Confirms before sending, then sends",
     "notes": "Must ask for confirmation first"},
    {"id": 14, "category": "Email",
     "action": "Type: 'delete email 5'",
     "expected": "Confirms, then deletes. check_email shows 5 remaining",
     "notes": "Must ask 'Are you sure?' first"},

    # --- Files & Apps (1D) ---
    {"id": 15, "category": "Files & Apps",
     "action": "Type: 'find my grocery list'",
     "expected": "Finds Grocery List.txt on Desktop",
     "notes": "Run setup_demo_files.py first if not found"},
    {"id": 16, "category": "Files & Apps",
     "action": "Type: 'open it'",
     "expected": "Opens in Notepad (os.startfile)",
     "notes": "Windows only — file opens in default text editor"},
    {"id": 17, "category": "Files & Apps",
     "action": "Type: 'open Word'",
     "expected": "Launches Word, blank doc",
     "notes": "Requires MS Word installed"},
    {"id": 18, "category": "Files & Apps",
     "action": "Type: 'type Dear Sarah, thank you for dinner in Word'",
     "expected": "Types text into Word via pywinauto",
     "notes": "Word must be open from previous test"},
    {"id": 19, "category": "Files & Apps",
     "action": "Type: 'save this as a PDF on my Desktop'",
     "expected": "Saves PDF via win32com",
     "notes": "Word must be open with content"},
    {"id": 20, "category": "Files & Apps",
     "action": "Type: 'what's in my Documents folder?'",
     "expected": "list_folder shows contents",
     "notes": ""},
    {"id": 21, "category": "Files & Apps",
     "action": "Type: 'find files I changed today'",
     "expected": "find_recent_files shows today's files",
     "notes": ""},

    # --- System & Troubleshooting (1E) ---
    {"id": 22, "category": "System & Troubleshooting",
     "action": "Type: 'is my computer running slow?'",
     "expected": "check_system_health: memory, disk, processes in plain language",
     "notes": "Should NOT show raw numbers, use plain language"},
    {"id": 23, "category": "System & Troubleshooting",
     "action": "Type: 'my internet isn't working'",
     "expected": "check_internet: ping test + WiFi status",
     "notes": ""},
    {"id": 24, "category": "System & Troubleshooting",
     "action": "Open Notepad first, then type: 'Notepad is frozen'",
     "expected": "fix_frozen_program: reports running, asks to confirm before killing",
     "notes": "MUST ask confirmation — never close without asking"},
    {"id": 25, "category": "System & Troubleshooting",
     "action": "Type: 'save a note that my doctor appointment is Thursday at 2:30'",
     "expected": "save_note to ~/TechBuddy Notes/",
     "notes": "Check file actually created on disk"},
    {"id": 26, "category": "System & Troubleshooting",
     "action": "Type: 'what are my notes?'",
     "expected": "read_notes lists saved files",
     "notes": ""},
    {"id": 27, "category": "System & Troubleshooting",
     "action": "Type: 'search the web for CVS pharmacy hours'",
     "expected": "search_web returns DuckDuckGo results",
     "notes": "Should summarize in plain language"},

    # --- Video Calls (1F) ---
    {"id": 28, "category": "Video Calls",
     "action": "Type: 'do I have any meetings?'",
     "expected": "check_for_meeting_links finds Zoom link in email #3",
     "notes": "Should mention Dr. Johnson"},
    {"id": 29, "category": "Video Calls",
     "action": "Type: 'join the video call'",
     "expected": "Opens zoom.us link, shows step-by-step Zoom instructions",
     "notes": ""},
    {"id": 30, "category": "Video Calls",
     "action": "Type: 'what's on my screen?'",
     "expected": "read_my_screen: PIL screenshot -> Claude Vision describes it",
     "notes": "Windows only — uses PIL.ImageGrab"},
    {"id": 31, "category": "Video Calls",
     "action": "After instructions, type: 'did that work?'",
     "expected": "verify_screen_step: takes screenshot, verifies result",
     "notes": ""},

    # --- Family SMS (1G) ---
    {"id": 32, "category": "Family SMS",
     "action": "Open SMS panel, select Sarah, type 'check on mom'",
     "expected": "TechBuddy processes request, returns SMS-length reply",
     "notes": "Click purple 'Send a SMS text to Mom's TechBuddy' button first"},
    {"id": 33, "category": "Family SMS",
     "action": "Select Michael, type 'delete email 5'",
     "expected": "Michael has can_delete=True, should work",
     "notes": ""},
    {"id": 34, "category": "Family SMS",
     "action": "Select Sarah, type 'delete email 5'",
     "expected": "Sarah does NOT have can_delete — should be blocked",
     "notes": "Should show safety message about permissions"},
    {"id": 35, "category": "Family SMS",
     "action": "Test unknown number via browser console or curl",
     "expected": "'This number isn't authorized'",
     "notes": "fetch('/sms/simulate', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({from_number:'+19999999999', message:'hi'})})"},
    {"id": 36, "category": "Family SMS",
     "action": "Check main chat for green family notification",
     "expected": "'Your daughter Sarah asked me to help...'",
     "notes": "Should appear within 3 seconds (polling interval)"},

    # --- iPhone / MacinCloud (1H) ---
    {"id": 37, "category": "iPhone (MacinCloud)",
     "action": "Type: 'what's on my phone?'",
     "expected": "capture_phone_screen -> screenshot -> Claude describes iPhone",
     "notes": "REQUIRES MacinCloud active — skip if not available"},
    {"id": 38, "category": "iPhone (MacinCloud)",
     "action": "Type: 'open Settings on my phone'",
     "expected": "open_phone_app -> Settings app launches",
     "notes": "REQUIRES MacinCloud active"},
    {"id": 39, "category": "iPhone (MacinCloud)",
     "action": "Type: 'open Safari on my phone'",
     "expected": "Safari opens",
     "notes": "REQUIRES MacinCloud active"},
    {"id": 40, "category": "iPhone (MacinCloud)",
     "action": "Type: 'open Photos on my phone'",
     "expected": "Photos app opens (com.apple.mobileslideshow)",
     "notes": "REQUIRES MacinCloud active"},

    # --- UI Polish (1I) ---
    {"id": 41, "category": "UI Polish",
     "action": "After scam detection: click 'See what I was considering...'",
     "expected": "Collapsible opens, shows Claude's reasoning",
     "notes": "The thinking-trace-content div should expand"},
    {"id": 42, "category": "UI Polish",
     "action": "Verify avatar thinking animation",
     "expected": "360-degree spin, eyes roam, sparkles fast",
     "notes": "Happens while waiting for Claude's response"},
    {"id": 43, "category": "UI Polish",
     "action": "Verify avatar speaking animation",
     "expected": "Mouth cycles, arms wave, gentle bob",
     "notes": "Happens when TTS plays"},
    {"id": 44, "category": "UI Polish",
     "action": "Verify avatar idle animation",
     "expected": "Continuous 8px bob with 1-degree tilt",
     "notes": "Always running when not thinking/speaking"},
    {"id": 45, "category": "UI Polish",
     "action": "Verify header layout",
     "expected": "Credit line visible, 4 buttons in flex row, no overlap",
     "notes": "Check at 1920x1080 and smaller window"},

    # --- Edge Cases (1J) ---
    {"id": 46, "category": "Edge Cases",
     "action": "Send empty message (click Send with empty input)",
     "expected": "'I didn't catch that. Could you say it again?'",
     "notes": "Handled in /chat route"},
    {"id": 47, "category": "Edge Cases",
     "action": "API error (temporarily invalid key, send msg, restore key)",
     "expected": "'Something went wrong on my end...' — no traceback shown",
     "notes": "IMPORTANT: restore API key after this test!"},
    {"id": 48, "category": "Edge Cases",
     "action": "Type: 'open an app called FakeApp'",
     "expected": "Graceful: 'I don't know how to open FakeApp'",
     "notes": ""},
    {"id": 49, "category": "Edge Cases",
     "action": "Type: 'find a file called xyznonexistent'",
     "expected": "'I couldn't find any files...'",
     "notes": ""},
    {"id": 50, "category": "Edge Cases",
     "action": "Send 10+ rapid messages to hit max tool rounds",
     "expected": "'I'm still working on that. Could you tell me more?'",
     "notes": "Tests MAX_TOOL_ROUNDS = 10 limit"},
]


def save_results(path: Path, results: list, completed: bool):
    data = {
        "timestamp": datetime.now().isoformat(),
        "completed": completed,
        "total": len(SCENARIOS),
        "results": results,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def load_partial_results():
    """Find most recent incomplete results file to resume."""
    if not RESULTS_DIR.exists():
        return None, []
    files = sorted(RESULTS_DIR.glob("manual_*.json"), reverse=True)
    for f in files:
        data = json.loads(f.read_text())
        if data.get("completed") is False:
            return f, data.get("results", [])
    return None, []


def print_summary(results: list):
    passes = sum(1 for r in results if r["status"] == "PASS")
    fails = sum(1 for r in results if r["status"] == "FAIL")
    skips = sum(1 for r in results if r["status"] == "SKIP")
    total = passes + fails + skips

    print()
    print("=" * 60)
    print(f"  SUMMARY: {passes} passed, {fails} failed, {skips} skipped ({total}/50)")
    print("=" * 60)

    if fails > 0:
        print()
        print("  FAILURES:")
        for r in results:
            if r["status"] == "FAIL":
                s = next((s for s in SCENARIOS if s["id"] == r["id"]), None)
                action = s["action"] if s else f"Test #{r['id']}"
                print(f"    #{r['id']}: {action}")
                if r.get("note"):
                    print(f"           -> {r['note']}")
    print()


def main():
    # Check for resumable session
    resume_path, existing_results = load_partial_results()
    completed_ids = {r["id"] for r in existing_results}
    results = list(existing_results)

    if resume_path and completed_ids:
        print(f"\nFound incomplete session ({len(completed_ids)}/50 done).")
        choice = input("Resume? [Y/n] ").strip().lower()
        if choice == "n":
            results = []
            completed_ids = set()
            resume_path = None

    now = datetime.now()
    results_path = resume_path or (RESULTS_DIR / f"manual_{now.strftime('%Y-%m-%d_%H-%M')}.json")

    print()
    print("=" * 60)
    print("  TechBuddy Manual Test Runner")
    print("  50 scenarios — type p(pass) f(fail) s(skip) q(quit)")
    print("=" * 60)

    current_category = None

    for scenario in SCENARIOS:
        if scenario["id"] in completed_ids:
            continue

        # Print category header
        if scenario["category"] != current_category:
            current_category = scenario["category"]
            print(f"\n{'─' * 60}")
            print(f"  {current_category}")
            print(f"{'─' * 60}\n")

        print(f"  [{scenario['id']}/50] {scenario['action']}")
        print(f"    EXPECTED: {scenario['expected']}")
        if scenario.get("notes"):
            print(f"    NOTE: {scenario['notes']}")

        while True:
            choice = input("    Result [p/f/s/q]: ").strip().lower()
            if choice in ("p", "pass"):
                result = {"id": scenario["id"], "status": "PASS", "note": ""}
                break
            elif choice in ("f", "fail"):
                note = input("    What went wrong? ").strip()
                result = {"id": scenario["id"], "status": "FAIL", "note": note}
                break
            elif choice in ("s", "skip"):
                result = {"id": scenario["id"], "status": "SKIP", "note": ""}
                break
            elif choice in ("q", "quit"):
                save_results(results_path, results, completed=False)
                print(f"\n  Saved partial results to {results_path}")
                print_summary(results)
                return
            else:
                print("    Type p (pass), f (fail), s (skip), or q (quit)")

        results.append(result)
        save_results(results_path, results, completed=False)

    # All done
    save_results(results_path, results, completed=True)
    print(f"\n  Results saved to {results_path}")
    print_summary(results)


if __name__ == "__main__":
    main()
