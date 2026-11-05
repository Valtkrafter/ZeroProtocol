# Zero Protocol: Roadmap (2026-10-28)

The plan from "the walk is in the game" to a first playable slice. Written for the user first, then for every AI that works here.
Sizes: **S** = one session, **M** = 2-4 sessions (an animation is one animator job of 3-5 rounds plus the Unity bake), **L** = 5 or more.
Owner: **Claude** = main agent + `yoru-animator`; **either** = Claude or Antigravity, one at a time; **you** = your decision or play-test.

## Where we are
| Works in the game | Missing |
|---|---|
| Idle v2, Walk (polished, in since 2026-10-28), Sprint (new, weapons out, in since 2026-10-29), jump physics, dash movement (no clip of its own) | Strafe, aim, shoot, reload, dodge, slide, jump/fall/land, cover, hit and death clips |
| Dual pistols with aim, fire, bloom, aim assist, lock-on, shoulder camera, Alt free look and the rebuilt controls (she faces the crosshair, lock-on turns only her body; built, not played), a 4-lane shooting range with trolleys, paper targets and terminals | Pistol models in the hands (shots start at invisible points), slow motion, cover |
| Hair, tail, ears and bust physics, face expression, blink | Enemies, player health and damage, any audio, menus beyond the Esc panel, a toon shader (Yoru is unlit), saving |

## How every animation is made (the loop that worked for the walk)
1. References first (frames, not guesses); the animator builds 2-3 variants that differ in ONE thing. 2. You pick by looking. 3. Polish rounds, judged from the game camera (zoomed crops); tempo only with a moving character. 4. I bake it into Unity and compare it with Blender (the walk: 0.4 mm mean). 5. You look at it in the game.
The animator never touches Unity; I bake only after your OK.

## Track A: Yoru's animations (Claude)
| # | Animation | Size | Notes |
|---|---|---|---|
| A1 | **New sprint** (Shift held), built from scratch for a third-person shooter | M | The user wants a completely new one (2026-10-28): tactical sprint, pistols lowered, she faces the way she runs. The controls rebuild (C0) is built (2026-10-28): the sprint already turns her the way she runs and ends on stop, aim or fire; only the clip is missing. **Update (2026-10-28 evening):** the weapons-OUT sprint (pistols in her hands) is built first and must look like a natural run while she holds the pistols; the round-1 "carry poses" were rejected. **Done (2026-10-29):** baked into the game after five rounds (natural arms holding the pistols, trunk lean about 28°, the user: "looks good enough"); he played it and found the body leans down too far. **Lean corrected the same evening (2026-10-29):** two rounds of variants (hip→neck 20 / 23 / 26°, then 16 / 12 / 8°), he picked 12°; baked, the round-5 sprint is in `Archiv/Run_v2_r5/`, play-test pending. Her hands look empty until the pistol models exist (B4). |
| A1b | Sprint with weapons away (hands free) | M | The user wants her to put her weapons away outside a fight (2026-10-28). Matches today's walk and idle. After A1; needs decision 9. |
| A2 | Jog, about 3.4 m/s | S-M | Only if the walk-to-sprint blend still slides (measure with `LocomotionQualityTest`; the changelog lists it as a known issue). |
| A3 | **Aim pose** with two pistols | M | Three variants from 21 Oct still wait for your pick. Pistol placeholders first. |
| A4 | **Strafe in 8 directions** (aim walk) | L | The biggest block: forward, back, left, right and the diagonals, with an upper-body layer so legs and arms are separate. |
| A5 | **Fire** left and right, plus recoil | M | Additive, on the upper-body layer. |
| A6 | **Reload** (both pistols) | M | |
| A7 | **Dodge** in 4 directions, plus dash from walk and sprint | L | New design; three earlier looks were rejected (sprint push, panther, glide step). Needs references (NTE, WuWa, Genshin, Endfield dodges). |
| A8 | Slide | M | From the sprint. |
| A9 | Jump, fall, land (and the run jump) | M | The controller already feeds the parameters; only the clips are missing. |
| A10 | **Cover**: enter, idle, peek and fire, move along, exit | L | |
| A11 | Hit reactions and death (Yoru) | M | After player health exists (C5). |
| A12 | Turn in place, start and stop steps | S-M | Polish for how it feels. |
| A13 | Special idle (hands in front), small gestures | S | Already noted in the character guide. |
| A14 | Melee gun-fu combos, stealth moves | L each | After shooting works. |
| A15 | **Draw and holster** (pistols from the thigh holsters to the hands and back) | M | New wish (2026-10-28): outside a fight the weapons are away. Goes with B4 (pistol models, holster sockets) and decision 9. |

