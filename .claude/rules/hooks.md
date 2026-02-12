---
paths:
  - "hooks/**"
---
# Hook Script Rules
- Receive JSON on stdin (contains tool_input, tool_name, session_id, etc.)
- Return JSON on stdout
- Exit code 0 = success, continue normally
- Exit code 2 = BLOCK the action (prevents tool execution)
- Must complete within 60 seconds (default timeout)
- No interactive prompts — hooks are fully non-interactive
- No print statements outside of the JSON response
- Test with: echo '{"tool_input": {"to": "test@example.com"}}' | python hooks/script.py
- All blocking decisions must include a clear reason in the response
