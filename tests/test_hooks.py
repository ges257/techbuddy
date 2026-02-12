"""Tests for the 3 hook scripts — the safety layer.

These test the pure functions directly (no subprocess needed).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hooks.validate_send import check_for_scam, check_recipient, check_links
from hooks.accessibility_check import check_content


# --- validate_send.py ---

def test_clean_email_allowed():
    assert check_for_scam("Hi grandma, here are the photos from Sunday!") is None

def test_scam_phrase_blocked():
    result = check_for_scam("Act now! Send money immediately!")
    assert result is not None
    assert "act now" in result.lower()

def test_scam_gift_card():
    result = check_for_scam("Please buy a gift card and send the code")
    assert result is not None

def test_clean_recipient_allowed():
    assert check_recipient("grandma@gmail.com") is None

def test_bad_recipient_blocked():
    result = check_recipient("not-an-email")
    assert result is not None
    assert "doesn't look right" in result

def test_empty_recipient_blocked():
    result = check_recipient("")
    assert result is not None

def test_suspicious_link_blocked():
    result = check_links("Check this out: bit.ly/free-stuff")
    assert result is not None
    assert "bit.ly" in result

def test_clean_links_allowed():
    assert check_links("Here is the google.com website") is None

def test_no_scam_no_links():
    assert check_for_scam("Thanks for dinner last night!") is None
    assert check_links("Thanks for dinner last night!") is None


# --- accessibility_check.py ---

def test_small_font_warns():
    warnings = check_content("template.html", "body { font-size: 12px; }")
    assert any("12px" in w for w in warnings)

def test_ok_font_no_warning():
    warnings = check_content("template.html", "body { font-size: 20px; }")
    assert not any("too small" in w for w in warnings)

def test_non_frontend_skipped():
    warnings = check_content("app.py", "font-size: 10px;")
    assert warnings == []

def test_jargon_warns():
    html = '<p class="help">Please navigate to the settings page</p>'
    warnings = check_content("help.html", html)
    assert any("navigate to" in w for w in warnings)

def test_no_jargon_clean():
    html = '<p class="help">Click the big blue button</p>'
    warnings = check_content("help.html", html)
    jargon_warnings = [w for w in warnings if "jargon" in w.lower() or "plain language" in w.lower()]
    assert len(jargon_warnings) == 0


# --- verify_elderly_safe.py (tested via main() contract) ---

def test_clean_stop():
    """verify_elderly_safe with no errors returns 'All clear'."""
    import json
    import subprocess
    result = subprocess.run(
        [sys.executable, "hooks/verify_elderly_safe.py"],
        input=json.dumps({"stop_reason": "done", "tool_results": []}),
        capture_output=True, text=True,
        cwd=str(Path(__file__).resolve().parent.parent),
    )
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert "All clear" in output.get("message", "")

def test_failed_send_warns():
    """verify_elderly_safe flags failed send actions."""
    import json
    import subprocess
    data = {
        "stop_reason": "done",
        "tool_results": [
            {"tool_name": "send_email", "is_error": True},
        ],
    }
    result = subprocess.run(
        [sys.executable, "hooks/verify_elderly_safe.py"],
        input=json.dumps(data),
        capture_output=True, text=True,
        cwd=str(Path(__file__).resolve().parent.parent),
    )
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert "send_email" in output.get("message", "").lower()
