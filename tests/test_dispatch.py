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
