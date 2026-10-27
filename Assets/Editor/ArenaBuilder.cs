using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using ZeroProtocol.CameraSystem;
using ZeroProtocol.Combat;
using ZeroProtocol.Player;

namespace ZeroProtocol.EditorTools
{
    /// <summary>
    /// Builds the high-end cyberpunk shooting range arena scene:
    /// Enclosed Cyberpunk Firing Bay (32m x 70m x 6.5m) with acoustic ceiling baffles,
    /// bullet trap backstop at Z = 60m, 4 operational firing stalls with glass dividers,
    /// counters, brass catch trays, overhead neon lane signs, motorized target trolley
    /// carriers (0.8m to 25m), dynamic paper bullseye targets with hole decals,
    /// deep reactive steel poppers, moving rail target, proximity cyber-terminals,
    /// brass shell casing pooling, Yoru controller, and decoupled Gun-Fu combat.
    /// </summary>
    public static class ArenaBuilder
    {
        const string ScenePath = "Assets/Scenes/Arena.unity";
        const string YoruPrefabPath = "Assets/Characters/Yoru/ShiroganeYoru.prefab";
        static readonly bool UseScalpShell = false;
        const string MatDir = "Assets/Materials/Arena";

        [MenuItem("Zero Protocol/Build Test Arena")]
        public static void Build()
        {
            PlayerSettings.runInBackground = true;
            EditorSceneManager.SaveOpenScenes();

            Directory.CreateDirectory(MatDir);
            var floorMat = MakeMat("ArenaGrid", new Color(1f, 1f, 1f), GridTexture(), 48f);
            var ceilingMat = MakeMat("ArenaCeiling", new Color(0.12f, 0.13f, 0.16f), null, 1f);
            var baffleMat = MakeMat("ArenaBaffle", new Color(0.18f, 0.20f, 0.25f), null, 1f);
            var crateMat = MakeMat("ArenaCrate", new Color(0.86f, 0.52f, 0.20f), null, 1f);
            var blockMat = MakeMat("ArenaBlock", new Color(0.22f, 0.24f, 0.28f), null, 1f);
            var steelMat = MakeMat("ArenaSteel", new Color(0.38f, 0.42f, 0.48f), null, 1f, metallic: 0.85f, smoothness: 0.65f);
            var brassMat = MakeMat("ArenaBrass", new Color(0.88f, 0.68f, 0.24f), null, 1f, metallic: 0.92f, smoothness: 0.75f);
            var dummyMat = MakeMat("ArenaDummy", new Color(0.169f, 0.176f, 0.259f), null, 1f);
            var headMat = MakeMat("ArenaDummyHead", new Color(0.24f, 0.26f, 0.35f), null, 1f);
            var neonCyanMat = MakeMat("ArenaNeonCyan", new Color(0.0f, 0.941f, 1.0f), null, 1f, emissive: true);
            var neonYellowMat = MakeMat("ArenaNeonYellow", new Color(1.0f, 0.745f, 0.043f), null, 1f, emissive: true);
            var stripeMat = MakeMat("ArenaStripe", new Color(1.0f, 0.85f, 0.1f), null, 1f, emissive: true);
            var hazardMat = MakeMat("ArenaHazard", new Color(1f, 1f, 1f), HazardTexture(), 4f, emissive: true);
            var glassMat = MakeGlassMat("ArenaGlass", new Color(0.25f, 0.75f, 0.85f, 0.35f));
            var paperMat = MakeMat("ArenaPaperTarget", Color.white, PaperBullseyeTexture(), 1f);

            Scene scene = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);
            Directory.CreateDirectory("Assets/Scenes");

            var root = new GameObject("Arena").transform;

            // -----------------------------------------------------------
            // 1. ENCLOSED CYBERPUNK FIRING BAY FACILITY
            // Dimensions: 32m wide (X: -16m to +16m) x 70m long (Z: -10m to +60m) x 6.5m high (Y: 0m to 6.5m)
            // -----------------------------------------------------------
            var facility = new GameObject("FacilityEnclosure").transform;
            facility.SetParent(root);

            // Floor: 32m x 70m centered at Z = 25m, top surface sits at y = 0
            var floor = GameObject.CreatePrimitive(PrimitiveType.Cube);
            floor.name = "Floor";
            floor.transform.SetParent(facility);
            floor.transform.position = new Vector3(0f, -0.5f, 25f);
            floor.transform.localScale = new Vector3(32f, 1f, 70f);
            floor.GetComponent<Renderer>().sharedMaterial = floorMat;

            // Ceiling: 32m x 70m at Y = 6.5m
            var ceiling = GameObject.CreatePrimitive(PrimitiveType.Cube);
            ceiling.name = "Ceiling";
            ceiling.transform.SetParent(facility);
            ceiling.transform.position = new Vector3(0f, 6.75f, 25f);
            ceiling.transform.localScale = new Vector3(32f, 0.5f, 70f);
            ceiling.GetComponent<Renderer>().sharedMaterial = ceilingMat;

            // Acoustic Ceiling Baffles (spaced every 5m from Z = -8m to +56m)
            var bafflesRoot = new GameObject("CeilingBaffles").transform;
            bafflesRoot.SetParent(facility);
            for (float bz = -8f; bz <= 56f; bz += 5.0f)
            {
                var baffle = Box(bafflesRoot, $"Baffle_Z{bz:F0}", new Vector3(31.5f, 0.6f, 0.18f), new Vector3(0f, 6.1f, bz), baffleMat);
                var bc = baffle.GetComponent<Collider>();
                if (bc != null) Object.DestroyImmediate(bc);
            }

            // Facility Perimeter Walls
            Box(facility, "Wall_West", new Vector3(1f, 6.5f, 70f), new Vector3(-16.5f, 3.25f, 25f), blockMat);
            Box(facility, "Wall_East", new Vector3(1f, 6.5f, 70f), new Vector3(16.5f, 3.25f, 25f), blockMat);
            Box(facility, "Wall_South_Rear", new Vector3(32f, 6.5f, 1f), new Vector3(0f, 3.25f, -10.5f), blockMat);
            Box(facility, "Wall_North_Front", new Vector3(32f, 6.5f, 1f), new Vector3(0f, 3.25f, 60.5f), blockMat);

