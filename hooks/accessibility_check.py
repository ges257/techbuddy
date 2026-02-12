#!/usr/bin/env python3
"""PostToolUse hook: checks Write/Edit output for accessibility violations.

Runs after any Write or Edit tool call. Scans the file content for
common elderly-accessibility issues. Warns but does not block (exit 0).
Returns JSON on stdout with warnings if any found.
"""
import json
import sys
import re


def check_content(file_path: str, content: str) -> list[str]:
    warnings = []

    # Only check frontend-related files
    frontend_extensions = {".html", ".css", ".jsx", ".tsx", ".js"}
    if not any(file_path.endswith(ext) for ext in frontend_extensions):
        return warnings

    # Check for small font sizes
    small_fonts = re.findall(r'font-size:\s*(\d+)px', content)
    for size in small_fonts:
        if int(size) < 18:
            warnings.append(f"Font size {size}px is too small (minimum 18px for elderly users)")

    # Check for small touch targets
    small_targets = re.findall(r'(?:width|height|min-width|min-height):\s*(\d+)px', content)
    for size in small_targets:
        if int(size) < 44 and int(size) > 0:
            # Only flag button/input-related sizes
            pass  # Too many false positives on generic sizes

    # Check for jargon in user-facing strings
    jargon = ["navigate to", "authenticate", "credentials", "interface", "toggle",
              "download", "upload", "URL", "sync", "configuration"]
    content_lower = content.lower()
    for word in jargon:
        if word.lower() in content_lower:
            # Only flag if it's in a visible string (rough check: inside quotes or HTML text)
            if re.search(rf'["\'>]\s*[^<]*{re.escape(word.lower())}', content_lower):
                warnings.append(f"Found jargon '{word}' — use plain language for elderly users")

    return warnings


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        json.dump({}, sys.stdout)
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    content = tool_input.get("content", "") or tool_input.get("new_string", "")

    warnings = check_content(file_path, content)

    if warnings:
        json.dump({
            "message": "Accessibility warnings:\n" + "\n".join(f"  - {w}" for w in warnings)
        }, sys.stdout)
    else:
        json.dump({}, sys.stdout)

    # Always exit 0 — warn but don't block
    sys.exit(0)


if __name__ == "__main__":
    main()
