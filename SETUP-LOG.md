# TechBuddy Setup Log — Feb 11, 2026

## Project
TechBuddy — "Claude Code for Elderly People"
Built for: "Built with Opus 4.6: a Claude Code Hackathon" (Feb 10-16, 2026, $50K first prize)
Problem Statement 2: Break the Barriers (digital divide for elderly)

## What Was Done

### Research Phase (earlier sessions)
- Read and synthesized 13 Anthropic docs on Claude Code best practices
- Analyzed Boris Cherny's (Claude Code creator) public workflow recommendations
- Took notes from Cat Wu's (Claude Code Product Lead) live hackathon AMA
- Researched Computer Use API limitations (22% desktop reliability) and designed tiered fallback
- Studied IndyDevDan's multi-agent orchestration patterns
- Created v4 plan, analyzed corrections, produced v5 final plan

### Reference Documents Created
All saved to `/home/schwartzlabs.ai/02_projects/hackathon/`:
- `techbuddy-v5-2_11_26_6-08pm.md` — Complete v5 product build plan
- `claude-code-setup-plan-2_11_26_6-31pm.md` — Dev environment setup plan (the plan we're executing)
- `bestpractices-research-2_11_26_4-44pm.md` — 13 Anthropic docs synthesized
- `improvements_workarounds_to_v4-2_11_26_5-58pm.md` — Workarounds and scaffolding strategies
- `techbuddy-v4-analysis-2_11_26_5-15pm.md` — v4 corrections

### Setup Phases Completed

**Phase 1 — Directory Scaffold**
```
~/techbuddy/
├── .claude/
│   ├── agents/       (5 subagent files)
│   ├── rules/        (3 rule files)
│   └── settings.json (hooks + permissions)
├── skills/           (4 skill dirs with SKILL.md)
├── hooks/            (empty — scripts to be written)
├── mcp_servers/      (empty — servers to be written)
├── frontend/         (empty — UI to be built)
├── demos/            (empty — demo assets)
├── tests/            (empty — tests to be written)
└── CLAUDE.md         (project context)
```

**Phase 2 — CLAUDE.md** (53 lines)
Project context loaded every Claude Code session. Covers: architecture, accessibility standards, coding conventions, commands, gotchas, compaction instructions.

**Phase 3 — .claude/settings.json**
- 4 hook types: SessionStart (git status + TODO), PreToolUse x2 (validate sends), PostToolUse (a11y check on Write|Edit), Stop (safety verify)
- 14 permission allows (python, npm, git, pytest, ruff, etc.)
- 4 permission denies (rm -rf, force push, hard reset, .env reads)

**Phase 4 — .claude/rules/** (3 files, path-conditional)
- `accessibility.md` — triggers on frontend/**, *.html, *.css, *.jsx, *.tsx
- `mcp-servers.md` — triggers on mcp_servers/**
- `hooks.md` — triggers on hooks/**

**Phase 5 — .claude/agents/** (5 subagent files)
All use model: sonnet, permissionMode: acceptEdits

| Agent | Skills | Scope |
|-------|--------|-------|
| email-assistant | a11y-check, safety, elderly-prompt | Read/send email, scam detection |
| files-assistant | a11y-check, elderly-prompt | Find files by name/date (#1 senior pain point) |
| printing-helper | safety, elderly-prompt | Print docs, troubleshoot printer issues |
| photo-manager | a11y-check, elderly-prompt | Find/view/share photos |
| video-call-helper | elderly-prompt | Join Zoom/Meet/FaceTime, camera/mic help |

**Phase 6 — skills/** (4 SKILL.md files)

| Skill | Purpose |
|-------|---------|
| accessibility-check | Enforce 18px font, 48px targets, 4.5:1 contrast, plain language |
| safety-validation | Validate sends, flag scams, confirm deletes/financial |
| generate-module | Developer tool: scaffold new subagent + MCP + tests |
| elderly-prompt | Rewrite text for elderly — word subs, warm tone, no jargon |

## Remaining Phases
- Phase 7: Write `.mcp.json` (MCP server config)
- Phase 8: Write `TODO.md` (injected by SessionStart hook)
- Phase 9: Git commit
- Phase 10: Create GitHub repo and push

## Key Architecture Decisions
1. **Tiered fallback** (not Computer Use): win32com → pywinauto → existing MCP → Claude Vision text
2. **Claude Code primitives**: Using all 7 (CLAUDE.md, Rules, Hooks, Skills, Subagents, MCP, plus awareness of Agent Teams)
3. **Less scaffolding = better** (Cat Wu): Keep CLAUDE.md tight, don't over-specify
4. **Tool names dead obvious** (Cat Wu): #1 failure mode is overlapping/confusing tools
5. **Hooks for safety, not advisory**: Deterministic enforcement of elderly safety guardrails
