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

## Day 2 (Feb 13) — Modules 1-3
- [ ] Email assistant (read, send, scam detection)
- [ ] Files assistant (find, open, organize)
- [ ] Printing helper (print, troubleshoot)

## Day 3 (Feb 14) — Modules 4-5 + Integration
- [ ] Photo manager (find, view, share)
- [ ] Video call helper (join Zoom/Meet/FaceTime)
- [ ] End-to-end testing across modules

## Day 4 (Feb 15) — Demo + Polish
- [ ] Progressive demo: story layer → API layer → wow layer → architecture layer
- [ ] OBS backup recording
- [ ] Accessibility audit (full checklist)
- [ ] README for judges

## Day 5 (Feb 16) — Submit by 3pm EST
- [ ] Final demo recording
- [ ] GitHub repo cleanup
- [ ] Submit to hackathon