About 40 clips in total (the graphics plan's estimate). The first six give a character that moves, aims, shoots and reloads properly.

## Track B: Wiring the animations into the game (Claude, needs your OK each time)
| # | Task | Size | Notes |
|---|---|---|---|
| B1 | New Animator controller: base locomotion layer, upper-body layer (aim, fire, reload), additive recoil, face | M | Parameters such as MoveX, MoveY, Aiming, LockedOn, Fire, Reload, DodgeDirection. |
| B2 | Animation bridge component | S | Lives outside `Assets/Scripts/Combat`, because the verifier fails on any Animator reference there. It listens to the combat events and drives the Animator. |
| B3 | Controller: ~~face the aim or lock-on direction, strafe movement~~ (done in C0: `Facing`, `LocalMove`, `MoveX`, `MoveY` are ready), dodge state with invincibility frames, jump and land states, cover state | M | |
| B4 | **Pistol models in the hands**, holster sockets, muzzle sockets on the guns (replacing the fixed offsets), hands on the grips, draw and holster | M | Needs two pistol models (question 7). |
| B5 | Foot IK on slopes and stairs | S | Optional. |

## Track C: Combat and gameplay (either AI)
| # | Task | Size | Notes |
|---|---|---|---|
| C0 | ~~**Controls and camera logic, fix first**~~: she always faces the crosshair (W/A/S/D strafe), Alt free look, lock-on turns only her body (W/A/S/D relative to the target), sprint faces the way she runs | M | **Built 2026-10-28, play-test pending** (verifier 249/249 on a scratch copy). Decided in `AI_Context.md`; the built defaults waiting for your look are listed there (sprint resumes after aim or fire, dodge turn, reverse walk when backing up). |
| C1 | **Play-test and commit** the range and gun fixes and Alt free look | S | You press Play and try them; then commit in two groups. |
| C2 | ~~Crosshair or no crosshair~~ | S | Decided 2026-10-28: the crosshair stays, also while locked on. |
| C3 | **Slow-motion ability** (Dead Eye style, limited) | M | |
| C4 | **Cover system** in code: detect, snap, aim from cover | L | Pairs with A10. |
| C5 | Player health, damage, death, respawn, hit feedback (hit-stop) | M | |
| C6 | **Enemies**: first a gunman (move, take cover, shoot), then shield units, then the Hollows (fast melee), then one boss | L | Needs characters and rigs (question 6). |
| C7 | Dodge rules: invincibility, perfect dodge into slow motion, cooldown | S-M | |
| C8 | Weapon feel: recoil, spread, aim assist, reload times, ammo | S-M | Ongoing. |
| C9 | Lock-on polish (switch targets, body aiming) | S | |
| C10 | Melee gun-fu and stealth | L | Later, as planned. |

## Track D: Look, sound, interface
| # | Task | Size | Notes |
|---|---|---|---|
| D1 | **Toon shader and outline for Yoru** (lilToon or MToon) | M | The biggest visual jump; Yoru is unlit today. Best before you sign off final animations, because the look changes how they read. |
| D2 | Tonemapping, bloom, colour grading, light rig, fog | M | See `Grafik_Plan.md`. |
| D3 | VFX: sprint wind, dodge afterimage, hit sparks, dust | M | |
| D4 | **Audio**: footsteps, guns, dodge whoosh, hits, music (the Moonlight Sonata as signature), UI sounds | M-L | There is no sound in the game yet. |
| D5 | Interface: pause and settings menu, graphics levels, key rebinding, gamepad | M | |
| D6 | Level kit and the first real arena | L | Grey boxes today. |

## Track E: Story and content
| # | Task | Size | Notes |
|---|---|---|---|
| E1 | Define the **vertical slice**: one arena, 3 enemy types and a boss, dual pistols only, sprint, dodge, slide, shoulder aim, hit feedback, simple AI, toon look | S | `Grafik_Plan.md` already proposes this. |
| E2 | The **prologue** (rain, barricade, standoff, gun-fu fight, handover into play) from `Drehbuch_Prolog.md` | L | Decide: cutscene, or playable from scene 5. |
| E3 | Zones, serum and cell stability, progression | L | After the slice. |

## Track F: Technical and housekeeping
| # | Task | Size |
|---|---|---|
| F1 | Commits in clean groups; use `/handoff` for the switch commit | S |
| F2 | Emission bug: materials lose `_EMISSION` (set `globalIlluminationFlags` in `ArenaBuilder.cs` near line 759) | S |
| F3 | Repo clutter: `Assets/_Recovery`, `_Dev`, `TutorialInfo`, `SampleScene`, the template input actions, root logs and result files | S |
| F4 | Tests: ~~free-look checks in the verifier~~ (done, TEST 17); one command that compile-checks and runs the combat checks on a scratch copy (the range session built the method) | S-M |
| F5 | One command that bakes any Blender clip into Unity and checks it (export, stream, bake, parity, the Play Mode movement tests `PoseParityTest`, `WalkVerifyTest`, `LocomotionQualityTest`) | M |
| F6 | Docs: the README status is outdated, the changelog `[Unreleased]` needs the walk polish, the combat sandbox and Alt; next version 0.0.3 | S |
| F7 | Standalone build test (Arena as start scene), launcher update, GitHub release | M |
| F8 | Performance: spring-bone cost with many characters, quality levels, 60 fps on a mid-range GPU | M |

## Track G: Workflow
| # | Task |
|---|---|
| G1 | Test the Gemini handoff once ("catch up") and fix what it misses |
| G2 | Reference capture for dodge, strafe, aim and cover (many links in `Animations_Referenzen.md` are still "not seen") |
| G3 | Keep briefs lean (usage limits); one fresh animator per movement |

## Suggested order
1. **M1, feels right to move (this week):** **C0** controls rebuild (built, play-test it), play-test Alt, the range and the new walk; commit; then ~~**A1** the new sprint~~ (baked 2026-10-29, lean corrected to 12° the same evening, play-test it) (**A2** only if it slides). Next animation: **A3** the aim pose.
2. **M2, aim and shoot:** A3, B4, A4, B1-B3, A5, A6. At the end Yoru walks, aims, shoots and reloads with real animations.
3. **M3, dodge:** A7, A8, C7, D3 (afterimage).
4. **M4, a real fight:** C5, C6 (first enemy), C3 slow motion, A11, A9, D4 (basic audio).
5. **M5, cover and look:** A10 + C4, D1 + D2, D5.
6. **M6, vertical slice:** E1 and E2, three enemy types and a boss, release 0.1.0.

## Decisions I need from you
1. Tempo "B": 0.70 s (in the game now) or 0.83 s?
2. ~~Sprint: polish or new~~ Answered: a completely new sprint.
3. Aim pose: A, B or C (compact arms or more extended)? The 21 October pictures were deleted; I rebuild the three variants as a picture sheet when we reach A3.
4. ~~Crosshair: yes or no together with lock-on?~~ Answered: yes, the crosshair stays.
5. Dodge style: is there a reference you like? (Three looks were rejected before.)
6. Enemies: where do the characters come from (own models, VRoid, others), and how many types in the slice?
7. Pistol models: where do they come from?
8. Gamepad now or later?
9. When does she draw and put away the pistols: when you aim or fire and after some seconds without a fight, with a key, or something else? (Your wish of 2026-10-28: weapons away outside a fight.)

## Risks
- **Volume:** about 40 clips for one person. The polish method and additive layers keep it manageable.
- **Two AIs at once** editing the same files. Keep to the handoff rule.
- **Usage limits:** animator rounds are the expensive part.
- **Verifier guardrail** blocks Animator references in `Combat`: keep the bridge outside.
- **Spring bones** cost time per character; many enemies need a cheaper variant.
