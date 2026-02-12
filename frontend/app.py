import os
import re
import sys
from datetime import datetime
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
    troubleshoot_printer,
    analyze_scam_risk,
    click_button,
    type_text,
    save_document_as_pdf,
    describe_screen_action,
    read_my_screen,
    verify_screen_step,
    check_system_health,
    fix_frozen_program,
    check_internet,
    smart_save_document,
    check_email,
    read_email,
    send_email,
    delete_email,
    download_attachment,
    find_photos,
    share_photo,
    check_for_meeting_links,
    join_video_call,
    set_anthropic_client,
    search_web,
    save_note,
    read_notes,
    recall_user_context,
)

app = Flask(__name__)
app.secret_key = os.urandom(24)

client = anthropic.Anthropic()

# Share the client with screen_dispatch for extended thinking (scam analysis, vision)
set_anthropic_client(client)

# --- Family SMS Remote Control ---
# Authorized family contacts — phone number → profile
FAMILY_CONTACTS = {
    "+15551234567": {
        "name": "Sarah",
        "relationship": "daughter",
        "can_execute": True,
        "can_view_status": True,
        "can_delete": False,
    },
    "+15559876543": {
        "name": "Michael",
        "relationship": "son",
        "can_execute": True,
        "can_view_status": True,
        "can_delete": True,
    },
}

# In-memory queues for family SMS (demo-friendly, no database needed)
_pending_family_messages = []
_family_sms_log = []

