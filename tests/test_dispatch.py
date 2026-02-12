"""Tests for screen_dispatch.py tools — the ones that work on any OS."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp_servers.screen_dispatch import (
    find_file,
    list_folder,
    print_document,
    troubleshoot_printer,
    analyze_scam_risk,
    describe_screen_action,
    read_my_screen,
    set_anthropic_client,
    check_email,
    read_email,
    send_email,
    delete_email,
    download_attachment,
    find_photos,
    share_photo,
    check_for_meeting_links,
    join_video_call,
    save_document_as_pdf,
    search_web,
    save_note,
    read_notes,
    recall_user_context,
    NOTES_DIR,
)


def test_find_file_not_found():
    result = find_file("zzz_nonexistent_file_xyz_12345", search_in="/tmp")
    assert "couldn't find" in result.lower()

def test_find_file_with_results():
    result = find_file("CLAUDE", search_in=str(Path(__file__).resolve().parent.parent))
    assert "CLAUDE" in result

def test_list_folder_exists():
    project_dir = str(Path(__file__).resolve().parent.parent)
    result = list_folder(project_dir)
    assert "frontend" in result or "hooks" in result

def test_list_folder_missing():
    result = list_folder("/tmp/zzz_nonexistent_folder_xyz")
    assert "can't find" in result.lower()

def test_describe_zoom_join():
    result = describe_screen_action("join a meeting", "Zoom")
    assert "step" in result.lower() or "click" in result.lower()

def test_describe_unknown_combo():
    result = describe_screen_action("fly to mars", "SpaceApp")
    assert "not sure" in result.lower() or "walk you through" in result.lower()

def test_print_missing_file():
    result = print_document("/tmp/zzz_no_such_file.pdf")
    assert "can't find" in result.lower()

def test_print_too_many_copies():
    result = print_document("/tmp/zzz_no_such_file.pdf", copies=10)
    # Should hit the "can't find" check first since file doesn't exist
    # But if file existed, copies > 5 would warn
    assert "can't find" in result.lower() or "lot of copies" in result.lower()


# --- Email tools ---

def test_check_email_returns_list():
    result = check_email()
    assert "email" in result.lower()
    assert "Sarah" in result or "CVS" in result

def test_read_email_valid():
    result = read_email(1)
    assert "Sarah" in result
    assert "pot roast" in result.lower() or "dinner" in result.lower()

def test_read_email_invalid():
    result = read_email(999)
    assert "can't find" in result.lower()

def test_send_email_success():
    result = send_email("daughter@gmail.com", "Hi sweetie", "Just wanted to say hello!")
    assert "sent" in result.lower()

def test_delete_email_valid():
    result = delete_email(6)
    assert "deleted" in result.lower() or "done" in result.lower()

def test_inbox_has_scam():
    result = read_email(5)
    assert "act now" in result.lower() or "prize" in result.lower() or "social security" in result.lower()


# --- Photo tools ---

def test_find_photos_no_results():
    result = find_photos("zzz_nonexistent_photo_xyz", search_in="/tmp")
    assert "couldn't find" in result.lower()

def test_share_photo_missing():
    result = share_photo("/tmp/zzz_no_such_photo.jpg", "grandma@gmail.com")
    assert "can't find" in result.lower()


# --- Video call tools ---

def test_check_meeting_links():
    result = check_for_meeting_links()
    # Inbox has no meeting links in our simulated data, so should say none found
    assert "don't see" in result.lower() or "found" in result.lower()

def test_join_zoom():
    result = join_video_call("https://zoom.us/j/123456789")
    assert "zoom" in result.lower()
    assert "step" in result.lower() or "join" in result.lower()

def test_join_meet():
    result = join_video_call("https://meet.google.com/abc-defg-hij")
    assert "google meet" in result.lower()

def test_join_unknown():
    result = join_video_call("https://example.com/meeting")
    # Now warns about untrusted domains (scam shield)
    assert "not sure" in result.lower() or "recognize" in result.lower()


# --- Printer troubleshooting ---

def test_troubleshoot_printer_returns_checklist():
    result = troubleshoot_printer()
    assert "printer" in result.lower()
    assert "turned on" in result.lower() or "turn" in result.lower()


# --- Email attachments ---

def test_read_email_shows_attachments():
    result = read_email(3)
    assert "Appointment_Details.pdf" in result

def test_read_email_shows_meeting_link():
    result = read_email(3)
    assert "zoom.us" in result

def test_download_attachment_valid():
    result = download_attachment(3, "Appointment_Details.pdf")
    assert "downloaded" in result.lower()
    assert "Appointment_Details.pdf" in result

def test_download_attachment_no_name():
    result = download_attachment(3)
    assert "downloaded" in result.lower()

def test_download_attachment_invalid_email():
    result = download_attachment(999)
    assert "can't find" in result.lower()

def test_download_attachment_no_attachments():
    result = download_attachment(2)  # CVS email has no attachments
    assert "doesn't have" in result.lower() or "no attachment" in result.lower()

def test_download_attachment_wrong_name():
    result = download_attachment(3, "nonexistent.pdf")
    assert "can't find" in result.lower()


# --- Meeting links from inbox ---

def test_check_meeting_links_finds_zoom():
    result = check_for_meeting_links()
    assert "Dr. Johnson" in result
    assert "zoom" in result.lower()


# --- Send email with attachment ---

def test_send_email_with_attachment():
    # Create a temp file to attach
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"test pdf content")
        temp_path = f.name
    result = send_email("sarah@gmail.com", "Letter", "Here's my letter!", attachment=temp_path)
    assert "sent" in result.lower()
    assert "attachment" in result.lower() or ".pdf" in result.lower()
    os.unlink(temp_path)

def test_send_email_with_missing_attachment():
    result = send_email("sarah@gmail.com", "Letter", "Here!", attachment="/tmp/nonexistent_file.pdf")
    assert "can't find" in result.lower()


# --- Save as PDF (non-Windows gives instructions) ---

def test_save_as_pdf_non_windows():
    result = save_document_as_pdf("/tmp/test.pdf")
    # On Linux/WSL: returns step-by-step instructions
    # On Windows: would try win32com
    assert "pdf" in result.lower() or "save" in result.lower()


# --- Scam Shield ---

def test_analyze_scam_dangerous():
    result = analyze_scam_risk(
        "CONGRATULATIONS! You have won $50,000! Send your SSN and bank account number now!",
        "email"
    )
    assert "danger" in result.lower() or "scam" in result.lower()

def test_analyze_scam_irs_impersonation():
    result = analyze_scam_risk(
        "This is the IRS. Your Social Security Number has been suspended. Call 1-800-555-0199 immediately.",
        "phone"
    )
    assert "1-800-829-1040" in result  # Real IRS number
    assert "mail" in result.lower()  # "IRS contacts by mail"

def test_analyze_scam_tech_support():
    result = analyze_scam_risk(
        "WARNING: Your computer is infected with a virus! Call Microsoft Support at 1-888-555-0123 now!",
        "popup"
    )
    assert "scam" in result.lower() or "danger" in result.lower()
    assert "1-800-642-7676" in result  # Real Microsoft number

def test_analyze_scam_safe_content():
    result = analyze_scam_risk(
        "Hi grandma! Can we go feed the ducks this weekend? Love, Tommy",
        "email"
    )
    assert "safe" in result.lower()

def test_analyze_scam_grandparent():
    result = analyze_scam_risk(
        "Grandma, I'm in jail and I need bail money right now. Don't tell anyone please!",
        "phone"
    )
    assert "danger" in result.lower() or "scam" in result.lower()
    assert "grandparent" in result.lower()

def test_read_email_scam_shows_warning():
    result = read_email(5)  # Prize scam email
    assert "SCAM WARNING" in result or "WARNING" in result
    assert "prize" in result.lower() or "congratulations" in result.lower()

def test_read_email_safe_no_warning():
    result = read_email(1)  # Sarah's dinner email
    assert "SCAM WARNING" not in result
    assert "CAUTION" not in result

def test_check_email_flags_suspicious():
    result = check_email()
    assert "SUSPICIOUS" in result  # Prize email should be flagged

def test_join_suspicious_link():
    result = join_video_call("https://totally-legit-meeting.xyz/join")
    assert "not sure" in result.lower() or "don't recognize" in result.lower() or "not recognize" in result.lower()

def test_join_trusted_link():
    result = join_video_call("https://zoom.us/j/123456789")
    assert "zoom" in result.lower()
    assert "step" in result.lower() or "join" in result.lower()


# --- Vision + Extended Thinking tests ---

def test_read_my_screen_non_windows():
    """On non-Windows, read_my_screen returns a helpful string."""
    result = read_my_screen()
    assert isinstance(result, str)
    assert "describe" in result.lower()


def test_set_anthropic_client():
    """set_anthropic_client should accept a client object."""
    # Just verify it doesn't crash — we'll pass None to reset
    set_anthropic_client(None)


def test_analyze_scam_safe_no_api_call():
    """Safe content should return 'safe' without needing API client."""
    set_anthropic_client(None)  # Ensure no client
    result = analyze_scam_risk("Hi, dinner at 5pm on Sunday!", "email")
    assert "safe" in result.lower()


def test_analyze_scam_keyword_fallback():
    """When no API client, scam analysis falls back to keyword matching."""
    set_anthropic_client(None)  # Force keyword-only mode
    result = analyze_scam_risk(
        "URGENT: Your account has been suspended! Call 1-800-555-0000 immediately. "
        "Send $500 in gift cards to restore access. From: IRS",
        "email"
    )
    assert "DANGER" in result or "WARNING" in result
    assert "scam" in result.lower() or "urgency" in result.lower() or "gift card" in result.lower()


# --- Web Search ---

def test_search_web_empty_query():
    result = search_web("")
    assert "need something" in result.lower()

def test_search_web_returns_results():
    """search_web should return results (or graceful fallback if no network)."""
    result = search_web("python programming language", num_results=2)
    # Either returns results or a graceful fallback message
    assert isinstance(result, str)
    assert len(result) > 10

def test_search_web_clamps_num_results():
    """num_results should be clamped to 1-5."""
    result = search_web("test query", num_results=100)
    assert isinstance(result, str)

def test_search_web_graceful_on_bad_query():
    """Should not crash on unusual queries."""
    result = search_web("!@#$%^&*()", num_results=1)
    assert isinstance(result, str)


# --- Local Memory ---

def test_save_note_creates_file(tmp_path, monkeypatch):
    """save_note should create a .md file."""
    import mcp_servers.screen_dispatch as sd
    monkeypatch.setattr(sd, "NOTES_DIR", tmp_path)
    result = save_note("test-note", "Hello from TechBuddy!")
    assert "saved" in result.lower()
    assert (tmp_path / "test-note.md").exists()
    content = (tmp_path / "test-note.md").read_text()
    assert "Hello from TechBuddy!" in content

def test_save_note_appends(tmp_path, monkeypatch):
    """save_note should append, not overwrite."""
    import mcp_servers.screen_dispatch as sd
    monkeypatch.setattr(sd, "NOTES_DIR", tmp_path)
    save_note("log", "First entry")
    save_note("log", "Second entry")
    content = (tmp_path / "log.md").read_text()
    assert "First entry" in content
    assert "Second entry" in content

def test_save_note_empty_content():
    result = save_note("test", "")
    assert "empty" in result.lower()

def test_save_note_empty_filename():
    result = save_note("", "some content")
    assert "need a name" in result.lower()

def test_read_notes_list_all(tmp_path, monkeypatch):
    """read_notes with no filename should list files."""
    import mcp_servers.screen_dispatch as sd
    monkeypatch.setattr(sd, "NOTES_DIR", tmp_path)
    (tmp_path / "preferences.md").write_text("test")
    (tmp_path / "contacts.md").write_text("test")
    result = read_notes()
    assert "preferences.md" in result
    assert "contacts.md" in result

def test_read_notes_specific_file(tmp_path, monkeypatch):
    """read_notes with filename should return that file's content."""
    import mcp_servers.screen_dispatch as sd
    monkeypatch.setattr(sd, "NOTES_DIR", tmp_path)
    (tmp_path / "preferences.md").write_text("Font size: large\nEmail first thing")
    result = read_notes("preferences")
    assert "Font size: large" in result

