import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, session

import anthropic

# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Add project root to path so we can import mcp_servers
sys.path.insert(0, str(PROJECT_ROOT))

from mcp_servers.screen_dispatch import (
    find_file,
    find_recent_files,
    open_file,
    list_folder,
    print_document,
    click_button,
    type_text,
    describe_screen_action,
    check_email,
    read_email,
    send_email,
    delete_email,
)

app = Flask(__name__)
app.secret_key = os.urandom(24)

client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are TechBuddy, a warm and patient AI assistant that helps elderly people use their computer.

PERSONALITY:
- Speak like a friendly, patient neighbor — never like a tech manual.
- Use simple words. Say "click" not "navigate to". Say "internet" not "network". Say "picture" not "image file".
- One step at a time. Never give more than 3 steps in a single message.
- Always reassure after completing something: "You're doing great!" / "That worked perfectly!"
- If something goes wrong, never blame them. Say "Let's try that again" not "You entered it wrong".

CAPABILITIES (use the tools provided):
- Email: use check_email to see their inbox, read_email to read one, send_email to send, delete_email to remove
- Find files: use find_file or find_recent_files when they've lost a file
- Open files: use open_file to open a document, photo, or any file
- List folders: use list_folder to show what's in a folder
- Print: use print_document to send something to the printer
- Click buttons: use click_button to press buttons in apps (Windows)
- Type text: use type_text to fill in fields in apps (Windows)
- Step-by-step help: use describe_screen_action for Zoom, email, etc.

