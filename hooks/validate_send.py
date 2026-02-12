#!/usr/bin/env python3
"""PreToolUse hook: validates email/SMS sends before they execute.

Receives JSON on stdin with tool_name and tool_input.
Exit 0 = allow, Exit 2 = block.
Returns JSON on stdout with optional 'message' to show user.
"""
import json
import sys
import re

SCAM_PHRASES = [
    "act now", "urgent", "your account will be closed",
    "send money", "wire transfer", "gift card",
    "social security", "ssn", "verify your identity",
    "you have won", "claim your prize", "lottery",
    "irs", "tax refund", "suspended account",
]

SUSPICIOUS_DOMAINS = [
    "bit.ly", "tinyurl", "t.co", "goo.gl",
]


def check_for_scam(text: str) -> str | None:
    lower = text.lower()
    for phrase in SCAM_PHRASES:
        if phrase in lower:
            return f"This message contains '{phrase}' which is often used in scams."
    return None


def check_recipient(email: str) -> str | None:
    if not email or not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return "The email address doesn't look right. Let's double-check it."
    return None


def check_links(text: str) -> str | None:
    lower = text.lower()
    for domain in SUSPICIOUS_DOMAINS:
        if domain in lower:
            return f"This message contains a shortened link ({domain}) which could be suspicious."
    return None


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        # Can't parse input — allow but warn
        json.dump({"message": "Could not validate this action."}, sys.stdout)
        sys.exit(0)

    tool_input = data.get("tool_input", {})

    # Check recipient
    recipient = tool_input.get("to", "") or tool_input.get("recipient", "") or tool_input.get("phone", "")
    if recipient and "@" in recipient:
        issue = check_recipient(recipient)
        if issue:
            json.dump({"decision": "block", "message": issue}, sys.stdout)
            sys.exit(2)

    # Check message content for scam indicators
    body = tool_input.get("body", "") or tool_input.get("message", "") or tool_input.get("content", "")
    subject = tool_input.get("subject", "")
    full_text = f"{subject} {body}"

    scam = check_for_scam(full_text)
    if scam:
        json.dump({"decision": "block", "message": scam}, sys.stdout)
        sys.exit(2)

    link_issue = check_links(full_text)
    if link_issue:
        json.dump({"decision": "block", "message": link_issue}, sys.stdout)
        sys.exit(2)

    # All clear
    json.dump({"decision": "allow"}, sys.stdout)
    sys.exit(0)


if __name__ == "__main__":
    main()
