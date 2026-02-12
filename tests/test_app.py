"""Tests for Flask app — routes + utilities, no Claude API calls."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from frontend.app import execute_tool, serialize_content, _extract_tool_thinking, _strip_tool_thinking, _build_system_prompt


def test_index_returns_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"TechBuddy" in resp.data

def test_chat_empty_message(client):
    resp = client.post("/chat", json={"message": ""})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "didn't catch" in data["reply"].lower()

def test_serialize_text_block():
    class FakeTextBlock:
        type = "text"
        text = "Hello there!"
    result = serialize_content([FakeTextBlock()])
    assert result == [{"type": "text", "text": "Hello there!"}]

def test_serialize_tool_use_block():
    class FakeToolUse:
        type = "tool_use"
        id = "toolu_123"
        name = "find_file"
        input = {"name": "recipe"}
    result = serialize_content([FakeToolUse()])
    assert result == [{"type": "tool_use", "id": "toolu_123", "name": "find_file", "input": {"name": "recipe"}}]

def test_execute_tool_unknown():
    result = execute_tool("nonexistent_tool", {})
    assert "Unknown tool" in result

def test_execute_tool_find_file():
    result = execute_tool("find_file", {"name": "zzz_nonexistent_xyz", "search_in": "/tmp"})
    assert isinstance(result, str)
    assert "couldn't find" in result.lower()


# --- Extended Thinking / Vision tests ---

def test_serialize_thinking_block():
    """Thinking blocks should be serialized correctly."""
    class FakeThinkingBlock:
        type = "thinking"
        thinking = "Let me reason about this..."
    result = serialize_content([FakeThinkingBlock()])
    assert result == [{"type": "thinking", "thinking": "Let me reason about this..."}]


def test_execute_tool_read_my_screen_non_windows():
    """On non-Windows (WSL/Linux), read_my_screen returns a helpful string."""
    result = execute_tool("read_my_screen", {})
    assert isinstance(result, str)
    assert "describe what you see" in result.lower()


def test_execute_tool_structured_return():
    """Vision tool can return a list (structured content), not just a string."""
    # read_my_screen on non-Windows returns a string, but the function
    # signature allows list return — test that execute_tool handles both types
    result = execute_tool("find_file", {"name": "test"})
    assert isinstance(result, (str, list))


def test_extract_tool_thinking():
    """Thinking trace markers should be extracted correctly."""
    text = "DANGER — scam!\n\n[THINKING_TRACE]This is a phishing email because...[/THINKING_TRACE]"
    thinking = _extract_tool_thinking(text)
    assert thinking == "This is a phishing email because..."


def test_extract_tool_thinking_empty():
    """No markers → empty string."""
    assert _extract_tool_thinking("Just a normal message.") == ""


def test_strip_tool_thinking():
    """Thinking markers should be stripped from the text."""
    text = "DANGER — scam!\n\n[THINKING_TRACE]reasoning here[/THINKING_TRACE]"
    stripped = _strip_tool_thinking(text)
    assert "[THINKING_TRACE]" not in stripped
    assert "DANGER" in stripped


def test_chat_response_includes_thinking_field(client):
    """The /chat endpoint should return a thinking field when present."""
    from unittest.mock import patch
    with patch("frontend.app.call_claude") as mock_claude:
        mock_claude.return_value = ("Here's what I found!", "I'm thinking about files...", [])
        resp = client.post("/chat", json={"message": "find my grocery list"})
        data = resp.get_json()
        assert "reply" in data
        assert "thinking" in data
        assert "thinking about files" in data["thinking"]


def test_chat_response_no_thinking_when_empty(client):
    """The /chat endpoint should NOT include thinking field when empty."""
    from unittest.mock import patch
    with patch("frontend.app.call_claude") as mock_claude:
        mock_claude.return_value = ("Hello!", "", [])
        resp = client.post("/chat", json={"message": "hi"})
        data = resp.get_json()
        assert "reply" in data
        assert "thinking" not in data


# --- Date Awareness ---

def test_system_prompt_has_date():
    """System prompt should include today's date."""
    prompt = _build_system_prompt()
    assert "TODAY'S DATE:" in prompt
    assert "2026" in prompt

def test_system_prompt_has_day_of_week():
    """System prompt should include the day of week."""
    prompt = _build_system_prompt()
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    assert any(day in prompt for day in days)

def test_system_prompt_has_web_search_section():
    """System prompt should include web search instructions."""
    prompt = _build_system_prompt()
    assert "SEARCHING THE WEB" in prompt
    assert "search_web" in prompt

def test_system_prompt_has_memory_section():
    """System prompt should include local memory instructions."""
    prompt = _build_system_prompt()
    assert "LOCAL MEMORY" in prompt
    assert "recall_user_context" in prompt
    assert "NOT in the cloud" in prompt

def test_system_prompt_has_session_date():
    """System prompt should include session date format for note filenames."""
    prompt = _build_system_prompt()
    # Should have a session date like "session-2_12_26"
    assert "session-" in prompt


# --- New tool execute tests ---

def test_execute_tool_search_web():
    result = execute_tool("search_web", {"query": ""})
    assert isinstance(result, str)
    assert "need something" in result.lower()

def test_execute_tool_save_note():
    result = execute_tool("save_note", {"filename": "", "content": "test"})
    assert isinstance(result, str)

def test_execute_tool_read_notes():
    result = execute_tool("read_notes", {})
    assert isinstance(result, str)

def test_execute_tool_recall_user_context():
    result = execute_tool("recall_user_context", {})
    assert isinstance(result, str)