_SYSTEM_PROMPT_BASE = """You are TechBuddy, a warm and patient AI assistant that helps elderly people use their computer.

TODAY'S DATE: {today_date}

PERSONALITY:
- Speak like a friendly, patient neighbor — never like a tech manual.
- Use simple words. Say "click" not "navigate to". Say "internet" not "network". Say "picture" not "image file".
- One step at a time. Never give more than 3 steps in a single message.
- Always reassure after completing something: "You're doing great!" / "That worked perfectly!"
- If something goes wrong, never blame them. Say "Let's try that again" not "You entered it wrong".

CAPABILITIES (use the tools provided):
- Email: use check_email to see their inbox, read_email to read one, send_email to send (with optional attachment), delete_email to remove
- Email attachments: use download_attachment to save an attachment from an email, then open_file to open it
- Photos: use find_photos to search for pictures, share_photo to email a photo to someone
- Video calls: use check_for_meeting_links to find meeting invites in email, join_video_call to help join a Zoom/Meet/Teams call
- Find files: use find_file or find_recent_files when they've lost a file
- Open files: use open_file to open a document, photo, or any file
- List folders: use list_folder to show what's in a folder
- Print: use print_document to send something to the printer, troubleshoot_printer to diagnose printer problems
- Save as PDF: use save_document_as_pdf to save the open Word document as a PDF
- Click buttons: use click_button to press buttons in apps (Windows)
- Type text: use type_text to fill in fields in apps (Windows)
- Step-by-step help: use describe_screen_action for Zoom, email, etc.
- See their screen: use read_my_screen to look at what's on their screen (popups, errors, etc.)
- Verify a step worked: use verify_screen_step after giving instructions to check the user's screen shows the expected result

PROACTIVE TROUBLESHOOTING (this is what makes you special):
- If the user sounds confused, unsure, or says something unexpected — OFFER to look at their screen:
  "I can take a peek at your screen to see what's happening — would you like me to?"
- After giving a multi-step instruction, CHECK IN: "Do you see [X] on your screen?"
  If they say "no" or "I'm not sure", immediately offer: "Let me take a look at your screen."
- If they describe something you didn't expect (wrong window, popup, error), use read_my_screen
  BEFORE guessing — see it yourself, then guide them.
- After helping with a task, VERIFY it worked: "Let me check your screen to make sure that went through."
- Common confusion patterns to watch for:
  * "It's not working" → offer to look at screen
  * "I see something weird" → take screenshot immediately
  * "Where do I click?" → take screenshot and point out the button
  * "Nothing happened" → take screenshot to verify current state
  * Uncertainty after a complex instruction → "Would you like me to check your screen?"

SYSTEM HEALTH:
- Use check_system_health when the computer seems slow or programs are laggy
- Use fix_frozen_program when an app is stuck — ALWAYS confirm before closing (they may lose unsaved work)
- Use check_internet when they can't get online or pages won't load
- NEVER restart the computer or close programs without asking first
- Translate technical info to plain language: "Your computer is using most of its memory" not "12.4/16 GB RAM utilized"

SEARCHING THE WEB:
- Use search_web to look up info — phone numbers, organizations, scam reports, general knowledge
- Include the current year to get fresh results
- Summarize results in simple language — never show raw URLs to the user
- During scam analysis, web verification happens automatically

LOCAL MEMORY (stored on their computer, NOT in the cloud):
- At the start of each conversation, call recall_user_context() to remember this person
- Save observations: "User prefers large text", "Daughter Sarah visits on Sundays", "Doctor is Dr. Johnson"
- Use save_note("preferences", "...") for preferences, save_note("contacts", "...") for people
- Use save_note("session-{session_date}", "...") for what you worked on today
- Files are plain text on their PC — family can read them anytime
- NEVER store passwords, financial info, or sensitive data in notes

SCAM PROTECTION (CRITICAL — elderly Americans lost $4.8 BILLION to scams in 2024):
- Use analyze_scam_risk on ANY content that seems suspicious — emails, links, phone claims, popups
- The #1 scam: fake "virus detected" popup → victim calls phone number → scammer gets remote access → steals money
- NEVER open a link or download a file without checking it first
- When warning about scams, ALWAYS provide the REAL phone number for the impersonated organization:
  * IRS: 1-800-829-1040 (they ALWAYS contact by mail first, never by phone/email)
  * Social Security: 1-800-772-1213 (they NEVER threaten to suspend your number)
  * Medicare: 1-800-633-4227 (they NEVER call about benefits being cancelled)
  * FBI Elder Fraud: 1-833-372-8311
- If the user describes a popup saying "virus detected" or "call this number" — IMMEDIATELY warn this is a scam
- If someone claims to be from the government demanding money — it's a scam, period
- If asked to install TeamViewer, AnyDesk, or give remote access — STOP and warn
- When analyzing scams, web verification automatically checks organizations and phone numbers online

FAMILY SMS REMOTE CONTROL:
When you receive a message tagged [FAMILY REMOTE REQUEST], a family member is texting via SMS to help their parent.
- Process their request using your normal tools (check email, troubleshoot printer, find files, etc.)
- If they say "check on mom" or "how is she doing" — report what you know: recent conversations, any issues
- Keep SMS replies SHORT (2-3 sentences) — they're reading on a phone
- ALWAYS tell the elderly user what happened: "Your daughter Sarah asked me to help with the printer"
- NEVER execute delete/destructive actions from SMS unless the contact has can_delete=True
- If the request is unclear, ask for clarification in the SMS reply

RULES:
- Always confirm before sending emails, deleting files, or any action that can't be undone.
- If you detect a potential scam, warn them clearly and firmly — this could save them thousands of dollars.
- Keep responses SHORT — 2-3 sentences max unless they ask for more detail.
- If they seem frustrated, slow down and offer encouragement.
- Never use jargon. Never show error codes or technical messages.
- Use warm greetings: "Hi there!" not "Hello, how may I assist you today?"
- USE YOUR TOOLS when the user asks for help with files, printing, or apps. Don't just describe — actually do it.
"""


