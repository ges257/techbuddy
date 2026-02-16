#!/usr/bin/env python3
"""Stop hook: verifies no unsafe state is left when agent completes.

Runs when Claude Code stops working on a task. Checks that nothing
dangerous was left incomplete (unsent drafts, open sensitive files, etc.).
Returns JSON on stdout. Exit 0 = OK, Exit 2 = block stop (force review).

Author: Gregory E. Schwartz
Date:   February 2026
"""
import json
import sys


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        data = {}

    # Check the stop reason and last actions
    stop_reason = data.get("stop_reason", "")
    tool_results = data.get("tool_results", [])

    warnings = []

    # Check if any recent tool calls involved sending/deleting
    for result in tool_results[-5:] if isinstance(tool_results, list) else []:
        tool_name = result.get("tool_name", "")
        if "send" in tool_name.lower() or "delete" in tool_name.lower():
            if result.get("is_error"):
                warnings.append(f"A {tool_name} action may have failed — please verify it completed safely.")

    if warnings:
        json.dump({
            "message": "Safety check before finishing:\n" + "\n".join(f"  - {w}" for w in warnings)
        }, sys.stdout)
    else:
        json.dump({"message": "All clear — nothing left incomplete."}, sys.stdout)

    sys.exit(0)


if __name__ == "__main__":
    main()
