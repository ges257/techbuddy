# Generate Module

Scaffold a new TechBuddy module (subagent + MCP tools + tests + frontend integration).

## Steps
1. Create subagent file in `.claude/agents/<module-name>.md` with:
   - YAML frontmatter: name, description, model: sonnet, permissionMode: acceptEdits, relevant skills
   - Markdown body: approach, common requests, safety considerations
2. Create MCP tool functions in `mcp_servers/` or add to existing server
3. Create test file in `tests/test_<module-name>.py`
4. Add route/handler in `frontend/app.py` if needed
5. Update `TODO.md` with the new module status

## Subagent Template
```markdown
---
name: <module-name>
description: <one-line description>
model: sonnet
permissionMode: acceptEdits
skills:
  - elderly-prompt
---

You help elderly users with <task>. <emotional context>.

APPROACH:
- <step 1>
- <step 2>

COMMON REQUESTS:
- "<request>" -> <action>

SAFETY:
- <safety consideration>
```

## Conventions
- Tool names must be dead obvious to the model
- No overlapping functionality with existing modules
- All user-facing text through elderly-prompt formatting
- Include at least 3 common requests with actions
