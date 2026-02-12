# TechBuddy — Claude Code for Elderly People

## What This Is
AI chat assistant helping elderly people use their computer through natural conversation. 5 modules: email, files, printing, photos, video calls. Chat window UI with voice input/TTS.

## Architecture
- Frontend: Flask chat window (big text, voice via Web Speech API, TTS via Speech Synthesis)
- Backend: Claude API (Opus 4.6) as intent router, delegates to specialized subagents
- 5 subagents in `.claude/agents/`: email-assistant, files-assistant, printing-helper, photo-manager, video-call-helper
- Dispatch layer in `mcp_servers/screen_dispatch.py`: win32com (Tier 1) → pywinauto (Tier 2) → existing MCP (Tier 3) → Claude Vision text instructions (Tier 4)
- Hooks in `.claude/settings.json`: PreToolUse (validate sends), PostToolUse (a11y check), SessionStart (git status + TODO), Stop (safety verify)
- MCP config in `.mcp.json`: filesystem, google-workspace, playwright, screen-dispatch, sms-provider

## Accessibility Standards (Non-Negotiable)
- Min font: 18px
- Min touch target: 48px
- Min contrast ratio: 4.5:1
- Plain language only — no jargon ever
- Max 3 steps to any feature
- Always confirm before: sending, deleting, financial actions
- Error messages are elderly-friendly (no tracebacks, no technical terms)

## Coding Conventions
- Python 3.11+ with type hints
- Async where possible (asyncio)
- MCP servers use `from mcp import Server`
- All user-facing text goes through elderly-prompt skill formatting
- Tool names must be dead obvious — no ambiguous or overlapping names

## Commands
- Run frontend: `python frontend/app.py`
- Run MCP server: `python mcp_servers/<server>.py`
- Test: `pytest tests/`
- Lint: `ruff check .`

## Project Gotchas
- Computer Use API scores 22% on desktop — never depend on it, always use tiered fallback
- win32com only works on Windows — test on WSL2 carefully
- Hook scripts: JSON on stdin, JSON on stdout, exit code 2 = block action
- Hooks go in `.claude/settings.json` NOT a separate hooks.json file
- Subagent configs do NOT have inline hooks — hooks fire from settings level for all agents
- `PostToolUseFailure` does NOT exist — use `PostToolUse` and check for errors
- MCP tool matcher format: `mcp__servername__toolname`
- Keep enabled MCP servers to 5-6 max to avoid context bloat

## When Compacting
Preserve: modified files list, current module being worked on, which subagents are done vs pending, the tiered fallback architecture, accessibility standards.
