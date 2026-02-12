# TechBuddy — Build Log
**Last updated:** February 11, 2026 — 8:56 PM EST

---

## Competition
- **Event:** "Built with Opus 4.6: a Claude Code Hackathon" (Feb 10–16, 2026)
- **Deadline:** Monday Feb 16, 3:00 PM EST
- **Problem:** Statement 2 — Break the Barriers (digital divide for elderly)
- **Prizes:** $50K first, $25K second, $10K third
- **Judging:** Demo 30%, Impact 25%, Opus 4.6 Use 25%, Depth & Execution 20%
- **GitHub:** https://github.com/ges257/techbuddy

---

## Day 0 — Setup (Feb 11, afternoon)

### Research Completed
- 13 Anthropic docs synthesized (context engineering, hooks, skills, multi-agent, prompting)
- Boris Cherny (Claude Code creator) workflow analysis
- Cat Wu (Claude Code Product Lead) hackathon AMA — key insights:
  - Claude Code Guide Agent = most underused feature
  - Tool names must be DEAD OBVIOUS
  - Meta-prompting works better than direct prompting
  - Less scaffolding = better results (removed 30-40% → improved quality)
- Computer Use API limitations researched (22% desktop reliability)
- Designed tiered fallback: win32com → pywinauto → MCP → Claude Vision
- Plan evolved through 5 versions (v1→v5)

### Reference Documents (at `/home/schwartzlabs.ai/02_projects/hackathon/`)
| Document | File |
|----------|------|
| Final build plan | `techbuddy-v5-2_11_26_6-08pm.md` |
| Dev environment setup plan | `claude-code-setup-plan-2_11_26_6-31pm.md` |
| Best practices research | `bestpractices-research-2_11_26_4-44pm.md` |
| Computer Use workarounds | `improvements_workarounds_to_v4-2_11_26_5-58pm.md` |
| Cat Wu AMA notes | `mor aboyt primitritives.md` |
| Day 0 completion summary | `day0-setup-complete-2_11_26_8-44pm.md` |

### Claude Code Config Created (10 phases, all complete)
1. **CLAUDE.md** — 48-line project context (architecture, a11y standards, gotchas)
2. **`.claude/settings.json`** — 4 hook types + 14 permission allows + 4 denies
3. **`.claude/rules/`** — 3 path-conditional rule files (accessibility, mcp-servers, hooks)
4. **`.claude/agents/`** — 5 subagent files (email, files, printing, photos, video calls)
5. **`skills/`** — 4 SKILL.md files (accessibility-check, safety-validation, generate-module, elderly-prompt)
6. **`.mcp.json`** — MCP config (filesystem + screen-dispatch)
7. **`TODO.md`** — Build schedule (injected by SessionStart hook)
8. **Git + GitHub** — Repo at `ges257/techbuddy`, initial commit `7f456fd`

### All 7 Claude Code Primitives Used
| Primitive | Status | Files |
|-----------|--------|-------|
| CLAUDE.md | Done | `CLAUDE.md` |
| Rules | Done | `.claude/rules/` (3 files) |
| Hooks | Configured | `.claude/settings.json` (scripts TBD) |
| Skills | Done | `skills/` (4 dirs) |
| Subagents | Done | `.claude/agents/` (5 files) |
| MCP Servers | Configured | `.mcp.json` |
| Agent Teams | Aware | Documented, not using (experimental) |

---

## Day 1 — Chunk 1: Flask Chat + Claude API (Feb 11, evening)

### What Was Built
A working Flask chat window that talks to Claude API as TechBuddy.

### Environment Setup
- Python 3.12.3 virtualenv at `~/techbuddy/venv/`
- Installed: flask 3.1.2, anthropic 0.79.0, python-dotenv 1.2.1
- API key stored in `.env` (gitignored)

### Files Created
| File | Purpose |
|------|---------|
| `frontend/app.py` | Flask app — `/` serves UI, `/chat` calls Claude API |
| `frontend/templates/chat.html` | Chat UI — elderly-accessible, warm colors |
| `frontend/requirements.txt` | Python dependencies |
| `.env` | ANTHROPIC_API_KEY (gitignored) |
| `venv/` | Python virtualenv (gitignored) |

### How to Run
```bash
cd ~/techbuddy
venv/bin/python frontend/app.py
# Open http://localhost:5000
```

### What It Does
- Full-page chat window at `http://localhost:5000`
- Type a message → Claude Opus 4.6 responds as TechBuddy
- TechBuddy system prompt: warm, patient, plain language, max 3 steps
- Conversation history maintained per session (multi-turn)
- Errors shown as friendly messages (no tracebacks)

### Accessibility (CSS)
- Font: 20px system font, #1a1a1a on light backgrounds
- Buttons/inputs: 60px height, 12px border-radius
- Send button: 100px+ wide, green #4CAF50
- Background: warm cream #FFF8F0
- User messages: soft blue #E3F2FD
- TechBuddy messages: warm peach #FFF3E0
- "TechBuddy is thinking..." animated indicator

### Verified Working
- [x] Flask starts without errors
- [x] Chat UI renders at localhost:5000
- [x] Message → Claude API → TechBuddy response
- [x] Response: "Hi there! I'd be happy to help you find your file!"
- [x] Multi-turn conversation works
- [x] Font ≥18px, buttons ≥48px
- [x] Graceful error handling

---

## Current Project Structure
```
~/techbuddy/
├── CLAUDE.md                          # Project context
├── TODO.md                            # Build schedule
├── SETUP-LOG.md                       # THIS FILE
├── .mcp.json                          # MCP server config
├── .env                               # API key (gitignored)
├── .gitignore                         # .env, venv, __pycache__, etc.
├── venv/                              # Python virtualenv (gitignored)
├── frontend/
│   ├── app.py                         # Flask + Claude API backend
│   ├── requirements.txt               # Python deps
│   └── templates/
│       └── chat.html                  # Chat UI
├── .claude/
│   ├── settings.json                  # Hooks + permissions
│   ├── agents/                        # 5 subagent .md files
│   └── rules/                         # 3 conditional rule files
├── skills/                            # 4 SKILL.md files
├── hooks/                             # (empty — Day 1 next)
├── mcp_servers/                       # (empty — Day 1 next)
├── demos/                             # (empty — Day 4)
└── tests/                             # (empty — Day 2+)
```

---

## What's Next

### Remaining Day 1 Tasks
- [ ] Add voice input (Web Speech API — browser-side JS)
- [ ] Add TTS for responses (Speech Synthesis API — browser-side JS)
- [ ] Backend: Claude API intent router (route to subagents)
- [ ] Dispatch layer: `mcp_servers/screen_dispatch.py`
- [ ] Hook scripts: `validate_send.py`, `accessibility_check.py`, `verify_elderly_safe.py`

### Full Schedule
- **Day 2 (Feb 13):** Modules 1-3 (email, files, printing)
- **Day 3 (Feb 14):** Modules 4-5 (photos, video calls) + integration
- **Day 4 (Feb 15):** Progressive demo + OBS backup + a11y audit
- **Day 5 (Feb 16):** Final recording + submit by 3:00 PM EST