def test_read_notes_missing_file(tmp_path, monkeypatch):
    import mcp_servers.screen_dispatch as sd
    monkeypatch.setattr(sd, "NOTES_DIR", tmp_path)
    result = read_notes("nonexistent")
    assert "don't have" in result.lower()

def test_read_notes_no_dir():
    """read_notes should handle missing notes directory gracefully."""
    import mcp_servers.screen_dispatch as sd
    original = sd.NOTES_DIR
    sd.NOTES_DIR = Path("/tmp/zzz_nonexistent_techbuddy_notes_dir")
    result = read_notes()
    sd.NOTES_DIR = original
    assert "first time" in result.lower()

def test_recall_user_context_no_notes():
    """recall_user_context should be friendly when no notes exist."""
    import mcp_servers.screen_dispatch as sd
    original = sd.NOTES_DIR
    sd.NOTES_DIR = Path("/tmp/zzz_nonexistent_techbuddy_notes_dir")
    result = recall_user_context()
    sd.NOTES_DIR = original
    assert "first conversation" in result.lower()

def test_recall_user_context_with_notes(tmp_path, monkeypatch):
    """recall_user_context should read preferences + contacts + latest session."""
    import mcp_servers.screen_dispatch as sd
    monkeypatch.setattr(sd, "NOTES_DIR", tmp_path)
    (tmp_path / "preferences.md").write_text("Prefers large text")
    (tmp_path / "contacts.md").write_text("Sarah = daughter")
    (tmp_path / "session-2_12_26.md").write_text("Helped with email today")
    result = recall_user_context()
    assert "Prefers large text" in result
    assert "Sarah = daughter" in result
    assert "Helped with email today" in result

