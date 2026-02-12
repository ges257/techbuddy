# TechBuddy — Claude Code for Elderly People

## What This Is
AI chat assistant helping elderly people use their computer through natural conversation. 5 modules: email, files, printing, photos, video calls. Plus Scam Shield active protection layer + Vision (screen reading). Chat window UI with voice input/TTS.

## Architecture
- Frontend: Flask chat window (big text, voice via Web Speech API, TTS via Speech Synthesis)
- Backend: Claude API (Opus 4.6) with extended thinking + prompt caching, 26 tools via direct tool-use loop (up to 5 rounds)
- Dispatch layer in `mcp_servers/screen_dispatch.py`: 26 tools with tiered fallback: win32com (Tier 1) → pywinauto (Tier 2) → existing MCP (Tier 3) → Claude Vision (Tier 4, read_my_screen captures screenshots)
- Proactive Troubleshooting: system prompt instructs Claude to offer screen reading when user seems confused + `verify_screen_step()` tool verifies steps were completed via screenshot
- Web Search: DuckDuckGo search (no API key) via `search_web()` tool + `_web_verify_scam()` auto-verification in scam analysis
- Date Awareness: `_build_system_prompt()` injects today's date into system prompt
- Local Memory: `save_note()`, `read_notes()`, `recall_user_context()` — .md files in `~/TechBuddy Notes/` (private, never in cloud)
- Scam Shield: 3-layer protection — `_scan_for_scam()` keyword pre-filter → `_web_verify_scam()` internet verification → extended thinking deep analysis via inner API call. `analyze_scam_risk()` tool, auto-scan on email read
- Extended Thinking: `thinking={"type": "adaptive"}` on main loop and scam analysis inner call
- Prompt Caching: `cache_control: {"type": "ephemeral"}` on system message for faster repeat interactions
- Vision: `read_my_screen()` captures screenshot via PIL.ImageGrab, returns base64 to Claude Vision for screen analysis
- Thinking trace UI: collapsible "See what I was considering..." section under assistant messages
- Hooks in `.claude/settings.json`: PreToolUse (validate sends), PostToolUse (a11y check), SessionStart (git status + TODO), Stop (safety verify)
- 5 subagent configs in `.claude/agents/` (for Claude Code context, not runtime delegation)
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
- Run frontend: `cd ~/techbuddy && venv/bin/python frontend/app.py` → http://localhost:5000
- Run on Windows: `cd C:\Users\grego\techbuddy && venv\Scripts\python frontend\app.py`
- Test: `cd ~/techbuddy && venv/bin/pytest tests/ -v` (122/122 passing)
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
- Scam Shield scoring: `_scan_for_scam()` returns SAFE (0 flags), SUSPICIOUS (1-2), DANGEROUS (3+ or financial/tech_support present)
- Notes directory: `~/TechBuddy Notes/` (Windows: `C:\Users\grego\TechBuddy Notes\`); on WSL uses WIN_HOME
- Web search: duckduckgo_search library renamed to ddgs (warning is cosmetic, works fine)
- WSL path detection: `IS_WSL` flag auto-detects, `WIN_HOME` points to `/mnt/c/Users/grego/`
- Simulated inbox has 6 emails with attachments and meeting links — email #5 is a scam for demo
- Real Zoom PMI: 367 817 4163 (in Dr. Johnson email #3)

## When Compacting
Preserve: modified files list, current module being worked on, which subagents are done vs pending, the tiered fallback architecture, accessibility standards.
