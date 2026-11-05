---
description: Read the shared context and the newest handoff entry, and brief the user without starting any work
---

Catch up on the project after another AI (or an earlier session) worked on it. Read only; start no work.

1. Read `Docs/AI_Context.md` (skip it if it is already in context) and the newest entry at the top of `Docs/AI_Handoff.md` in full, plus the headline of the one below it.
2. Run `git log --oneline` back to the last `handoff:` commit, and `git status --short`. Anything newer than the newest entry (commits or uncommitted files) was done by someone who did not write an entry: look at `git diff --stat` for it and report it separately.
3. Brief the user in 10 lines at most: where the project stands, what changed since the last entry, what is open or waiting for the user, and anything risky or contradictory (for example files the entry says not to touch that have changed). If the entry names a background job, check whether its output files exist.
4. Ask nothing unless something blocks the next step. Do not edit files and do not commit.
