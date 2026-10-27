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
    /// Builds the cyberpunk test arena scene:
    /// Multi-lane firing range (10m, 20m, 30m, 50m), shooting stalls, overhead neon signage,
    /// floor lane markings, ammo resupply crate, hybrid reactive targets (dummies, steel poppers, moving rail targets),
    /// Yoru character controller, combat systems, and third-person camera.
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
            var floorMat = MakeMat("ArenaGrid", new Color(1f, 1f, 1f), GridTexture(), 80f);
            var crateMat = MakeMat("ArenaCrate", new Color(0.86f, 0.52f, 0.20f), null, 1f);
            var blockMat = MakeMat("ArenaBlock", new Color(0.62f, 0.66f, 0.72f), null, 1f);
            var dummyMat = MakeMat("ArenaDummy", new Color(0.169f, 0.176f, 0.259f), null, 1f);      // Cyberpunk Idle #2B2D42
            var headMat = MakeMat("ArenaDummyHead", new Color(0.24f, 0.26f, 0.35f), null, 1f);
            var steelMat = MakeMat("ArenaSteel", new Color(0.38f, 0.42f, 0.48f), null, 1f);
            var neonCyanMat = MakeMat("ArenaNeonCyan", new Color(0.0f, 0.941f, 1.0f), null, 1f, true);
            var neonYellowMat = MakeMat("ArenaNeonYellow", new Color(1.0f, 0.745f, 0.043f), null, 1f, true);
            var stripeMat = MakeMat("ArenaStripe", new Color(1.0f, 0.85f, 0.1f), null, 1f, true);

            Scene scene = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);
            Directory.CreateDirectory("Assets/Scenes");

            var root = new GameObject("Arena").transform;

            // Floor: 80m x 110m centered at Z = 15m, top surface sits at y = 0 (covers Z = -40m to +70m)
            var floor = GameObject.CreatePrimitive(PrimitiveType.Cube);
            floor.name = "Floor";
            floor.transform.SetParent(root);
            floor.transform.position = new Vector3(0f, -0.5f, 15f);
            floor.transform.localScale = new Vector3(80f, 1f, 110f);
            floor.GetComponent<Renderer>().sharedMaterial = floorMat;

            // Boundary Walls
            Box(root, "Wall_North", new Vector3(80f, 5f, 1.2f), new Vector3(0f, 2.5f, 58f), blockMat);
            Box(root, "Wall_South", new Vector3(80f, 5f, 1.2f), new Vector3(0f, 2.5f, -38f), blockMat);
            Box(root, "Wall_East", new Vector3(1.2f, 5f, 96f), new Vector3(39.4f, 2.5f, 10f), blockMat);
            Box(root, "Wall_West", new Vector3(1.2f, 5f, 96f), new Vector3(-39.4f, 2.5f, 10f), blockMat);

            // Arena Props (crates, pillars, platform, stairs)
            Box(root, "Crate_S", new Vector3(1f, 1f, 1f), new Vector3(16f, 0.5f, 4f), crateMat);
            Box(root, "Crate_M", new Vector3(1.5f, 1.5f, 1.5f), new Vector3(18f, 0.75f, 6f), crateMat);
            Box(root, "Crate_L", new Vector3(2f, 2f, 2f), new Vector3(-16f, 1f, 5f), crateMat);
            Box(root, "Crate_Stack", new Vector3(1f, 1f, 1f), new Vector3(-16f, 2.5f, 5f), crateMat);
            Box(root, "Pillar_A", new Vector3(1.2f, 5f, 1.2f), new Vector3(-18f, 2.5f, -4f), blockMat);
            Box(root, "Pillar_B", new Vector3(1.2f, 5f, 1.2f), new Vector3(18f, 2.5f, -4f), blockMat);

            // Stairs and elevated platform
            for (int i = 0; i < 4; i++)
            {
                Box(root, "Stair_" + i, new Vector3(3f, 0.3f * (i + 1), 0.8f),
                    new Vector3(-20f, 0.15f * (i + 1), 8f + 0.8f * i), blockMat);
            }
            Box(root, "Platform", new Vector3(6f, 1.2f, 6f), new Vector3(-20f, 0.6f, 14f), blockMat);

            // -----------------------------------------------------------
            // MULTI-LANE FIRING RANGE (Player starts at Z = -4)
            // Lane 1: X = -9m, Distance = 10m (Z = 6m) -> Silhouette Dummy
            // Lane 2: X = -3m, Distance = 20m (Z = 16m) -> Silhouette Dummy
            // Lane 3: X = 3m, Distance = 30m (Z = 26m) -> Steel Popper Target
            // Lane 4: X = 9m, Distance = 50m (Z = 46m) -> Elevated Moving Rail Target
            // -----------------------------------------------------------
            var rangeRoot = new GameObject("FiringRange").transform;
            rangeRoot.SetParent(root);

            // 1. Shooting Stalls & Dividers at Booth (Z = -4m)
            float[] dividerX = { -12f, -6f, 0f, 6f, 12f };
            for (int i = 0; i < dividerX.Length; i++)
            {
                // Stall partition wall
                Box(rangeRoot, $"StallDivider_{i}", new Vector3(0.2f, 1.4f, 3.5f), new Vector3(dividerX[i], 0.7f, -4f), blockMat);
                // Safety railing top
                var rail = Box(rangeRoot, $"StallRailing_{i}", new Vector3(0.25f, 0.08f, 3.5f), new Vector3(dividerX[i], 1.44f, -4f), neonCyanMat);
                var col = rail.GetComponent<Collider>();
                if (col != null) Object.DestroyImmediate(col);
            }

            // Overhead Gantry Frame & Neon Distance Signs (Y = 3.6m, Z = -2.5m)
            var gantryBeam = Box(rangeRoot, "OverheadGantry", new Vector3(24.5f, 0.25f, 0.4f), new Vector3(0f, 3.6f, -2.5f), blockMat);
            var gantryCol = gantryBeam.GetComponent<Collider>();
            if (gantryCol != null) Object.DestroyImmediate(gantryCol);

            CreateNeonSign(rangeRoot, "10M", new Vector3(-9f, 3.6f, -2.5f), blockMat, new Color(0.0f, 0.941f, 1.0f));
            CreateNeonSign(rangeRoot, "20M", new Vector3(-3f, 3.6f, -2.5f), blockMat, new Color(0.0f, 0.941f, 1.0f));
            CreateNeonSign(rangeRoot, "30M", new Vector3(3f, 3.6f, -2.5f), blockMat, new Color(1.0f, 0.745f, 0.043f));
            CreateNeonSign(rangeRoot, "50M", new Vector3(9f, 3.6f, -2.5f), blockMat, new Color(1.0f, 0.2f, 0.4f));

            // Floor Lane Divider Stripes along Z
            for (int i = 0; i < dividerX.Length; i++)
            {
                float laneLen = (i == 4) ? 52f : ((i == 3) ? 32f : 22f);
                var line = Box(rangeRoot, $"FloorDividerLine_{i}", new Vector3(0.08f, 0.01f, laneLen),
                    new Vector3(dividerX[i], 0.005f, -2.25f + laneLen * 0.5f), neonCyanMat);
                var c = line.GetComponent<Collider>();
                if (c != null) Object.DestroyImmediate(c);
            }

            // High-Contrast Floor Threshold Stripes (Distance Markers)
            CreateFloorThresholdStripe(rangeRoot, "Threshold_10M", new Vector3(-9f, 0.006f, 6f), 5.8f, stripeMat);
            CreateFloorThresholdStripe(rangeRoot, "Threshold_20M", new Vector3(-3f, 0.006f, 16f), 5.8f, stripeMat);
            CreateFloorThresholdStripe(rangeRoot, "Threshold_30M", new Vector3(3f, 0.006f, 26f), 5.8f, stripeMat);
            CreateFloorThresholdStripe(rangeRoot, "Threshold_50M", new Vector3(9f, 0.006f, 46f), 5.8f, stripeMat);

            // Interactive Ammo Resupply Station at Booth (X = -13m, Z = -4m)
            CreateAmmoCrate(rangeRoot, "AmmoResupplyStation", new Vector3(-13.2f, 0f, -4f), crateMat, neonCyanMat);

            // Targets in the 4 Lanes
            // Lane 1 (10m): Silhouette Dummy
            CreateShootingTarget(rangeRoot, "Target_10m_Dummy", new Vector3(-9f, 0f, 6f), dummyMat, headMat);

            // Lane 2 (20m): Silhouette Dummy
            CreateShootingTarget(rangeRoot, "Target_20m_Dummy", new Vector3(-3f, 0f, 16f), dummyMat, headMat);

            // Lane 3 (30m): Steel Popper Target (drops flat 90 deg, respawns after 2.5s)
            CreatePopperTarget(rangeRoot, "Target_30m_Popper", new Vector3(3f, 0f, 26f), steelMat, blockMat);

            // Lane 4 (50m): Elevated Moving Rail Target (sinusoidal motion with 0.8s turnaround pause)
            CreateElevatedRailTarget(rangeRoot, "Target_50m_Rail", new Vector3(6.5f, 1.4f, 46f), new Vector3(5f, 0f, 0f), blockMat, dummyMat, headMat);

            // Auxiliary Targets in Arena
            CreateShootingTarget(root, "Dummy_Aux_1", new Vector3(0f, 0f, 12f), dummyMat, headMat);
            CreateShootingTarget(root, "Dummy_Aux_2", new Vector3(-18f, 0f, 12f), dummyMat, headMat);
            CreateShootingTarget(root, "Dummy_Aux_3", new Vector3(18f, 0f, 18f), dummyMat, headMat);

            // -----------------------------------------------------------
            // PLAYER & CAMERA RIG SETUP
            // -----------------------------------------------------------
            var yoruPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(YoruPrefabPath);
            var player = new GameObject("Player");
            player.tag = "Player";
            player.transform.position = new Vector3(0f, 0.05f, -4f);
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
            cam.transform.position = new Vector3(0f, 2.2f, -9f);

            PostFxBuilder.Add(cam);

            var dirLight = Object.FindFirstObjectByType<Light>();
            if (dirLight != null) { dirLight.shadows = LightShadows.Soft; dirLight.intensity = 1.1f; }

            EditorSceneManager.SaveScene(scene, ScenePath);
            AssetDatabase.SaveAssets();
            Debug.Log("[ZeroProtocol] Multi-Lane Firing Range & Arena built: " + ScenePath);
        }

        static GameObject Box(Transform parent, string name, Vector3 size, Vector3 pos, Material mat)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = name;
            go.transform.SetParent(parent);
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
            backplate.transform.localScale = new Vector3(1.8f, 0.65f, 0.12f);
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

        static GameObject CreateShootingTarget(Transform parent, string name, Vector3 pos, Material bodyMat, Material headMat)
        {
            var targetRoot = new GameObject(name);
            targetRoot.transform.SetParent(parent);
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
            targetRoot.transform.SetParent(parent);
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
            railRoot.transform.SetParent(parent);
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
            crateRoot.transform.SetParent(parent);
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

        static Material MakeMat(string name, Color color, Texture2D tex, float tiling, bool emissive = false)
        {
            string path = MatDir + "/" + name + ".mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null)
            {
                mat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
                AssetDatabase.CreateAsset(mat, path);
            }
            mat.SetColor("_BaseColor", color);
            mat.SetFloat("_Smoothness", emissive ? 0.8f : 0.15f);
            mat.SetFloat("_Metallic", emissive ? 0f : 0.1f);
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

        static Texture2D GridTexture()
        {
            string path = MatDir + "/Grid.png";
            if (!File.Exists(path))
            {
                const int n = 256;
                var tex = new Texture2D(n, n, TextureFormat.RGBA32, false);
                Color fill = new Color(0.32f, 0.35f, 0.39f), line = new Color(0.62f, 0.66f, 0.71f);
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
    }
}
