# Zero Protocol: Claude Code

@GEMINI.md
@Docs/AI_Context.md

## Session start
- Read the first 60 lines of `Docs/AI_Handoff.md` (the newest entry), then `git log --oneline -10` and `git status --short`. If something changed after that entry, tell the user before you continue.
- The user says "handoff" → run `/handoff`. "Catch up" → run `/catchup`.

## Claude-specific
- All Yoru animation work goes through the `yoru-animator` agent (`.claude/agents/yoru-animator.md`). Brief it leanly, one fresh agent per movement.
- When the user makes a durable decision, add it to `Docs/AI_Context.md` (Decisions) as well as to memory. Antigravity cannot see Claude's memory.
- Commit or push only when the user asks. Running `/handoff` is the user asking for the switch commit.
