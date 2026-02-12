"""Tests for Family SMS Remote Control feature."""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from frontend.app import (
    app,
    FAMILY_CONTACTS,
    process_family_sms,
    _pending_family_messages,
    _family_sms_log,
    DESTRUCTIVE_KEYWORDS,
)


def _get_client():
    app.config["TESTING"] = True
    return app.test_client()


# --- FAMILY_CONTACTS structure ---

def test_family_contacts_has_entries():
    assert len(FAMILY_CONTACTS) >= 2


def test_family_contacts_have_required_fields():
    for number, contact in FAMILY_CONTACTS.items():
        assert number.startswith("+")
        assert "name" in contact
        assert "relationship" in contact
        assert "can_execute" in contact
        assert "can_view_status" in contact
        assert "can_delete" in contact


def test_sarah_cannot_delete():
    sarah = FAMILY_CONTACTS["+15551234567"]
    assert sarah["name"] == "Sarah"
    assert sarah["can_delete"] is False


def test_michael_can_delete():
    michael = FAMILY_CONTACTS["+15559876543"]
    assert michael["name"] == "Michael"
    assert michael["can_delete"] is True


# --- Authorization ---

def test_simulate_unauthorized_number():
    client = _get_client()
    resp = client.post("/sms/simulate", json={
        "from_number": "+19999999999",
        "message": "check on mom",
    })
    data = resp.get_json()
    assert data["error"] is True
    assert "authorized" in data["reply"].lower()


def test_simulate_empty_message():
    client = _get_client()
    resp = client.post("/sms/simulate", json={
        "from_number": "+15551234567",
        "message": "",
    })
    data = resp.get_json()
    assert data["error"] is True


# --- Permission enforcement ---

def test_destructive_blocked_for_sarah():
    """Sarah (can_delete=False) should be blocked from delete requests."""
    sarah = FAMILY_CONTACTS["+15551234567"]
    result = process_family_sms(sarah, "delete email number 3")
    assert "can't do that" in result.lower() or "safety" in result.lower()


def test_destructive_keywords_exist():
    assert "delete" in DESTRUCTIVE_KEYWORDS
    assert "remove" in DESTRUCTIVE_KEYWORDS


# --- Simulate endpoint ---

def test_simulate_endpoint_returns_json():
    client = _get_client()
    with patch("frontend.app.call_claude") as mock_claude:
        mock_claude.return_value = ("Hi Sarah, the printer looks fine!", "", [])
        resp = client.post("/sms/simulate", json={
            "from_number": "+15551234567",
            "message": "mom says printer isnt working",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert "reply" in data
        assert "printer" in data["reply"].lower()


def test_simulate_pushes_to_pending():
    """Simulated SMS should push a message to _pending_family_messages."""
    _pending_family_messages.clear()
    client = _get_client()
    with patch("frontend.app.call_claude") as mock_claude:
        mock_claude.return_value = ("Done! I checked the inbox.", "", [])
        client.post("/sms/simulate", json={
            "from_number": "+15551234567",
            "message": "check moms email",
        })
    assert len(_pending_family_messages) >= 1
    msg = _pending_family_messages[-1]
    assert msg["from_name"] == "Sarah"
    assert msg["from_relationship"] == "daughter"
    assert "check moms email" in msg["original_message"]


# --- Twilio webhook ---

def test_sms_incoming_unauthorized():
    client = _get_client()
    resp = client.post("/sms/incoming", data={
        "From": "+19999999999",
        "Body": "check on mom",
    })
    assert resp.status_code == 200
    assert "text/xml" in resp.content_type
    assert "authorized" in resp.data.decode().lower()


def test_sms_incoming_empty_body():
    client = _get_client()
    resp = client.post("/sms/incoming", data={
        "From": "+15551234567",
        "Body": "",
    })
    assert resp.status_code == 200
    assert "text/xml" in resp.content_type


def test_sms_incoming_returns_twiml():
    client = _get_client()
    with patch("frontend.app.call_claude") as mock_claude:
        mock_claude.return_value = ("Hi Sarah, everything looks good!", "", [])
        resp = client.post("/sms/incoming", data={
            "From": "+15551234567",
            "Body": "check on mom",
        })
    assert resp.status_code == 200
    assert "text/xml" in resp.content_type
    assert "<Response>" in resp.data.decode()
    assert "<Message>" in resp.data.decode()


# --- Family messages polling ---

def test_family_messages_returns_list():
    _pending_family_messages.clear()
    _pending_family_messages.append({
        "from_name": "Sarah",
        "from_relationship": "daughter",
        "original_message": "test",
        "result": "test result",
    })
    client = _get_client()
    resp = client.get("/family/messages")
    data = resp.get_json()
    assert "messages" in data
    assert len(data["messages"]) == 1
    assert data["messages"][0]["from_name"] == "Sarah"


def test_family_messages_clears_after_fetch():
    _pending_family_messages.clear()
    _pending_family_messages.append({
        "from_name": "Test",
        "from_relationship": "test",
        "original_message": "test",
        "result": "test",
    })
    client = _get_client()
    # First fetch gets messages
    resp1 = client.get("/family/messages")
    assert len(resp1.get_json()["messages"]) == 1
    # Second fetch is empty
    resp2 = client.get("/family/messages")
    assert len(resp2.get_json()["messages"]) == 0


# --- Audit log ---

def test_sms_log_records_interactions():
    _family_sms_log.clear()
    sarah = FAMILY_CONTACTS["+15551234567"]
    with patch("frontend.app.call_claude") as mock_claude:
        mock_claude.return_value = ("Printer is fine.", "", [])
        process_family_sms(sarah, "check printer")
    assert len(_family_sms_log) >= 1
    entry = _family_sms_log[-1]
    assert entry["from"] == "Sarah"
    assert entry["message"] == "check printer"
    assert "timestamp" in entry
