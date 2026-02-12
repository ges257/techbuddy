---
paths:
  - "mcp_servers/**"
---
# MCP Server Rules
- Use `from mcp import Server` — standard MCP package only
- Tool names must be DEAD OBVIOUS to the model — no ambiguity
- Ask: "Would Claude pick the right tool from this name alone?"
- Tool descriptions: 3-4+ sentences minimum explaining what it does and when to use it
- No overlapping tool functionality — the #1 failure mode for tool selection
- Return structured data (dicts/lists), not prose
- Handle errors gracefully — return elderly-friendly error messages
- Each tool should do one thing well
- Tiered fallback pattern: try direct API first, then UI automation, then vision