            // -----------------------------------------------------------
            // 2. BULLET TRAP BACKSTOP AT Z = 60m
            // Angled heavy steel deflector trap with hazard stripes and warning stencils
            // -----------------------------------------------------------
            var backstopRoot = new GameObject("BulletTrapBackstop_60M").transform;
            backstopRoot.SetParent(facility);

            // Lower angled steel ramp (deflects bullets into trap)
            var rampLower = GameObject.CreatePrimitive(PrimitiveType.Cube);
            rampLower.name = "SteelDeflector_Lower";
            rampLower.transform.SetParent(backstopRoot);
            rampLower.transform.position = new Vector3(0f, 1.8f, 58.2f);
            rampLower.transform.rotation = Quaternion.Euler(-32f, 0f, 0f);
            rampLower.transform.localScale = new Vector3(31.8f, 0.45f, 4.5f);
            rampLower.GetComponent<Renderer>().sharedMaterial = steelMat;

            // Upper angled steel deflector
            var rampUpper = GameObject.CreatePrimitive(PrimitiveType.Cube);
            rampUpper.name = "SteelDeflector_Upper";
            rampUpper.transform.SetParent(backstopRoot);
            rampUpper.transform.position = new Vector3(0f, 4.8f, 58.2f);
            rampUpper.transform.rotation = Quaternion.Euler(32f, 0f, 0f);
            rampUpper.transform.localScale = new Vector3(31.8f, 0.45f, 4.5f);
            rampUpper.GetComponent<Renderer>().sharedMaterial = steelMat;

            // Hazard stripe fascia beam
            var hazardFascia = Box(backstopRoot, "HazardFascia", new Vector3(32f, 0.75f, 0.2f), new Vector3(0f, 3.3f, 56.5f), hazardMat);
            var hfc = hazardFascia.GetComponent<Collider>();
            if (hfc != null) Object.DestroyImmediate(hfc);

            // Warning Stencil
            CreateWarningSign(backstopRoot, "DANGER // BULLET TRAP // 60M BACKSTOP", new Vector3(0f, 3.3f, 56.35f), new Color(1.0f, 0.85f, 0.05f));

            // -----------------------------------------------------------
            // 3. FIRING STALLS & SHOOTING LANES (Lanes 1 to 4 at X = -9m, -3m, +3m, +9m)
            // Stalls: Solid acoustic partitions (1.4m), tempered glass (0.8m), heavy counters,
            // brass catch trays, overhead neon signs, downlights, and proximity cyber-terminals.
            // -----------------------------------------------------------
            var rangeRoot = new GameObject("FiringRange").transform;
            rangeRoot.SetParent(root);

            float[] laneX = { -9f, -3f, 3f, 9f };
            string[] laneNames = { "LANE 01", "LANE 02", "LANE 03", "LANE 04" };
            float[] dividerX = { -12f, -6f, 0f, 6f, 12f };

            // Stall Dividers (Z from -4.5m to -1.0m, length 3.5m)
            for (int i = 0; i < dividerX.Length; i++)
            {
                // Solid acoustic partition wall (height 1.4m)
                Box(rangeRoot, $"StallDivider_{i}_Lower", new Vector3(0.2f, 1.4f, 3.5f), new Vector3(dividerX[i], 0.7f, -2.75f), blockMat);

                // Safety tempered glass upper panel (height 0.8m, Y: 1.4m to 2.2m)
                var glass = Box(rangeRoot, $"StallDivider_{i}_Glass", new Vector3(0.06f, 0.8f, 3.5f), new Vector3(dividerX[i], 1.8f, -2.75f), glassMat);
                var gc = glass.GetComponent<Collider>();
                if (gc != null) Object.DestroyImmediate(gc);

                // Top neon accent runner
                var rail = Box(rangeRoot, $"StallDivider_{i}_TopRail", new Vector3(0.22f, 0.06f, 3.5f), new Vector3(dividerX[i], 2.23f, -2.75f), neonCyanMat);
                var rc = rail.GetComponent<Collider>();
                if (rc != null) Object.DestroyImmediate(rc);
            }

            // Overhead Gantry Frame & Neon Lane Signs at Z = -1.0m, Y = 3.6m
            var gantryBeam = Box(rangeRoot, "OverheadGantry", new Vector3(25f, 0.25f, 0.35f), new Vector3(0f, 3.6f, -1.0f), blockMat);
            var gbc = gantryBeam.GetComponent<Collider>();
            if (gbc != null) Object.DestroyImmediate(gbc);

            // Floor Lane Dividers along Z (from Z = -1m to Z = 56m)
            for (int i = 0; i < dividerX.Length; i++)
            {
                float runnerLen = 57f;
                var runner = Box(rangeRoot, $"FloorRunner_{i}", new Vector3(0.08f, 0.015f, runnerLen),
                    new Vector3(dividerX[i], 0.008f, -1f + runnerLen * 0.5f), neonCyanMat);
                var col = runner.GetComponent<Collider>();
                if (col != null) Object.DestroyImmediate(col);
            }

            // Distance Threshold Floor Stripes
            CreateFloorThresholdStripe(rangeRoot, "Threshold_5M", new Vector3(0f, 0.008f, 4f), 24f, stripeMat);
            CreateFloorThresholdStripe(rangeRoot, "Threshold_10M", new Vector3(0f, 0.008f, 9f), 24f, stripeMat);
            CreateFloorThresholdStripe(rangeRoot, "Threshold_15M", new Vector3(0f, 0.008f, 14f), 24f, stripeMat);
            CreateFloorThresholdStripe(rangeRoot, "Threshold_25M", new Vector3(0f, 0.008f, 24f), 24f, stripeMat);

            // Rear Ammo Resupply Counter at Z = -7.5m
            CreateAmmoCrate(rangeRoot, "AmmoResupplyStation", new Vector3(-6f, 0f, -7.5f), crateMat, neonCyanMat);
            CreateAmmoCrate(rangeRoot, "AmmoResupplyStation_R", new Vector3(6f, 0f, -7.5f), crateMat, neonCyanMat);

