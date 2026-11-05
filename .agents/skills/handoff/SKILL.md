---
name: handoff
description: Writes the AI handoff entry, updates the shared project context and commits the switch point. Use when the user says "handoff" or is about to switch from Antigravity to Claude Code, and at the end of a work session.
---

Hand the work over to the next AI (usually Claude Code). The user invoking this skill is the request to commit the switch point.

1. Gather facts: `git status --short`, `git log --oneline` back to the last commit whose subject starts with `handoff:` (or the last 10 commits if there is none), and `git diff --stat` for uncommitted changes. Note any background job still running.
2. Add a new entry at the top of `Docs/AI_Handoff.md`, below the template and above the older entries, using the template in that file. Header: today's date and time, `Antigravity (<your model>) → Claude Code`. Under "Plan / what I did" include the plan or walkthrough summary you followed in this session. About 20 lines at most: commit range and file names, not diffs. If the file now has more than 5 entries, move the oldest to `Docs/handoff_archive/YYYY-MM.md` (create it or append).
3. If a durable decision, ownership, pipeline state or animation state changed, update `Docs/AI_Context.md` (under about 120 lines; point to docs instead of copying them).
4. Commit with `git add -A` and the message `handoff: antigravity → claude`, plus 1-3 lines of body. Before adding, check `git status --short` for anything that should not be committed (logs, `*.blend1`, large files outside LFS, anything secret) and list those for the user instead of adding them. Do not push.
5. Answer in 6 lines at most: the entry's headline, the commit hash, what was left uncommitted and why, and the sentence to tell the next AI: "Catch up: read Docs/AI_Context.md and the newest entry in Docs/AI_Handoff.md."