def _build_system_prompt() -> str:
    """Build the system prompt with today's date injected."""
    now = datetime.now()
    today_date = now.strftime("%A, %B %d, %Y")
    session_date = f"{now.month}_{now.day}_{now.strftime('%y')}"
    return _SYSTEM_PROMPT_BASE.format(today_date=today_date, session_date=session_date)

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
        "name": "analyze_scam_risk",
        "description": "Analyze any content for scam indicators. Use this on suspicious emails, links, phone messages, or popups. Returns risk level and plain-language explanation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "The text to analyze (email body, URL, phone message, popup text)"},
                "content_type": {"type": "string", "description": "What kind of content: 'email', 'link', 'phone', 'popup'", "default": "email"},
            },
            "required": ["content"],
        },
    },
    {
        "name": "troubleshoot_printer",
        "description": "Check why the printer isn't working. Diagnoses offline printer, stuck jobs, wrong default printer. Use when the user says 'my printer isn't working' or 'I can't print'.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "save_document_as_pdf",
        "description": "Save the currently open Word document as a PDF. The document must already be open in Word. Use when the user wants to convert a Word doc to PDF.",
        "input_schema": {
            "type": "object",
            "properties": {
                "save_path": {"type": "string", "description": "Full path where to save the PDF (e.g., 'C:\\Users\\grego\\Desktop\\Letter.pdf')"},
            },
            "required": ["save_path"],
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
        "name": "read_my_screen",
        "description": "Take a screenshot of the user's screen so you can SEE what they see. Use when they say 'what's on my screen?', 'I see a popup', 'something appeared', 'what does this error say?', 'what should I click?', or 'I don't know what I'm looking at'. This lets you actually look at their screen and give specific help.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "verify_screen_step",
        "description": "Take a screenshot to verify the user completed a step. Use after giving instructions to check it worked — like looking over their shoulder. For example, after saying 'click Send', verify the email was sent. Returns what's on screen with verification guidance.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expected": {
                    "type": "string",
                    "description": "What should be visible (e.g., 'Word document is open', 'email was sent', 'printer dialog appeared')",
                },
            },
            "required": ["expected"],
        },
    },
    {
        "name": "check_system_health",
        "description": "Check why the computer is slow or acting up. Shows memory usage, hard drive space, and which programs are using the most resources. Use when they say 'my computer is slow' or 'everything is freezing'.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "fix_frozen_program",
        "description": "Close a program that is frozen or not responding. ALWAYS confirm with the user first — they may lose unsaved work. Call without confirm first to check, then with confirm=True to close.",
        "input_schema": {
            "type": "object",
            "properties": {
                "program_name": {
                    "type": "string",
                    "description": "Name of the frozen program (e.g., 'Word', 'Chrome', 'Notepad')",
                },
                "confirm": {
                    "type": "boolean",
                    "description": "Set to true to actually close the program. False just checks if it's running.",
                    "default": False,
                },
            },
            "required": ["program_name"],
        },
    },
    {
        "name": "check_internet",
        "description": "Check if the internet is working and diagnose WiFi problems. Use when they say 'internet isn't working', 'WiFi is down', or 'pages won't load'.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "smart_save_document",
        "description": "Save content as a clearly named document with date and time stamp. Use whenever the user creates, downloads, or works on a document. Puts it in Documents/TechBuddy Saved with a clear name they can find later.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The text content to save",
                },
                "doc_type": {
                    "type": "string",
                    "description": "Type: 'note', 'letter', 'list', 'instructions', 'recipe', 'other'",
                    "default": "note",
                },
                "title": {
                    "type": "string",
                    "description": "Short title (e.g., 'Grocery List', 'Letter to Sarah'). Auto-generates if empty.",
                    "default": "",
                },
            },
            "required": ["content"],
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
        "description": "Send an email to someone. Can include a file attachment. Always confirm the recipient and message with the user before sending.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Email address to send to"},
                "subject": {"type": "string", "description": "Subject line"},
                "body": {"type": "string", "description": "The message to send"},
                "attachment": {"type": "string", "description": "Full path to a file to attach (optional)", "default": ""},
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
    {
        "name": "download_attachment",
        "description": "Download an attachment from an email and save it to Downloads folder. Use when the user wants to open or save a file from an email.",
        "input_schema": {
            "type": "object",
            "properties": {
                "email_id": {"type": "integer", "description": "The email number that has the attachment"},
                "attachment_name": {"type": "string", "description": "Name of the attachment to download (optional — downloads first one if not specified)", "default": ""},
            },
            "required": ["email_id"],
        },
    },
    {
        "name": "find_photos",
        "description": "Find photos on the computer by name or date. Use when the user says 'find my photos' or 'where are my vacation pictures?'",
        "input_schema": {
            "type": "object",
            "properties": {
                "search_term": {"type": "string", "description": "What to search for (e.g., 'vacation', 'grandkids')", "default": ""},
                "days_back": {"type": "integer", "description": "How many days back to look (0 = search by name only)", "default": 0},
            },
        },
    },
    {
        "name": "share_photo",
        "description": "Email a photo to someone. Always confirm with the user before sending.",
        "input_schema": {
            "type": "object",
            "properties": {
                "photo_path": {"type": "string", "description": "Full path to the photo"},
                "to_email": {"type": "string", "description": "Email address to send the photo to"},
            },
            "required": ["photo_path", "to_email"],
        },
    },
    {
        "name": "check_for_meeting_links",
        "description": "Check emails for video call links (Zoom, Google Meet, Teams). Use when the user asks about meetings or calls.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "join_video_call",
        "description": "Help the user join a video call by opening the meeting link and giving step-by-step instructions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "meeting_link": {"type": "string", "description": "The meeting URL (Zoom, Meet, or Teams link)"},
            },
            "required": ["meeting_link"],
        },
    },
    {
        "name": "search_web",
        "description": "Search the internet for information. Use when you need to look something up — phone numbers, organizations, how-to info, scam reports, or anything the user asks about. Always summarize results in simple language.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to search for (e.g., 'IRS phone number', 'CVS pharmacy hours')"},
                "num_results": {"type": "integer", "description": "How many results (1-5)", "default": 3},
            },
            "required": ["query"],
        },
    },
    {
        "name": "save_note",
        "description": "Save a note about the user on their computer. Use to remember preferences, contacts, routines, and session history. Notes are private — stored locally, never in the cloud.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Note name (e.g., 'preferences', 'contacts', 'session-2_12_26')"},
                "content": {"type": "string", "description": "What to save (plain text)"},
            },
            "required": ["filename", "content"],
        },
    },
    {
        "name": "read_notes",
        "description": "Read a saved note file, or list all available notes. Use to recall what you know about this person.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Note to read (e.g., 'preferences'). Leave empty to list all.", "default": ""},
            },
        },
    },
    {
        "name": "recall_user_context",
        "description": "Remember what you know about this person by reading saved notes. Call this at the start of each conversation to restore context — preferences, contacts, and recent session history.",
        "input_schema": {
            "type": "object",
            "properties": {},
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
    "troubleshoot_printer": troubleshoot_printer,
    "analyze_scam_risk": analyze_scam_risk,
    "click_button": click_button,
    "type_text": type_text,
    "save_document_as_pdf": save_document_as_pdf,
    "describe_screen_action": describe_screen_action,
    "read_my_screen": read_my_screen,
    "verify_screen_step": verify_screen_step,
    "check_system_health": check_system_health,
    "fix_frozen_program": fix_frozen_program,
    "check_internet": check_internet,
    "smart_save_document": smart_save_document,
    "check_email": check_email,
    "read_email": read_email,
    "send_email": send_email,
    "delete_email": delete_email,
    "download_attachment": download_attachment,
    "find_photos": find_photos,
    "share_photo": share_photo,
    "check_for_meeting_links": check_for_meeting_links,
    "join_video_call": join_video_call,
    "search_web": search_web,
    "save_note": save_note,
    "read_notes": read_notes,
    "recall_user_context": recall_user_context,
}


def execute_tool(name: str, input_data: dict) -> str | list:
    """Execute a dispatch tool and return its result.

    Returns either a string (most tools) or a list of content blocks
    (vision tool returns image + text).
    """
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
        elif block.type == "thinking":
            entry = {"type": "thinking", "thinking": block.thinking}
            if hasattr(block, "signature") and block.signature:
                entry["signature"] = block.signature
            result.append(entry)
    return result


def _extract_tool_thinking(text: str) -> str:
    """Extract thinking trace from tool result markers."""
    match = re.search(r'\[THINKING_TRACE\](.*?)\[/THINKING_TRACE\]', text, re.DOTALL)
    return match.group(1) if match else ""


def _strip_tool_thinking(text: str) -> str:
    """Remove thinking trace markers from text."""
    return re.sub(r'\[THINKING_TRACE\].*?\[/THINKING_TRACE\]', '', text, flags=re.DOTALL).strip()


def _compact_history(history: list) -> list:
    """Compact history to fit in session cookie (~4KB limit).

    Keeps full detail for the latest exchange (so tool-use pairs stay valid).
    Strips thinking/tool blocks from older messages, keeping only text.
    """
    if len(history) <= 4:
        return history

    # Find where the last user text message starts (= latest exchange)
    last_user_idx = 0
    for i in range(len(history) - 1, -1, -1):
        if history[i]["role"] == "user" and isinstance(history[i].get("content"), str):
            last_user_idx = i
            break

    compact = []
    for i, msg in enumerate(history):
        if i >= last_user_idx:
            # Keep latest exchange in full detail (tool pairs intact)
            compact.append(msg)
        elif msg["role"] == "user" and isinstance(msg.get("content"), str):
            compact.append(msg)
        elif msg["role"] == "assistant":
            content = msg.get("content")
            if isinstance(content, str):
                compact.append(msg)
            elif isinstance(content, list):
                # Extract just text from older assistant messages
                texts = [b["text"] for b in content if b.get("type") == "text"]
                if texts:
                    compact.append({"role": "assistant", "content": " ".join(texts)})
        # Drop old tool_result user messages (they're huge and no longer needed)

    # Cap at ~16 entries to stay under 4KB
    if len(compact) > 16:
        compact = compact[-16:]
        # Ensure starts with user message
        while compact and compact[0]["role"] != "user":
            compact = compact[1:]

    return compact


def call_claude(history: list) -> tuple[str, str, list]:
    """Call Claude API with tool use and extended thinking.

    Returns (final_text, thinking_text, updated_history).

    Uses extended thinking so Claude reasons before responding.
    Uses prompt caching for the system prompt.
    Handles structured tool results (vision returns image content blocks).
    """
    MAX_TOOL_ROUNDS = 5

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=16000,
            thinking={"type": "adaptive"},
            system=[{
                "type": "text",
                "text": _build_system_prompt(),
                "cache_control": {"type": "ephemeral"},
            }],
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
            # No tools — extract text and thinking, then return
            text_blocks = [b.text for b in assistant_content if b.type == "text"]
            thinking_blocks = [b.thinking for b in assistant_content if b.type == "thinking"]
            reply_text = " ".join(text_blocks) if text_blocks else "Done!"
            thinking_text = "\n".join(thinking_blocks) if thinking_blocks else ""
            return reply_text, thinking_text, history

        # Execute each tool and build tool results
        tool_results = []
        for tool_use in tool_uses:
            result = execute_tool(tool_use.name, tool_use.input)

            # Handle structured content (vision tool returns list of blocks)
            if isinstance(result, list):
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result,
                })
            else:
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result,
                })

        # Feed results back to Claude
        history.append({"role": "user", "content": tool_results})

    # If we hit max rounds, return what we have
    return "I'm still working on that. Could you tell me more about what you need?", "", history


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

    thinking_text = ""
    try:
        assistant_text, thinking_text, history = call_claude(history)
    except anthropic.AuthenticationError:
        assistant_text = "I'm having trouble connecting right now. Let's try again in a moment."
        history.append({"role": "assistant", "content": assistant_text})
    except Exception:
        assistant_text = "Something went wrong on my end. Let's try that again."
        history.append({"role": "assistant", "content": assistant_text})

    # Extract thinking traces embedded in tool results (scam analysis)
    tool_thinking = _extract_tool_thinking(assistant_text)
    if tool_thinking:
        assistant_text = _strip_tool_thinking(assistant_text)
        if not thinking_text:
            thinking_text = tool_thinking

    session["history"] = _compact_history(history)

    response_data = {"reply": assistant_text}
    if thinking_text:
        response_data["thinking"] = thinking_text
    return jsonify(response_data)