            // Construct each of the 4 Firing Lanes with full systems
            for (int laneIdx = 0; laneIdx < laneX.Length; laneIdx++)
            {
                float lx = laneX[laneIdx];
                string laneId = laneNames[laneIdx];

                var laneRoot = new GameObject(laneId).transform;
                laneRoot.SetParent(rangeRoot);

                // Overhead Neon Lane Sign
                CreateNeonSign(laneRoot, laneId, new Vector3(lx, 3.6f, -1.0f), blockMat, new Color(0.0f, 0.941f, 1.0f));

                // Recessed Overhead Downlight in Booth
                var downlightGo = new GameObject("Downlight");
                downlightGo.transform.SetParent(laneRoot, false);
                downlightGo.transform.position = new Vector3(lx, 4.2f, -2.75f);
                var spot = downlightGo.AddComponent<Light>();
                spot.type = LightType.Spot;
                spot.spotAngle = 75f;
                spot.range = 6.5f;
                spot.intensity = 1.6f;
                spot.color = new Color(0.9f, 0.95f, 1.0f);
                spot.shadows = LightShadows.Soft;

                // Heavy Shooting Counter (top at Y = 1.0m, Z = -1.0m)
                var counter = Box(laneRoot, "ShootingCounter", new Vector3(2.4f, 1.0f, 0.6f), new Vector3(lx, 0.5f, -1.0f), blockMat);

                // Brass Catch Tray on Counter Top
                var tray = Box(laneRoot, "BrassCatchTray", new Vector3(0.9f, 0.04f, 0.45f), new Vector3(lx + 0.55f, 1.02f, -1.0f), brassMat);

                // Stall Trigger Volume (detects Yoru entering/exiting stall)
                // Kinematic Rigidbody guarantees PhysX dispatches trigger events to CharacterController
                var triggerGo = new GameObject("StallProximityTrigger");
                triggerGo.transform.SetParent(laneRoot, false);
                triggerGo.transform.position = new Vector3(lx, 1.25f, -2.75f);
                var trigCol = triggerGo.AddComponent<BoxCollider>();
                trigCol.isTrigger = true;
                trigCol.size = new Vector3(2.6f, 2.4f, 3.5f);
                var trigRb = triggerGo.AddComponent<Rigidbody>();
                trigRb.isKinematic = true;

                // Overhead Dual Steel Guide Rails (spanning Z = -0.5m to Z = 25.5m at Y = 3.4m)
                var trackRoot = new GameObject("OverheadTrackBeam").transform;
                trackRoot.SetParent(laneRoot, false);
                float trackLen = 26f;
                var railL = Box(trackRoot, "Rail_L", new Vector3(0.06f, 0.12f, trackLen), new Vector3(lx - 0.25f, 3.4f, 12.5f), steelMat);
                var railR = Box(trackRoot, "Rail_R", new Vector3(0.06f, 0.12f, trackLen), new Vector3(lx + 0.25f, 3.4f, 12.5f), steelMat);
                var colL = railL.GetComponent<Collider>(); if (colL != null) Object.DestroyImmediate(colL);
                var colR = railR.GetComponent<Collider>(); if (colR != null) Object.DestroyImmediate(colR);

                // Motorized Target Trolley Carrier
                var trolleyGo = new GameObject("TargetTrolley");
                trolleyGo.transform.SetParent(laneRoot, false);
                trolleyGo.transform.position = new Vector3(lx, 3.4f, 9.0f); // Initially at 10m stop (Z = 9.0m)

                var trolley = trolleyGo.AddComponent<TargetTrolley>();
                trolley.boothOriginZ = -1.0f;
                trolley.smoothTime = 0.60f;
                trolley.maxSpeed = 8.5f;

                // Carriage Body
                var carriage = Box(trolleyGo.transform, "CarriageBody", new Vector3(0.7f, 0.18f, 0.45f), new Vector3(lx, 3.32f, 9.0f), blockMat);
                trolley.carriageTransform = carriage.transform;

                // Suspension Cables hanging down to paper target
                var suspRoot = new GameObject("SuspensionCables").transform;
                suspRoot.SetParent(trolleyGo.transform, false);
                var cableL = Box(suspRoot, "Cable_L", new Vector3(0.015f, 1.4f, 0.015f), new Vector3(lx - 0.24f, 2.5f, 9.0f), steelMat);
                var cableR = Box(suspRoot, "Cable_R", new Vector3(0.015f, 1.4f, 0.015f), new Vector3(lx + 0.24f, 2.5f, 9.0f), steelMat);
                var cl = cableL.GetComponent<Collider>(); if (cl != null) Object.DestroyImmediate(cl);
                var cr = cableR.GetComponent<Collider>(); if (cr != null) Object.DestroyImmediate(cr);

                // Paper Bullseye Target Sheet: Unscaled carrier root ensures isotropic coordinate metrics
                // and prevents non-uniform shearing on dynamic bullet hole decals
                var paperTargetGo = new GameObject("PaperTargetSheet");
                paperTargetGo.transform.SetParent(trolleyGo.transform, false);
                paperTargetGo.transform.position = new Vector3(lx, 1.4f, 9.0f);
                paperTargetGo.transform.localScale = Vector3.one;

                var paperCol = paperTargetGo.AddComponent<BoxCollider>();
                paperCol.size = new Vector3(0.55f, 0.85f, 0.02f);

                var visualGo = GameObject.CreatePrimitive(PrimitiveType.Cube);
                visualGo.name = "SheetVisual";
                visualGo.transform.SetParent(paperTargetGo.transform, false);
                visualGo.transform.localPosition = Vector3.zero;
                visualGo.transform.localScale = new Vector3(0.55f, 0.85f, 0.02f);
                visualGo.GetComponent<Renderer>().sharedMaterial = paperMat;
                var visCol = visualGo.GetComponent<Collider>();
                if (visCol != null) Object.DestroyImmediate(visCol);

                var paperTarget = paperTargetGo.AddComponent<PaperTarget>();
                paperTarget.paperRenderer = visualGo.GetComponent<Renderer>();
                paperTarget.sheetWidth = 0.55f;
                paperTarget.sheetHeight = 0.85f;
                trolley.paperTarget = paperTarget;

                // Lock-On target support for paper target
                var lockPaper = paperTargetGo.AddComponent<LockOnTarget>();
                lockPaper.aimHeight = 0f;

                // Deep Reactive Steel Targets in Lane
                // 30m Steel Popper (drops flat 90 degrees, auto resets)
                var popperGo = CreatePopperTarget(laneRoot, $"Popper_30M_{laneId}", new Vector3(lx, 0f, 29.0f), steelMat, blockMat);
                var popper = popperGo.GetComponentInChildren<PopperTarget>();

                // 40m Reactive Targets
                GameObject silTargetGo = null;
                if (laneIdx == 1 || laneIdx == 2)
                {
                    silTargetGo = CreateShootingTarget(laneRoot, $"Silhouette_40M_{laneId}", new Vector3(lx, 0f, 39.0f), dummyMat, headMat);
                }

                // 50m Elevated Moving Rail Target in Lane 4
                if (laneIdx == 3)
                {
                    CreateElevatedRailTarget(laneRoot, "MovingRailTarget_50M", new Vector3(lx - 2.5f, 1.6f, 49.0f), new Vector3(5f, 0f, 0f), blockMat, dummyMat, headMat);
                }

                // Proximity Floating Holographic Cyber-Terminal
                var terminalGo = CreateCyberTerminal(laneRoot, laneId, new Vector3(lx - 0.65f, 1.0f, -0.95f), blockMat, neonCyanMat);
                var terminal = terminalGo.GetComponent<RangeTerminal>();
                terminal.laneName = laneId;
                terminal.trolley = trolley;
                terminal.paperTarget = paperTarget;
                terminal.steelPoppers = (popper != null) ? new PopperTarget[] { popper } : new PopperTarget[0];

                var laneTargetsList = new System.Collections.Generic.List<ShootingTarget>();
                if (popper != null) laneTargetsList.Add(popper);
                if (silTargetGo != null)
                {
                    var st = silTargetGo.GetComponentInChildren<ShootingTarget>();
                    if (st != null) laneTargetsList.Add(st);
                }
                terminal.laneTargets = laneTargetsList.ToArray();

                // Wire proximity trigger to terminal
                var trigProxy = triggerGo.AddComponent<RangeTerminalTriggerProxy>();
                trigProxy.terminal = terminal;
            }

