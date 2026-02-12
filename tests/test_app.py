"""Tests for Flask app — routes + utilities, no Claude API calls."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from frontend.app import execute_tool, serialize_content


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
    result = execute_tool("find_file", {"name": "zzz_nonexistent_xyz"})
    assert isinstance(result, str)
    assert "couldn't find" in result.lower()