# --- Family SMS Remote Control ---

DESTRUCTIVE_KEYWORDS = ["delete", "remove", "cancel", "unsubscribe", "erase"]


def process_family_sms(contact: dict, message: str) -> str:
    """Process an SMS from a family member through the Claude tool-use loop.

    Returns the reply text to send back to the family member via SMS.
    Also pushes the interaction to the elderly person's chat window.
    """
    name = contact["name"]
    relationship = contact["relationship"]

    # Block destructive actions if not authorized
    if any(kw in message.lower() for kw in DESTRUCTIVE_KEYWORDS):
        if not contact.get("can_delete", False):
            return (
                f"Hi {name}, I can't do that through SMS for safety reasons. "
                f"Please help your mom in person or ask her directly."
            )

    # Build context-enriched message for Claude
    context_prefix = (
        f"[FAMILY REMOTE REQUEST from {name} ({relationship}) via SMS]\n"
        f"Permissions: execute={contact['can_execute']}, "
        f"view_status={contact['can_view_status']}, "
        f"delete={contact['can_delete']}\n"
        f"Their message: {message}\n\n"
        f"IMPORTANT: After completing this request, explain what you did "
        f"as if talking to {name} (the family member), not the elderly user. "
        f"Keep it brief — this goes back as an SMS (under 300 chars ideal). "
        f"Also tell the elderly user what happened in a warm, reassuring way."
    )

    # Each SMS is a standalone conversation (not tied to elderly's session)
    history = [{"role": "user", "content": context_prefix}]

    try:
        assistant_text, _, history = call_claude(history)
    except Exception:
        assistant_text = (
            f"Hi {name}, I had trouble with that request. "
            f"I'll let your mom know you tried to help."
        )

    # Log for audit trail
    _family_sms_log.append({
        "from": name,
        "relationship": relationship,
        "message": message,
        "reply": assistant_text,
        "timestamp": datetime.now().isoformat(),
    })

    # Push to elderly person's chat window
    _pending_family_messages.append({
        "from_name": name,
        "from_relationship": relationship,
        "original_message": message,
        "result": assistant_text,
    })

    return assistant_text