def test_save_note_adds_timestamp(tmp_path, monkeypatch):
    """save_note should include a timestamp."""
    import mcp_servers.screen_dispatch as sd
    monkeypatch.setattr(sd, "NOTES_DIR", tmp_path)
    save_note("timestamped", "Some content")
    content = (tmp_path / "timestamped.md").read_text()
    assert "Updated:" in content

def test_save_note_privacy_message(tmp_path, monkeypatch):
    """save_note should mention local/private storage."""
    import mcp_servers.screen_dispatch as sd
    monkeypatch.setattr(sd, "NOTES_DIR", tmp_path)
    result = save_note("test-privacy", "content")
    assert "not in the cloud" in result.lower() or "on your computer" in result.lower()


# ---------- verify_screen_step ----------

def test_verify_screen_step_empty_expected():
    """verify_screen_step should reject empty expected string."""
    from mcp_servers.screen_dispatch import verify_screen_step
    result = verify_screen_step("")
    assert "need to know" in result.lower()

def test_verify_screen_step_returns_content():
    """verify_screen_step should return string fallback on non-Windows (no PIL)."""
    from mcp_servers.screen_dispatch import verify_screen_step
    result = verify_screen_step("Word document is open")
    # On non-Windows (WSL test), returns a string asking user to describe screen
    if isinstance(result, str):
        assert "word document is open" in result.lower()
    else:
        # On Windows, returns list with image + verification prompt
        assert isinstance(result, list)
        assert len(result) >= 2

def test_verify_screen_step_includes_expected():
    """verify_screen_step should mention the expected state in its output."""
    from mcp_servers.screen_dispatch import verify_screen_step
    result = verify_screen_step("printer dialog appeared")
    if isinstance(result, str):
        assert "printer dialog appeared" in result.lower()
    else:
        # Check the text block in the list
        text_block = result[1]
        assert "printer dialog appeared" in text_block["text"].lower()