            // -----------------------------------------------------------
            // 4. PLAYER CHARACTER RIG & COMBAT PIPELINE
            // Spawn inside Lane 2 booth at X = -3m, Z = -2.5m facing +Z
            // -----------------------------------------------------------
            var yoruPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(YoruPrefabPath);
            var player = new GameObject("Player");
            player.tag = "Player";
            player.transform.position = new Vector3(-3f, 0.05f, -2.5f);
            var cc = player.AddComponent<CharacterController>();
            cc.height = 1.5f; cc.radius = 0.28f; cc.center = new Vector3(0f, 0.78f, 0f);
            cc.stepOffset = 0.35f; cc.slopeLimit = 50f; cc.skinWidth = 0.03f;

            if (yoruPrefab != null)
            {
                var model = (GameObject)PrefabUtility.InstantiatePrefab(yoruPrefab);
                model.name = "Yoru";
                model.transform.SetParent(player.transform, false);
                var ctrl = AssetDatabase.LoadAssetAtPath<RuntimeAnimatorController>(YoruAnimatorBuilder.ControllerPath);
                var modelAnimator = model.GetComponent<Animator>();
                if (ctrl != null && modelAnimator != null) modelAnimator.runtimeAnimatorController = ctrl;
                model.AddComponent<YoruSecondaryMotion>();
                model.AddComponent<YoruBlink>();
                model.AddComponent<YoruFaceExpression>();
                if (UseScalpShell)
                {
                    var scalp = model.AddComponent<YoruScalpShell>();
                    scalp.strandTexture = YoruHairFix.PrepareStrandTile();
                    scalp.baseMaterial = AssetDatabase.LoadAssetAtPath<Material>(YoruHairFix.MaterialPath);
                }
            }

            player.AddComponent<GameInput>();
            var controller = player.AddComponent<YoruController>();
            controller.animator = player.GetComponentInChildren<Animator>();
            var lockOnSystem = player.AddComponent<LockOnSystem>();
            controller.lockOn = lockOnSystem;

            // Auto-wire DualPistolCombat & Muzzle Sockets
            var combat = player.AddComponent<DualPistolCombat>();
            combat.input = player.GetComponent<GameInput>();

            var sockets = new GameObject("Sockets");
            sockets.transform.SetParent(player.transform, false);

            var muzzleL = new GameObject("Muzzle_L");
            muzzleL.transform.SetParent(sockets.transform, false);
            muzzleL.transform.localPosition = new Vector3(-0.25f, 1.15f, 0.45f);
            combat.muzzleLeft = muzzleL.transform;

            var muzzleR = new GameObject("Muzzle_R");
            muzzleR.transform.SetParent(sockets.transform, false);
            muzzleR.transform.localPosition = new Vector3(0.25f, 1.15f, 0.45f);
            combat.muzzleRight = muzzleR.transform;

            // Auto-wire GunVFX
            var vfx = player.AddComponent<GunVFX>();
            vfx.combat = combat;

            // Auto-wire Brass Shell Casing Pool
            var shellPool = player.AddComponent<ShellCasingPool>();
            shellPool.combat = combat;

            // Main Camera & Camera Rig
            var cam = Camera.main;
            cam.tag = "MainCamera";
            cam.nearClipPlane = 0.1f;
            cam.farClipPlane = 400f;
            var rig = cam.gameObject.AddComponent<ThirdPersonCamera>();
            rig.target = player.transform;
            rig.input = player.GetComponent<GameInput>();
            combat.mainCamera = cam;

