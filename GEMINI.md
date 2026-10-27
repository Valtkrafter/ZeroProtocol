# ZeroProtocol Unity Development Guidelines & Guardrails

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
