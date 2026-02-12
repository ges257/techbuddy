# TechBuddy — Build TODO

## Day 0 (Feb 11) — Setup
- [x] Project scaffold (dirs, git init)
- [x] CLAUDE.md
- [x] .claude/settings.json (hooks + permissions)
- [x] .claude/rules/ (3 files)
- [x] .claude/agents/ (5 subagents)
- [x] skills/ (4 SKILL.md files)
- [x] .mcp.json (MCP config)
- [x] TODO.md
- [x] Git commit + GitHub repo

## Day 1 (Feb 11-12) — Core Infrastructure
- [x] Frontend: Flask chat window (big text, voice input, TTS)
- [x] Backend: Claude API intent router (tool-use loop, 5 rounds max)
- [x] Dispatch layer: mcp_servers/screen_dispatch.py (8 tools, tiered fallback)
- [x] Hook scripts: validate_send.py, accessibility_check.py, verify_elderly_safe.py
- [x] Test suite: 30/30 pytest (hooks, dispatch, Flask app)

## Day 2 (Feb 12-13) — All 5 Modules + Demo Scenarios
- [x] Email assistant (check, read, send, delete + scam detection)
- [x] Files assistant (find_file, find_recent, open, list — done in Day 1)
- [x] Printing helper (print_document — done in Day 1)
- [x] Photo manager (find_photos, share_photo via email)
- [x] Video call helper (check_for_meeting_links, join_video_call)
- [x] 4 demo scenarios: Word→PDF→Email, printer troubleshoot, email attachment→open, Zoom invite
- [x] New tools: save_document_as_pdf, troubleshoot_printer, download_attachment
- [x] Enhanced: send_email with attachments, inbox with attachments + meeting links
- [x] Scam Shield: analyze_scam_risk, auto-scan emails, block dangerous files, validate URLs
- [x] Real Zoom PMI link (367 817 4163) in Dr. Johnson email
- [x] Tests: 64/64 passing
- [x] All work committed and pushed (c423265)
- [x] Family SMS Remote Control: demo panel, authorization, polling, Twilio webhook (e026297)
- [x] Tests: 80/80 passing
- [ ] End-to-end integration testing on Windows
- [ ] Polish + edge cases

## Day 3 (Feb 12-13) — Opus 4.6 Power Features
- [x] Prompt caching (cache_control on system message)
- [x] Extended thinking on main call_claude() loop (budget_tokens: 8000)
- [x] UI: collapsible thinking trace display
- [x] Vision: read_my_screen() tool (PIL screenshot → Claude Vision)
- [x] Extended thinking for scam analysis (inner API call with thinking)
- [x] Web search: search_web() via DuckDuckGo (no API key needed)
- [x] Web-verified scam analysis: _web_verify_scam() auto-checks orgs/phones/domains
- [x] Date awareness: _build_system_prompt() injects today's date
- [x] Local memory: save_note(), read_notes(), recall_user_context() — .md notes on user's PC
- [x] Tests: 117/117 passing (92 → 117)
- [ ] End-to-end Windows testing (all features including vision + thinking + web search + memory)
- [ ] UI polish (loading states, branding, thinking display)

## Day 4 (Feb 15) — Demo + Polish
- [ ] README.md for judges
- [ ] LICENSE (MIT) + .env.example
- [ ] Progressive demo: story layer → API layer → wow layer → architecture layer
- [ ] OBS backup recording
- [ ] Written summary (100-200 words)

## Day 5 (Feb 16) — Submit by 3pm EST
- [ ] Final demo recording
- [ ] GitHub repo cleanup
- [ ] Submit to hackathon
