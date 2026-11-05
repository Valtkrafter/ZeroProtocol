# ZeroProtocol Unity Development Guidelines & Guardrails

> These rules apply to every AI that works in this repo (Claude Code, Antigravity).

## 0. AI handoff: read before you start, update before you stop
- **Start:** read `Docs/AI_Context.md` (project, who owns what, decisions) and the newest entry at the top of `Docs/AI_Handoff.md`. Then run `git log --oneline -10` and `git status --short`. If something changed after that entry, tell the user before you continue.
- **Stop or switch (or when the user says "handoff"):** add a new entry at the top of `Docs/AI_Handoff.md` using the template in that file, with your own plan or walkthrough summary; update `Docs/AI_Context.md` if a durable decision changed; commit everything as `handoff: <from> → <to>`; do not push.
- **One AI at a time.** Do not touch what the newest entry lists under "Don't touch".
- **Animation belongs to Claude Code and its `yoru-animator` agent.** Do not create or change Yoru's clips, Animator controllers, IK rigs or humanoid bones (see section 4).

## 1. Editor Scripting & Domain Reload Safety
- **No Heavy Operations in `[InitializeOnLoad]`**: Never execute procedural scene building (`EditorSceneManager.NewScene`, `EditorSceneManager.SaveScene`), asset re-imports, or test suites inside static constructors (`[InitializeOnLoad]`) or `[DidReloadScripts]` callbacks.
- **Menu-Driven & Batchmode Only**: All scene builders (e.g. `ArenaBuilder.Build()`) and verification suites (`CombatSystemVerifier.RunTests()`) must strictly be manual actions triggered via `[MenuItem]` or dedicated command-line batchmode arguments.
- **Scene Integrity on Play**: Verify that scenes remain loaded and intact across Play Mode transitions without triggering unexpected unload/rebuild cycles.

## 2. EditMode Physics & Unit Test Execution
- **Physics Sync Invariant**: When creating or translating `GameObject` primitives with `Collider` components during EditMode unit tests, always execute `Physics.SyncTransforms()` immediately before running `Physics.Raycast`, `Physics.RaycastNonAlloc`, or `Physics.SphereCastNonAlloc`.
- **Test Cleanup Guarantee**: All temporary game objects instantiated during verification tests must be wrapped in `try ... finally` blocks to ensure orphaned colliders are never left in the active scene.

## 3. Particle System Object Pooling
- **State Before Duration Configuration**: When creating procedural `ParticleSystem` pools via `AddComponent<ParticleSystem>()`, immediately call `ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear)` before modifying `main.duration` or emission properties to prevent engine assertions.

## 4. Character Animation & Rig Guardrail
- **Zero Character Rig Alterations**: Do NOT modify character animation clips, `Animator` controllers, IK rigs, or humanoid bones (`J_Bip_*`) on Yoru unless specifically instructed by the user. Locomotion, combat, and aiming systems must operate procedurally around the established animation baseline.