RULES:
- Always confirm before sending emails, deleting files, or any action that can't be undone.
- If you detect a potential scam, warn them clearly.
- Keep responses SHORT — 2-3 sentences max unless they ask for more detail.
- If they seem frustrated, slow down and offer encouragement.
- Never use jargon. Never show error codes or technical messages.
- Use warm greetings: "Hi there!" not "Hello, how may I assist you today?"
- USE YOUR TOOLS when the user asks for help with files, printing, or apps. Don't just describe — actually do it.
"""

# Tool definitions for Claude API
TOOLS = [
    {
        "name": "find_file",
        "description": "Find a file by partial name. Searches Desktop, Documents, Downloads, Pictures. Use when the user says they saved something and can't find it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Partial filename to search for (e.g., 'grocery', 'receipt', 'photo')"},
                "search_in": {"type": "string", "description": "Where to search — 'common' for standard folders, or a specific path", "default": "common"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "find_recent_files",
        "description": "Find files recently saved or changed. Use when someone says 'I just saved it' or 'where did it go?'",
        "input_schema": {
            "type": "object",
            "properties": {
                "hours": {"type": "integer", "description": "How far back to look in hours", "default": 24},
                "file_type": {"type": "string", "description": "Filter: 'all', 'documents', 'pictures', 'spreadsheets'", "default": "all"},
            },
        },
    },
    {
        "name": "open_file",
        "description": "Open a file with the default application. Works for documents, pictures, PDFs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Full path to the file to open"},
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "list_folder",
        "description": "Show what's in a folder. Use when someone wants to see their files. Defaults to Desktop.",
        "input_schema": {
            "type": "object",
            "properties": {
                "folder_path": {"type": "string", "description": "'Desktop', 'Documents', 'Downloads', 'Pictures', or a full path", "default": "Desktop"},
            },
        },
    },
    {
        "name": "print_document",
        "description": "Send a document to the printer. Always confirm with user before printing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Full path to the file to print"},
                "copies": {"type": "integer", "description": "Number of copies", "default": 1},
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "click_button",
        "description": "Click a button in any open window. Use for Zoom 'Join', Outlook 'Send', etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "window_title": {"type": "string", "description": "Title of the window (e.g., 'Outlook', 'Zoom')"},
                "button_name": {"type": "string", "description": "Name of the button to click (e.g., 'Send', 'Join Meeting')"},
            },
            "required": ["window_title", "button_name"],
        },
    },
    {
        "name": "type_text",
        "description": "Type text into a field in any open window. Use for filling in email recipients, search boxes, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "window_title": {"type": "string", "description": "Title of the window"},
                "text": {"type": "string", "description": "The text to type"},
                "field_name": {"type": "string", "description": "Name of the text field (optional)", "default": ""},
            },
            "required": ["window_title", "text"],
        },
    },
    {
        "name": "describe_screen_action",
        "description": "Give step-by-step instructions for a task in an app. Use when you can't automate it directly.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "What the user wants to do (e.g., 'join zoom meeting')"},
                "app_name": {"type": "string", "description": "Which app (e.g., 'Zoom', 'Outlook', 'Chrome')"},
            },
            "required": ["task", "app_name"],
        },
    },
    {
        "name": "check_email",
        "description": "Check the email inbox. Shows recent emails with who sent them and what they're about. Use when the user says 'check my email' or 'do I have messages?'",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "read_email",
        "description": "Read a specific email by its number. Shows the full message. Use after check_email when the user wants to read one.",
        "input_schema": {
            "type": "object",
            "properties": {
                "email_id": {"type": "integer", "description": "The number of the email to read (from the inbox list)"},
            },
            "required": ["email_id"],
        },
    },
    {
        "name": "send_email",
        "description": "Send an email to someone. Always confirm the recipient and message with the user before sending.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Email address to send to"},
                "subject": {"type": "string", "description": "Subject line"},
                "body": {"type": "string", "description": "The message to send"},
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "delete_email",
        "description": "Delete an email from the inbox. Always confirm with the user before deleting.",
        "input_schema": {
            "type": "object",
            "properties": {
                "email_id": {"type": "integer", "description": "The number of the email to delete"},
            },
            "required": ["email_id"],
        },
    },
]

# Map tool names to actual functions
TOOL_FUNCTIONS = {
    "find_file": find_file,
    "find_recent_files": find_recent_files,
    "open_file": open_file,
    "list_folder": list_folder,
    "print_document": print_document,
    "click_button": click_button,
    "type_text": type_text,
    "describe_screen_action": describe_screen_action,
    "check_email": check_email,
    "read_email": read_email,
    "send_email": send_email,
    "delete_email": delete_email,
}


def execute_tool(name: str, input_data: dict) -> str:
    """Execute a dispatch tool and return its result."""
    func = TOOL_FUNCTIONS.get(name)
    if not func:
        return f"Unknown tool: {name}"
    try:
        return func(**input_data)
    except Exception as e:
        return "I had trouble with that. Let's try a different approach."


def serialize_content(content) -> list[dict]:
    """Convert Anthropic SDK content blocks to JSON-serializable dicts."""
    result = []
    for block in content:
        if block.type == "text":
            result.append({"type": "text", "text": block.text})
        elif block.type == "tool_use":
            result.append({
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input,
            })
    return result


def call_claude(history: list) -> tuple[str, list]:
    """Call Claude API with tool use. Returns (final_text, updated_history).

    Handles the tool-use loop: Claude may request tools, we execute them
    and feed results back, repeating until Claude gives a text response.
    """
    MAX_TOOL_ROUNDS = 5

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=history,
        )

        # Serialize content blocks for session storage
        assistant_content = response.content
        serialized = serialize_content(assistant_content)

        # Add assistant message to history (serialized for JSON)
        history.append({"role": "assistant", "content": serialized})

        # Check if Claude wants to use tools
        tool_uses = [b for b in assistant_content if b.type == "tool_use"]

        if not tool_uses:
            # No tools — extract text and return
            text_blocks = [b.text for b in assistant_content if b.type == "text"]
            return " ".join(text_blocks) if text_blocks else "Done!", history

        # Execute each tool and build tool results
        tool_results = []
        for tool_use in tool_uses:
            result = execute_tool(tool_use.name, tool_use.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": result,
            })

        # Feed results back to Claude
        history.append({"role": "user", "content": tool_results})

    # If we hit max rounds, return what we have
    return "I'm still working on that. Could you tell me more about what you need?", history


@app.route("/")
def index():
    session["history"] = []
    return render_template("chat.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"reply": "I didn't catch that. Could you say it again?"})

    # Retrieve or init conversation history
    history = session.get("history", [])
    history.append({"role": "user", "content": user_message})

    try:
        assistant_text, history = call_claude(history)
    except anthropic.AuthenticationError:
        assistant_text = "I'm having trouble connecting right now. Let's try again in a moment."
        history.append({"role": "assistant", "content": assistant_text})
    except Exception:
        assistant_text = "Something went wrong on my end. Let's try that again."
        history.append({"role": "assistant", "content": assistant_text})

    session["history"] = history

    return jsonify({"reply": assistant_text})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
