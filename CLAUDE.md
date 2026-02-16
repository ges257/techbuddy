<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=FFCCBC&fontColor=3E2723&height=180&section=header&text=CLAUDE.md&fontSize=45&fontAlignY=35&descAlignY=55&desc=The%20Project%20Blueprint&descSize=16&animation=fadeIn" width="100%"/>
</p>

> This file is loaded automatically by Claude Code at the start of every session. It defines the project's architecture, accessibility standards, coding conventions, and hard-won gotchas. It's the project's DNA.

<p align="center">
  <a href="README.md">README</a> · <a href="ARCHITECTURE.md">Architecture</a> · <a href="CHALLENGES.md">Challenges</a> · <a href="LEARNINGS.md">Learnings</a> · <a href="CLAUDE_CODE.md">Claude Code</a>
</p>

---

# TechBuddy — Claude Code for Elderly People

## What This Is
AI chat assistant helping elderly people use their computer through natural conversation. 5 modules: email, files, printing, photos, video calls. Plus Scam Shield active protection layer + Vision (screen reading). Chat window UI with voice input/TTS.

## Architecture
- Frontend: Flask chat window (big text, voice via Web Speech API, TTS via Kokoro on WSL port 5050 with browser fallback)
- Backend: Claude API (Opus 4.6) with extended thinking + prompt caching, 35 tools via direct tool-use loop (up to 10 rounds)
- Dispatch layer in `mcp_servers/screen_dispatch.py`: 35 tools with tiered fallback: win32com (Tier 1) → pywinauto (Tier 2) → existing MCP (Tier 3) → Claude Vision (Tier 4, read_my_screen captures screenshots)
- iOS Phone Control: `capture_phone_screen()`, `tap_phone_screen()`, `open_phone_app()` — via MacinCloud iOS Simulator + Cloudflare Tunnel. Mac Flask server at `PHONE_SERVER_URL` runs xcrun simctl commands.
- System Troubleshooting: `check_system_health()` (memory/disk/CPU), `fix_frozen_program()` (kill stuck apps w/ confirm), `check_internet()` (ping + WiFi diagnostics) — all via PowerShell
- Smart Document Saving: `smart_save_document()` auto-names files with date/time stamp, saves to `Documents/TechBuddy Saved/`
- Save as Word: `save_document_as_word()` saves current Word doc as .docx to a specified path
- Proactive Troubleshooting: system prompt instructs Claude to offer screen reading when user seems confused + `verify_screen_step()` tool verifies steps were completed via screenshot
- Web Search: DuckDuckGo search (no API key) via `search_web()` tool + `_web_verify_scam()` auto-verification in scam analysis
- Date Awareness: `_build_system_prompt()` injects today's date into system prompt
- Local Memory: `save_note()`, `read_notes()`, `recall_user_context()` — .md files in `~/TechBuddy Notes/` (private, never in cloud)
- Scam Shield: 3-layer protection — `_scan_for_scam()` keyword pre-filter → `_web_verify_scam()` internet verification → extended thinking deep analysis via inner API call. `analyze_scam_risk()` tool, auto-scan on email read
- Extended Thinking: `thinking={"type": "adaptive"}` on main loop and scam analysis inner call
- Prompt Caching: `cache_control: {"type": "ephemeral"}` on system message for faster repeat interactions
- Vision: `read_my_screen()` captures screenshot via PIL.ImageGrab, returns base64 to Claude Vision for screen analysis
- Real Gmail IMAP: `check_email()` and `read_email()` connect via imaplib with app password. Folder `"Tech Buddy Demo"` (IMAP name for `label:tech-buddy-demo`). `SINCE` date limit prevents >1MB crash. No simulated fallback when Gmail is configured — returns error instead. Simulated inbox only used when `USE_REAL_GMAIL=False`.
- Session Cookie: `_strip_image_data()` replaces base64 screenshots with `[screenshot taken]` to prevent Flask cookie overflow
- Word Typing: `type_text()` uses win32com `Selection.TypeText()` for Word documents (bypasses pywinauto focus issues)
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
- Test: `cd ~/techbuddy && venv/bin/pytest tests/ -v` (139 passed, 4 skipped)
- iOS Simulator demo apps (working): settings, messages, safari, photos, calendar, maps
- iOS Simulator apps NOT available: mail, phone, camera, notes
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
- Simulated inbox has 6 emails with attachments and meeting links — email #5 is a scam for demo (only active when USE_REAL_GMAIL=False)
- Real Gmail: IMAP folder name is `"Tech Buddy Demo"` (with spaces, quoted). Gmail search label `label:tech-buddy-demo` auto-converts to IMAP folder `Tech Buddy Demo`. imaplib has known bug (cpython #90378) with spaces — must quote folder name. SEARCH limited to SINCE (yesterday) to avoid >1MB imaplib crash.
- Real Zoom PMI: 367 817 4163 (in Dr. Johnson email #3)
- Gmail .env vars: `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `GMAIL_FOLDER=Tech Buddy Demo` — only set on Windows .env, NOT WSL (WSL tests use simulated inbox)
- type_text for Word: win32com `Selection.TypeText()` preferred over pywinauto for Word windows — more reliable cursor focus
- All Gmail print statements use `flush=True` for Flask console visibility

## When Compacting
Preserve: modified files list, current module being worked on, which subagents are done vs pending, the tiered fallback architecture, accessibility standards.

---

<p align="center">
  <a href="README.md">README</a> · <a href="ARCHITECTURE.md">Architecture</a> · <a href="CHALLENGES.md">Challenges</a> · <a href="LEARNINGS.md">Learnings</a> · <a href="CLAUDE_CODE.md">Claude Code</a>
</p>

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=FFCCBC&height=100&section=footer" width="100%"/>
</p>