            cam.gameObject.AddComponent<ControlsHint>();
            var combatUI = cam.gameObject.AddComponent<CombatUI>();
            combatUI.combat = combat;
            combatUI.lockOn = lockOnSystem;

            controller.cameraTransform = cam.transform;
            lockOnSystem.cameraRig = rig;
            cam.transform.position = new Vector3(-3f, 2.2f, -7.5f);

            PostFxBuilder.Add(cam);

            var dirLight = Object.FindFirstObjectByType<Light>();
            if (dirLight != null) { dirLight.shadows = LightShadows.Soft; dirLight.intensity = 0.95f; }

            EditorSceneManager.SaveScene(scene, ScenePath);
            AssetDatabase.SaveAssets();
            Debug.Log("[ZeroProtocol] Enclosed Cyberpunk Firing Bay Arena built: " + ScenePath);
        }

        static GameObject Box(Transform parent, string name, Vector3 size, Vector3 pos, Material mat)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = name;
            go.transform.SetParent(parent, false);
            go.transform.position = pos;
            go.transform.localScale = size;
            go.GetComponent<Renderer>().sharedMaterial = mat;
            return go;
        }

        static GameObject CreateFloorThresholdStripe(Transform parent, string name, Vector3 centerPos, float width, Material mat)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = name;
            go.transform.SetParent(parent, false);
            go.transform.position = centerPos;
            go.transform.localScale = new Vector3(width, 0.015f, 0.45f);
            go.GetComponent<Renderer>().sharedMaterial = mat;
            var col = go.GetComponent<Collider>();
            if (col != null) Object.DestroyImmediate(col);
            return go;
        }

        static GameObject CreateNeonSign(Transform parent, string text, Vector3 pos, Material bgMat, Color textColor)
        {
            var signRoot = new GameObject("Sign_" + text);
            signRoot.transform.SetParent(parent, false);
            signRoot.transform.position = pos;

            var backplate = GameObject.CreatePrimitive(PrimitiveType.Cube);
            backplate.name = "Backplate";
            backplate.transform.SetParent(signRoot.transform, false);
            backplate.transform.localScale = new Vector3(2.2f, 0.70f, 0.12f);
            backplate.GetComponent<Renderer>().sharedMaterial = bgMat;
            var col = backplate.GetComponent<Collider>();
            if (col != null) Object.DestroyImmediate(col);

            var textGo = new GameObject("Text");
            textGo.transform.SetParent(signRoot.transform, false);
            textGo.transform.localPosition = new Vector3(0f, 0f, -0.07f);
            var tm = textGo.AddComponent<TextMesh>();
            tm.text = text;
            tm.fontSize = 54;
            tm.characterSize = 0.08f;
            tm.alignment = TextAlignment.Center;
            tm.anchor = TextAnchor.MiddleCenter;
            tm.color = textColor;
            tm.fontStyle = FontStyle.Bold;

            return signRoot;
        }

        static GameObject CreateWarningSign(Transform parent, string text, Vector3 pos, Color textColor)
        {
            var textGo = new GameObject("WarningText");
            textGo.transform.SetParent(parent, false);
            textGo.transform.position = pos;
            var tm = textGo.AddComponent<TextMesh>();
            tm.text = text;
            tm.fontSize = 58;
            tm.characterSize = 0.11f;
            tm.alignment = TextAlignment.Center;
            tm.anchor = TextAnchor.MiddleCenter;
            tm.color = textColor;
            tm.fontStyle = FontStyle.Bold;
            return textGo;
        }

        static GameObject CreateCyberTerminal(Transform parent, string laneName, Vector3 counterBasePos, Material baseMat, Material neonMat)
        {
            var termRoot = new GameObject($"CyberTerminal_{laneName}");
            termRoot.transform.SetParent(parent, false);
            termRoot.transform.position = counterBasePos;

            // Terminal pedestal mount
            var pedestal = Box(termRoot.transform, "Pedestal", new Vector3(0.12f, 0.28f, 0.12f), counterBasePos + new Vector3(0f, 0.14f, 0f), baseMat);
            var pc = pedestal.GetComponent<Collider>(); if (pc != null) Object.DestroyImmediate(pc);

            // Angled Holographic Screen Frame
            var screenFrame = GameObject.CreatePrimitive(PrimitiveType.Cube);
            screenFrame.name = "ScreenFrame";
            screenFrame.transform.SetParent(termRoot.transform, false);
            screenFrame.transform.position = counterBasePos + new Vector3(0f, 0.40f, 0f);
            screenFrame.transform.rotation = Quaternion.Euler(22f, 0f, 0f);
            screenFrame.transform.localScale = new Vector3(0.75f, 0.45f, 0.03f);
            screenFrame.GetComponent<Renderer>().sharedMaterial = baseMat;
            var sfc = screenFrame.GetComponent<Collider>(); if (sfc != null) Object.DestroyImmediate(sfc);

            // Screen Display Surface
            var screenFace = GameObject.CreatePrimitive(PrimitiveType.Quad);
            screenFace.name = "ScreenFace";
            screenFace.transform.SetParent(screenFrame.transform, false);
            screenFace.transform.localPosition = new Vector3(0f, 0f, -0.55f);
            screenFace.transform.localRotation = Quaternion.Euler(0f, 180f, 0f);
            screenFace.transform.localScale = new Vector3(0.92f, 0.88f, 1f);
            screenFace.GetComponent<Renderer>().sharedMaterial = baseMat;
            var sdc = screenFace.GetComponent<Collider>(); if (sdc != null) Object.DestroyImmediate(sdc);

            // Holographic 3D Text Mesh
            var textGo = new GameObject("TerminalText");
            textGo.transform.SetParent(screenFrame.transform, false);
            textGo.transform.localPosition = new Vector3(-0.45f, 0.40f, -0.60f);
            textGo.transform.localRotation = Quaternion.Euler(0f, 180f, 0f);
            var tm = textGo.AddComponent<TextMesh>();
            tm.fontSize = 28;
            tm.characterSize = 0.024f;
            tm.lineSpacing = 1.15f;
            tm.alignment = TextAlignment.Left;
            tm.anchor = TextAnchor.UpperLeft;
            tm.color = new Color(0.0f, 0.941f, 1.0f);
            tm.fontStyle = FontStyle.Bold;

            // Terminal Holographic Accent Light
            var lightGo = new GameObject("TerminalLight");
            lightGo.transform.SetParent(screenFrame.transform, false);
            lightGo.transform.localPosition = new Vector3(0f, 0f, -0.6f);
            var lt = lightGo.AddComponent<Light>();
            lt.type = LightType.Point;
            lt.range = 1.6f;
            lt.intensity = 0.8f;
            lt.color = new Color(0.0f, 0.941f, 1.0f);
            lt.shadows = LightShadows.None;

            var termComp = termRoot.AddComponent<RangeTerminal>();
            termComp.laneName = laneName;
            termComp.terminalTextMesh = tm;
            termComp.screenRenderer = screenFace.GetComponent<Renderer>();
            termComp.terminalLight = lt;

            return termRoot;
        }

        static GameObject CreateShootingTarget(Transform parent, string name, Vector3 pos, Material bodyMat, Material headMat)
        {
            var targetRoot = new GameObject(name);
            targetRoot.transform.SetParent(parent, false);
            targetRoot.transform.position = pos;

            var basePlate = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            basePlate.name = "StandBase";
            basePlate.transform.SetParent(targetRoot.transform, false);
            basePlate.transform.localPosition = new Vector3(0f, 0.05f, 0f);
            basePlate.transform.localScale = new Vector3(0.9f, 0.05f, 0.9f);
            basePlate.GetComponent<Renderer>().sharedMaterial = bodyMat;

            var dummyTilt = new GameObject("DummyTilt");
            dummyTilt.transform.SetParent(targetRoot.transform, false);
            dummyTilt.transform.localPosition = Vector3.zero;

            var body = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            body.name = "Body";
            body.transform.SetParent(dummyTilt.transform, false);
            body.transform.localPosition = new Vector3(0f, 0.85f, 0f);
            body.transform.localScale = new Vector3(0.65f, 0.65f, 0.45f);
            var bodyRend = body.GetComponent<Renderer>();
            bodyRend.sharedMaterial = bodyMat;
            var bodyHitbox = body.AddComponent<TargetHitbox>();
            bodyHitbox.hitboxType = HitType.Body;

            var head = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            head.name = "Head";
            head.transform.SetParent(dummyTilt.transform, false);
            head.transform.localPosition = new Vector3(0f, 1.6f, 0f);
            head.transform.localScale = new Vector3(0.42f, 0.45f, 0.42f);
            var headRend = head.GetComponent<Renderer>();
            headRend.sharedMaterial = headMat;
            var headHitbox = head.AddComponent<TargetHitbox>();
            headHitbox.hitboxType = HitType.Headshot;

            var st = dummyTilt.AddComponent<ShootingTarget>();
            st.targetRenderer = bodyRend;
            st.headRenderer = headRend;
            st.headTransform = head.transform;
            st.bodyTransform = body.transform;
            st.omega = 25f;
            st.zeta = 0.35f;

            bodyHitbox.parentTarget = st;
            headHitbox.parentTarget = st;

            var lockTarget = dummyTilt.AddComponent<LockOnTarget>();
            lockTarget.aimHeight = 0.6f;

            return targetRoot;
        }

        static GameObject CreatePopperTarget(Transform parent, string name, Vector3 pos, Material steelMat, Material baseMat)
        {
            var targetRoot = new GameObject(name);
            targetRoot.transform.SetParent(parent, false);
            targetRoot.transform.position = pos;

            // Hinge base frame
            var basePlate = GameObject.CreatePrimitive(PrimitiveType.Cube);
            basePlate.name = "HingeBase";
            basePlate.transform.SetParent(targetRoot.transform, false);
            basePlate.transform.localPosition = new Vector3(0f, 0.1f, 0f);
            basePlate.transform.localScale = new Vector3(0.9f, 0.2f, 0.5f);
            basePlate.GetComponent<Renderer>().sharedMaterial = baseMat;

            // Motorized hinge post
            var post = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            post.name = "HingePost";
            post.transform.SetParent(targetRoot.transform, false);
            post.transform.localPosition = new Vector3(0f, 0.25f, 0f);
            post.transform.localScale = new Vector3(0.35f, 0.15f, 0.35f);
            post.GetComponent<Renderer>().sharedMaterial = baseMat;

            // Hinging plate root (drops flat 90 degrees around X axis)
            var platePivot = new GameObject("PlatePivot");
            platePivot.transform.SetParent(targetRoot.transform, false);
            platePivot.transform.localPosition = new Vector3(0f, 0.3f, 0f);

            // Circular steel target plate (body)
            var disc = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            disc.name = "SteelPlate";
            disc.transform.SetParent(platePivot.transform, false);
            disc.transform.localPosition = new Vector3(0f, 0.75f, 0f);
            disc.transform.localRotation = Quaternion.Euler(90f, 0f, 0f);
            disc.transform.localScale = new Vector3(0.85f, 0.06f, 0.85f);
            var discRend = disc.GetComponent<Renderer>();
            discRend.sharedMaterial = steelMat;

            // Target bullseye (head hitbox)
            var bullseye = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            bullseye.name = "Bullseye";
            bullseye.transform.SetParent(platePivot.transform, false);
            bullseye.transform.localPosition = new Vector3(0f, 1.25f, 0f);
            bullseye.transform.localScale = new Vector3(0.35f, 0.35f, 0.25f);
            var bullseyeRend = bullseye.GetComponent<Renderer>();
            bullseyeRend.sharedMaterial = steelMat;

            var popper = platePivot.AddComponent<PopperTarget>();
            popper.targetRenderer = discRend;
            popper.headRenderer = bullseyeRend;
            popper.bodyTransform = disc.transform;
            popper.headTransform = bullseye.transform;
            popper.dropAngle = 90f;
            popper.respawnDelay = 2.5f;

            var bodyHitbox = disc.AddComponent<TargetHitbox>();
            bodyHitbox.hitboxType = HitType.Body;
            bodyHitbox.parentTarget = popper;

            var headHitbox = bullseye.AddComponent<TargetHitbox>();
            headHitbox.hitboxType = HitType.Headshot;
            headHitbox.parentTarget = popper;

            var lockTarget = platePivot.AddComponent<LockOnTarget>();
            lockTarget.aimHeight = 0.85f;

            return targetRoot;
        }

        static GameObject CreateElevatedRailTarget(Transform parent, string name, Vector3 startPos, Vector3 offset, Material trackMat, Material dummyMat, Material headMat)
        {
            var railRoot = new GameObject(name);
            railRoot.transform.SetParent(parent, false);
            railRoot.transform.position = startPos;

            // Elevation Support Pillars
            Box(railRoot.transform, "Pillar_Left", new Vector3(0.45f, startPos.y + 0.1f, 0.45f), new Vector3(0f, -(startPos.y * 0.5f), 0f), trackMat);
            Box(railRoot.transform, "Pillar_Right", new Vector3(0.45f, startPos.y + 0.1f, 0.45f), offset + new Vector3(0f, -(startPos.y * 0.5f), 0f), trackMat);

            // Elevated Track Beam
            var track = GameObject.CreatePrimitive(PrimitiveType.Cube);
            track.name = "ElevatedTrackBeam";
            track.transform.SetParent(railRoot.transform, false);
            track.transform.localPosition = offset * 0.5f + new Vector3(0f, 0.05f, 0f);
            track.transform.localScale = new Vector3(offset.magnitude + 1.2f, 0.18f, 0.4f);
            track.GetComponent<Renderer>().sharedMaterial = trackMat;
            var trackCollider = track.GetComponent<Collider>();
            if (trackCollider != null) Object.DestroyImmediate(trackCollider);

            // Motorized Trolley
            var mover = new GameObject("TrolleyMover");
            mover.transform.SetParent(railRoot.transform, false);
            mover.transform.localPosition = Vector3.zero;

            var railComp = mover.AddComponent<MovingRailTarget>();
            railComp.railOffset = offset;
            railComp.travelDuration = 3.5f;
            railComp.pauseDuration = 0.8f;

            var targetGo = CreateShootingTarget(mover.transform, "Target", Vector3.zero, dummyMat, headMat);
            railComp.attachedTarget = targetGo.GetComponentInChildren<ShootingTarget>();

            return railRoot;
        }

        static GameObject CreateAmmoCrate(Transform parent, string name, Vector3 pos, Material crateMat, Material neonMat)
        {
            var crateRoot = new GameObject(name);
            crateRoot.transform.SetParent(parent, false);
            crateRoot.transform.position = pos;

            var box = GameObject.CreatePrimitive(PrimitiveType.Cube);
            box.name = "CrateBody";
            box.transform.SetParent(crateRoot.transform, false);
            box.transform.localPosition = new Vector3(0f, 0.45f, 0f);
            box.transform.localScale = new Vector3(1.1f, 0.9f, 0.7f);
            box.GetComponent<Renderer>().sharedMaterial = crateMat;

            var glowStripe = GameObject.CreatePrimitive(PrimitiveType.Cube);
            glowStripe.name = "GlowStripe";
            glowStripe.transform.SetParent(crateRoot.transform, false);
            glowStripe.transform.localPosition = new Vector3(0f, 0.85f, 0f);
            glowStripe.transform.localScale = new Vector3(1.15f, 0.08f, 0.75f);
            glowStripe.GetComponent<Renderer>().sharedMaterial = neonMat;
            var glowCol = glowStripe.GetComponent<Collider>();
            if (glowCol != null) Object.DestroyImmediate(glowCol);

            var signGo = new GameObject("AmmoLabel");
            signGo.transform.SetParent(crateRoot.transform, false);
            signGo.transform.localPosition = new Vector3(0f, 1.2f, 0f);
            var tm = signGo.AddComponent<TextMesh>();
            tm.text = "AMMO REFILL";
            tm.fontSize = 36;
            tm.characterSize = 0.055f;
            tm.alignment = TextAlignment.Center;
            tm.anchor = TextAnchor.MiddleCenter;
            tm.color = new Color(0f, 0.941f, 1.0f);
            tm.fontStyle = FontStyle.Bold;

            var crateComp = crateRoot.AddComponent<AmmoCrate>();
            crateComp.resupplyRadius = 2.5f;

            return crateRoot;
        }

        static Material MakeMat(string name, Color color, Texture2D tex, float tiling, bool emissive = false, float metallic = 0.1f, float smoothness = 0.15f)
        {
            string path = MatDir + "/" + name + ".mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null)
            {
                mat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
                AssetDatabase.CreateAsset(mat, path);
            }
            mat.SetColor("_BaseColor", color);
            mat.SetFloat("_Smoothness", emissive ? 0.8f : smoothness);
            mat.SetFloat("_Metallic", emissive ? 0f : metallic);
            if (emissive)
            {
                mat.EnableKeyword("_EMISSION");
                mat.SetColor("_EmissionColor", color * 2.2f);
            }
            if (tex != null)
            {
                mat.SetTexture("_BaseMap", tex);
                mat.SetTextureScale("_BaseMap", new Vector2(tiling, tiling));
            }
            EditorUtility.SetDirty(mat);
            return mat;
        }

        static Material MakeGlassMat(string name, Color color)
        {
            string path = MatDir + "/" + name + ".mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null)
            {
                mat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
                AssetDatabase.CreateAsset(mat, path);
            }
            mat.SetFloat("_Surface", 1f); // Transparent
            mat.SetFloat("_Blend", 0f);   // Alpha blend
            mat.SetColor("_BaseColor", color);
            mat.SetFloat("_Smoothness", 0.95f);
            mat.SetFloat("_Metallic", 0.1f);
            mat.renderQueue = 3000;
            EditorUtility.SetDirty(mat);
            return mat;
        }

        static Texture2D GridTexture()
        {
            string path = MatDir + "/Grid.png";
            if (!File.Exists(path))
            {
                const int n = 256;
                var tex = new Texture2D(n, n, TextureFormat.RGBA32, false);
                Color fill = new Color(0.22f, 0.24f, 0.28f), line = new Color(0.45f, 0.48f, 0.55f);
                for (int y = 0; y < n; y++)
                    for (int x = 0; x < n; x++)
                    {
                        bool edge = x < 3 || y < 3 || x >= n - 3 || y >= n - 3;
                        tex.SetPixel(x, y, edge ? line : fill);
                    }
                tex.Apply();
                File.WriteAllBytes(path, tex.EncodeToPNG());
                Object.DestroyImmediate(tex);
                AssetDatabase.ImportAsset(path);
                var imp = (TextureImporter)AssetImporter.GetAtPath(path);
                imp.wrapMode = TextureWrapMode.Repeat;
                imp.mipmapEnabled = true;
                imp.filterMode = FilterMode.Trilinear;
                imp.anisoLevel = 8;
                imp.SaveAndReimport();
            }
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }

        static Texture2D HazardTexture()
        {
            string path = MatDir + "/HazardStripes.png";
            if (!File.Exists(path))
            {
                const int n = 256;
                var tex = new Texture2D(n, n, TextureFormat.RGBA32, false);
                Color yellow = new Color(1.0f, 0.85f, 0.05f);
                Color black = new Color(0.12f, 0.12f, 0.15f);
                for (int y = 0; y < n; y++)
                {
                    for (int x = 0; x < n; x++)
                    {
                        bool stripe = ((x + y) / 24) % 2 == 0;
                        tex.SetPixel(x, y, stripe ? yellow : black);
                    }
                }
                tex.Apply();
                File.WriteAllBytes(path, tex.EncodeToPNG());
                Object.DestroyImmediate(tex);
                AssetDatabase.ImportAsset(path);
                var imp = (TextureImporter)AssetImporter.GetAtPath(path);
                imp.wrapMode = TextureWrapMode.Repeat;
                imp.mipmapEnabled = true;
                imp.filterMode = FilterMode.Bilinear;
                imp.SaveAndReimport();
            }
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }

        static Texture2D PaperBullseyeTexture()
        {
            string path = MatDir + "/PaperBullseye.png";
            if (!File.Exists(path))
            {
                const int n = 512;
                var tex = new Texture2D(n, n, TextureFormat.RGBA32, false);
                Color paperBg = new Color(0.08f, 0.09f, 0.12f);
                Color torso = new Color(0.17f, 0.18f, 0.25f);
                Color cyanRing = new Color(0.0f, 0.941f, 1.0f);
                Color yellowRing = new Color(1.0f, 0.745f, 0.043f);
                Color whiteCross = new Color(0.85f, 0.9f, 1.0f, 0.6f);

                float center = n * 0.5f;
                float pxPerM = n / 0.55f;
                float r10 = 0.05f * pxPerM;
                float r9 = 0.10f * pxPerM;
                float r8 = 0.16f * pxPerM;
                float r7 = 0.22f * pxPerM;
                float torsoW = 0.26f * pxPerM;
                float torsoH = 0.42f * pxPerM;

                for (int y = 0; y < n; y++)
                {
                    for (int x = 0; x < n; x++)
                    {
                        float dx = x - center;
                        float dy = y - center;
                        float dist = Mathf.Sqrt(dx * dx + dy * dy);

                        Color col = paperBg;

                        // Torso silhouette check
                        if (Mathf.Abs(dx) <= torsoW && Mathf.Abs(dy) <= torsoH)
                        {
                            col = torso;
                        }

                        // Concentric rings
                        if (dist <= r10)
                        {
                            col = yellowRing;
                        }
                        else if (Mathf.Abs(dist - r9) < 2.5f)
                        {
                            col = cyanRing;
                        }
                        else if (Mathf.Abs(dist - r8) < 2.5f)
                        {
                            col = cyanRing;
                        }
                        else if (Mathf.Abs(dist - r7) < 2.5f)
                        {
                            col = cyanRing;
                        }

                        // Reticle crosshair lines
                        if ((Mathf.Abs(dx) < 1.5f || Mathf.Abs(dy) < 1.5f) && dist < r7)
                        {
                            col = Color.Lerp(col, whiteCross, 0.7f);
                        }

                        tex.SetPixel(x, y, col);
                    }
                }
                tex.Apply();
                File.WriteAllBytes(path, tex.EncodeToPNG());
                Object.DestroyImmediate(tex);
                AssetDatabase.ImportAsset(path);
                var imp = (TextureImporter)AssetImporter.GetAtPath(path);
                imp.wrapMode = TextureWrapMode.Clamp;
                imp.mipmapEnabled = true;
                imp.filterMode = FilterMode.Trilinear;
                imp.SaveAndReimport();
            }
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }
    }

    /// <summary>
    /// Proxy component that routes trigger enter/exit from stall volume to the RangeTerminal.
    /// </summary>
    public class RangeTerminalTriggerProxy : MonoBehaviour
    {
        public RangeTerminal terminal;

        void Start()
        {
            var col = GetComponent<BoxCollider>();
            if (col != null && terminal != null)
            {
                // Check if player spawned inside the trigger volume at startup
                var hits = Physics.OverlapBox(transform.position + col.center, col.size * 0.5f, transform.rotation);
                for (int i = 0; i < hits.Length; i++)
                {
                    if (hits[i].CompareTag("Player") || hits[i].GetComponent<CharacterController>() != null || hits[i].GetComponent<ZeroProtocol.Player.YoruController>() != null)
                    {
                        terminal.SetPlayerInside(true);
                        break;
                    }
                }
            }
        }

        void OnTriggerEnter(Collider other)
        {
            if (terminal != null && (other.CompareTag("Player") || other.GetComponent<ZeroProtocol.Player.YoruController>() != null || other.GetComponent<CharacterController>() != null))
            {
                terminal.SetPlayerInside(true);
            }
        }

        void OnTriggerExit(Collider other)
        {
            if (terminal != null && (other.CompareTag("Player") || other.GetComponent<ZeroProtocol.Player.YoruController>() != null || other.GetComponent<CharacterController>() != null))
            {
                terminal.SetPlayerInside(false);
            }
        }
    }
}