@app.route("/sms/simulate", methods=["POST"])
def sms_simulate():
    """Simulated SMS endpoint for demo mode — bypasses Twilio entirely."""
    data = request.get_json()
    from_number = data.get("from_number", "")
    body = data.get("message", "").strip()

    if not body:
        return jsonify({"reply": "I didn't get a message. Try again?", "error": True})

    contact = FAMILY_CONTACTS.get(from_number)
    if not contact:
        return jsonify({
            "reply": "Sorry, this number isn't authorized for TechBuddy.",
            "error": True,
        })

    reply_text = process_family_sms(contact, body)

    # Truncate for SMS realism (1600 char Twilio limit)
    if len(reply_text) > 1500:
        reply_text = reply_text[:1497] + "..."

    return jsonify({"reply": reply_text})


@app.route("/sms/incoming", methods=["POST"])
def sms_incoming():
    """Twilio webhook — receives incoming SMS from family members.

    Expects form-encoded POST from Twilio. Returns TwiML XML.
    Only works when Twilio is configured; otherwise use /sms/simulate.
    """
    from_number = request.form.get("From", "")
    body = request.form.get("Body", "").strip()

    # Build TwiML response
    def twiml_reply(msg):
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f"<Response><Message>{msg}</Message></Response>"
        ), 200, {"Content-Type": "text/xml"}

    if not body:
        return twiml_reply("I didn't get a message. Try again?")

    contact = FAMILY_CONTACTS.get(from_number)
    if not contact:
        return twiml_reply(
            "Sorry, this number isn't authorized for TechBuddy. "
            "Ask your family member to add you."
        )

    reply_text = process_family_sms(contact, body)

    if len(reply_text) > 1500:
        reply_text = reply_text[:1497] + "..."

    return twiml_reply(reply_text)


@app.route("/family/messages", methods=["GET"])
def family_messages():
    """Polling endpoint — returns pending family messages for the chat UI."""
    messages = list(_pending_family_messages)
    _pending_family_messages.clear()
    return jsonify({"messages": messages})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
