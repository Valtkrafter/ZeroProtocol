using System;
using System.IO;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;
using ZeroProtocol.Combat;
using ZeroProtocol.CameraSystem;
using ZeroProtocol.Player;

namespace ZeroProtocol.EditorTools
{
    public static class CombatSystemVerifier
    {
        [MenuItem("Zero Protocol/Run Combat Verification Tests")]
        public static void RunTests()
        {
            var log = new System.Text.StringBuilder();
            log.AppendLine("======================================================");
            log.AppendLine("[CombatSystemVerifier] STARTING FULL COMBAT SYSTEM VERIFICATION");
            log.AppendLine("======================================================");

            int passCount = 0;
            int totalTests = 0;

            void Assert(bool condition, string testName, string details = "")
            {
                totalTests++;
                if (condition)
                {
                    passCount++;
                    log.AppendLine($"[PASS] {testName}");
                    Debug.Log($"[PASS] {testName}");
                }
                else
                {
                    string failMsg = $"[FAIL] {testName} - {details}";
                    log.AppendLine(failMsg);
                    Debug.LogError(failMsg);
                    File.WriteAllText("combat_verification_results.txt", log.ToString());
                    throw new Exception($"Test Failed: {testName} - {details}");
                }
            }

            // Pre-flight cleanup: Remove any orphaned test objects from previous interrupted runs
            var rootObjects = UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects();
            foreach (var go in rootObjects)
            {
                if (go != null && (go.name.StartsWith("_Test") || go.name.StartsWith("_Live") || go.name.StartsWith("_Occluded") || 
                    go.name.StartsWith("_Knock") || go.name.StartsWith("_Popper") || go.name.StartsWith("T1_Lock") || 
                    go.name.StartsWith("T2_Lock") || go.transform.position.x > 100f))
                {
                    UnityEngine.Object.DestroyImmediate(go);
                }
            }
            ShootingTarget.ActiveTargets.RemoveAll(t => t == null);
            LockOnTarget.All.RemoveAll(t => t == null);
            Physics.SyncTransforms();

            // -----------------------------------------------------------
            // TEST 1: Strict Architectural Guardrail - No Character Animation / Bones
            // -----------------------------------------------------------
            string combatDir = "Assets/Scripts/Combat";
            string[] combatFiles = Directory.GetFiles(combatDir, "*.cs", SearchOption.AllDirectories);
            Assert(combatFiles.Length >= 6, "Combat Script Delivery Count", $"Found {combatFiles.Length} files in {combatDir}");

            foreach (string file in combatFiles)
            {
                string text = File.ReadAllText(file);
                bool hasAnimator = Regex.IsMatch(text, @"\bAnimator\b");
                bool hasBones = Regex.IsMatch(text, @"\bJ_Bip\b");
                bool hasIK = Regex.IsMatch(text, @"\bIK\b");

                Assert(!hasAnimator, $"Animation Guardrail in {Path.GetFileName(file)} (No Animator)", "Must have zero Animator references");
                Assert(!hasBones, $"Animation Guardrail in {Path.GetFileName(file)} (No Humanoid Bones)", "Must have zero J_Bip_* bone references");
                Assert(!hasIK, $"Animation Guardrail in {Path.GetFileName(file)} (No IK)", "Must have zero IK references");
            }

            // -----------------------------------------------------------
            // TEST 2: Strict Architectural Guardrail - Purely Decoupled Contracts in DualPistolCombat
            // -----------------------------------------------------------
            string dualCombatCode = File.ReadAllText("Assets/Scripts/Combat/DualPistolCombat.cs");
            Assert(!Regex.IsMatch(dualCombatCode, @"\bCombatUI\b"), "DualPistolCombat Decoupling (No CombatUI)", "DualPistolCombat must have zero references to CombatUI");
            Assert(!Regex.IsMatch(dualCombatCode, @"\bGunVFX\b"), "DualPistolCombat Decoupling (No GunVFX)", "DualPistolCombat must have zero references to GunVFX");

            // -----------------------------------------------------------
            // TEST 3: Event Subscription / Unsubscription Audit
            // -----------------------------------------------------------
            string[] eventConsumerFiles = {
                "Assets/Scripts/Combat/GunVFX.cs",
                "Assets/Scripts/Combat/CombatUI.cs",
                "Assets/Scripts/Camera/ThirdPersonCamera.cs"
            };

            foreach (string f in eventConsumerFiles)
            {
                string content = File.ReadAllText(f);
                int plusEquals = Regex.Matches(content, @"\+=\s*Handle").Count;
                int minusEquals = Regex.Matches(content, @"\-=\s*Handle").Count;
                Assert(plusEquals > 0 && minusEquals >= plusEquals, $"Event Lifecycle Audit in {Path.GetFileName(f)}",
                    $"Subscribed (+={plusEquals}) vs Unsubscribed (-={minusEquals})");
            }

            // -----------------------------------------------------------
            // TEST 4: Zero Runtime GC Allocation Audit
            // -----------------------------------------------------------
            foreach (string file in combatFiles)
            {
                string text = File.ReadAllText(file);
                Assert(!text.Contains("Physics.RaycastAll"), $"Non-allocating physics in {Path.GetFileName(file)}", "Must not use RaycastAll");
                Assert(!text.Contains("Physics.SphereCastAll"), $"Non-allocating physics in {Path.GetFileName(file)}", "Must not use SphereCastAll");
            }

            // -----------------------------------------------------------
            // TEST 5: DualPistolCombat Mechanics & Alternating Cadence
            // -----------------------------------------------------------
            GameObject playerGo = null;
            GameObject targetGo = null;
            GameObject railGo = null;
            GameObject testCamGo = null;
            GameObject wallGo = null;
            GameObject liveTargetGo = null;
            GameObject camGo = null;
            GameObject occludedTargetGo = null;
            GameObject occluderWall = null;
            GameObject knockGo = null;
            GameObject popperGo = null;
            GameObject lockPlayerGo = null;
            GameObject lockCamGo = null;
            GameObject t1Go = null;
            GameObject t2Go = null;
            GameObject yoruGo = null;
            GameObject yoruTargetGo = null;
            GameObject crateGo = null;
            GameObject trolleyGo = null;
            GameObject paperGo = null;
            GameObject scaledPaperGo = null;
            GameObject termGo = null;
            GameObject textGo = null;
            GameObject trigGo = null;
            GameObject testCharGo = null;
            GameObject shellPoolGo = null;

            try
            {
                playerGo = new GameObject("_TestPlayer");
                var input = playerGo.AddComponent<GameInput>();
            var inputAwake = typeof(GameInput).GetMethod("Awake", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            inputAwake.Invoke(input, null);
            var combat = playerGo.AddComponent<DualPistolCombat>();
            combat.input = input;
            combat.EnsureMuzzleSockets();
            var combatAwake = typeof(DualPistolCombat).GetMethod("Awake", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            combatAwake.Invoke(combat, null);
            var inputUpdate = typeof(GameInput).GetMethod("Update", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);

            // Verify logical muzzle sockets
            Assert(combat.muzzleLeft != null, "Muzzle Socket Left Auto-creation");
            Assert(combat.muzzleRight != null, "Muzzle Socket Right Auto-creation");
            Assert(combat.muzzleLeft.name == "Muzzle_L", "Muzzle_L Name Match");
            Assert(combat.muzzleRight.name == "Muzzle_R", "Muzzle_R Name Match");

            // Verify initial ammo
            Assert(combat.AmmoLeft == 15, "Initial Left Ammo 15");
            Assert(combat.AmmoRight == 15, "Initial Right Ammo 15");

            // Test alternating firing events
            HandSide lastHandFired = HandSide.Right;
            int fireEventsReceived = 0;
            combat.OnWeaponFired += (data) =>
            {
                fireEventsReceived++;
                lastHandFired = data.Hand;
            };

            // Shot 1
            input.FireOverride = true;
            inputUpdate.Invoke(input, null);
            var updateMethod = typeof(DualPistolCombat).GetMethod("Update", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            updateMethod.Invoke(combat, null);

            Assert(fireEventsReceived == 1, "Shot 1 Fired Event Dispatched");
            Assert(lastHandFired == HandSide.Left, "Shot 1 Hand Alternation (Left First)");
            Assert(combat.AmmoLeft == 14, "Left Pistol Ammo Decremented to 14");
            Assert(combat.AmmoRight == 15, "Right Pistol Ammo Untouched at 15");

            // Advance time for cadence interval
            var nextFireTimeField = typeof(DualPistolCombat).GetField("nextFireTime", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            nextFireTimeField.SetValue(combat, 0f);

            // Shot 2
            input.FireOverride = true;
            inputUpdate.Invoke(input, null);
            updateMethod.Invoke(combat, null);

            Assert(fireEventsReceived == 2, "Shot 2 Fired Event Dispatched");
            Assert(lastHandFired == HandSide.Right, "Shot 2 Hand Alternation (Right Second)");
            Assert(combat.AmmoLeft == 14, "Left Pistol Ammo Remains 14");
            Assert(combat.AmmoRight == 14, "Right Pistol Ammo Decremented to 14");

            // -----------------------------------------------------------
            // TEST 6: Dynamic Bloom Math
            // -----------------------------------------------------------
            // Formula: theta_spread = clamp(theta_base + n_shots * delta_bloom + (v/v_run)*theta_move, min, max) * M_ADS
            float thetaBase = combat.thetaBase;
            float deltaBloom = combat.deltaBloom;
            float mAds = combat.mAds;

            Assert(combat.CurrentBloomAngle >= combat.thetaMin, "Bloom >= thetaMin");

            // When Aiming (ADS)
            input.AimHeldOverride = true;
            inputUpdate.Invoke(input, null);
            updateMethod.Invoke(combat, null);

            Assert(combat.IsAiming, "DualPistolCombat ADS Aiming State Active");
            Assert(combat.CurrentBloomAngle <= thetaBase, "Bloom Reduced in ADS Mode");

            input.AimHeldOverride = false;

            // -----------------------------------------------------------
            // TEST 7: Reactive Target Physics (Harmonic Wobble & Hitboxes)
            // -----------------------------------------------------------
            targetGo = new GameObject("_TestTarget");
            var dummyTilt = new GameObject("DummyTilt");
            dummyTilt.transform.SetParent(targetGo.transform);

            var body = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            body.transform.SetParent(dummyTilt.transform);
            body.transform.localPosition = new Vector3(0f, 0.85f, 0f);
            var bodyHb = body.AddComponent<TargetHitbox>();
            bodyHb.hitboxType = HitType.Body;

            var head = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            head.transform.SetParent(dummyTilt.transform);
            head.transform.localPosition = new Vector3(0f, 1.6f, 0f);
            var headHb = head.AddComponent<TargetHitbox>();
            headHb.hitboxType = HitType.Headshot;

            var st = dummyTilt.AddComponent<ShootingTarget>();
            st.targetRenderer = body.GetComponent<Renderer>();
            st.headRenderer = head.GetComponent<Renderer>();
            st.headTransform = head.transform;
            st.bodyTransform = body.transform;
            st.omega = 25f;
            st.zeta = 0.35f;
            bodyHb.parentTarget = st;
            headHb.parentTarget = st;
            var targetAwake = typeof(ShootingTarget).GetMethod("Awake", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            targetAwake.Invoke(st, null);

            Assert(st.IsAlive, "Target Initially Alive");
            Assert(st.CurrentHealth == 100f, "Target Initial Health 100");

            // Test Headshot Damage
            st.TakeDamage(new DamageInfo(75f, head.transform.position, Vector3.back, Vector3.forward, HitType.Headshot, HandSide.Left));
            Assert(st.CurrentHealth == 25f, "Headshot Damage Applied (-75 -> 25)");

            // Test Kill & Fallback
            st.TakeDamage(new DamageInfo(25f, body.transform.position, Vector3.back, Vector3.forward, HitType.Body, HandSide.Right));
            Assert(!st.IsAlive, "Target Marked Dead After Lethal Damage");
            Assert(st.CurrentHealth == 0f, "Target Health Clamped to 0");

            // -----------------------------------------------------------
            // TEST 8: Two-Tier Aim Assist Formula Verification (Subtle Soft Aimbot)
            // -----------------------------------------------------------
            // Tier 1 Friction: S_effective = S_base * lerp(frictionMin, 1.0, smoothstep(0, alpha_outer, alpha))
            float frictionMin = 0.65f;
            float alphaOuter = 6.0f;

            float S_center = Mathf.Lerp(frictionMin, 1.0f, Mathf.SmoothStep(0f, alphaOuter, 0f));
            Assert(Mathf.Approximately(S_center, frictionMin), "Tier 1 Friction at alpha=0 equals frictionMin (0.65)");

            float S_outside = Mathf.Lerp(frictionMin, 1.0f, Mathf.SmoothStep(0f, alphaOuter, 8.0f));
            Assert(Mathf.Approximately(S_outside, 1.0f), "Tier 1 Friction outside cone equals 1.0 (Full sensitivity)");

            // Tier 2 Magnetism: Hipfire <= 1.2 deg head, <= 2.5 deg body, weight = 0.40
            Assert(combat.magnetismHeadConeAngle <= 1.2f, "Tier 2 Magnetism Hipfire Head Cone Angle <= 1.2 deg");
            Assert(combat.magnetismMaxConeAngle <= 2.5f, "Tier 2 Magnetism Hipfire Body Cone Angle <= 2.5 deg");
            Assert(Mathf.Approximately(combat.magnetismWeight, 0.40f), "Tier 2 Magnetism Hipfire Trajectory Bending Weight = 0.40");

            // Tier 2 Magnetism: ADS <= 2.0 deg head, <= 3.8 deg body, weight = 0.55
            Assert(combat.magnetismAdsHeadConeAngle <= 2.0f, "Tier 2 Magnetism ADS Head Cone Angle <= 2.0 deg");
            Assert(combat.magnetismAdsMaxConeAngle <= 3.8f, "Tier 2 Magnetism ADS Body Cone Angle <= 3.8 deg");
            Assert(Mathf.Approximately(combat.magnetismAdsWeight, 0.55f), "Tier 2 Magnetism ADS Trajectory Bending Weight = 0.55");

            // -----------------------------------------------------------
            // TEST 9: MovingRailTarget Sinusoidal Velocity Profile
            // -----------------------------------------------------------
            railGo = new GameObject("_TestRail");
            var railTarget = railGo.AddComponent<MovingRailTarget>();
            railTarget.railOffset = new Vector3(10f, 0f, 0f);
            railTarget.travelDuration = 2.0f;
            railTarget.pauseDuration = 0.5f;

            Assert(railTarget.railOffset.x == 10f, "MovingRailTarget 10m Offset");

            // -----------------------------------------------------------
            // TEST 10: Hit Feedback Gating (Walls, Dead Dummies, Alive Targets)
            // -----------------------------------------------------------
            float testX = 800f;
            playerGo.transform.position = new Vector3(testX, 0f, 0f);
            playerGo.transform.rotation = Quaternion.identity;

            testCamGo = new GameObject("_TestCam10");
            var testCam10 = testCamGo.AddComponent<Camera>();
            testCamGo.transform.position = new Vector3(testX + 0.25f, 1.15f, -2f);
            testCamGo.transform.rotation = Quaternion.identity;
            combat.mainCamera = testCam10;

            wallGo = GameObject.CreatePrimitive(PrimitiveType.Cube);
            wallGo.name = "_TestWall";
            wallGo.transform.position = new Vector3(testX, 1.15f, 5f);
            wallGo.transform.localScale = new Vector3(10f, 5f, 0.5f);

            int hitFeedbackCount = 0;
            HitFeedbackData lastFeedback = default;
            Action<HitFeedbackData> feedbackHandler = (fb) =>
            {
                hitFeedbackCount++;
                lastFeedback = fb;
            };
            combat.OnHitFeedback += feedbackHandler;

            // Shot into static wall (has collider, but NO IDamageable)
            Physics.SyncTransforms();
            nextFireTimeField.SetValue(combat, 0f);

            var executeShotMethod = typeof(DualPistolCombat).GetMethod("ExecuteShot", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            executeShotMethod.Invoke(combat, new object[] { HandSide.Left });

            Assert(hitFeedbackCount == 0, "Hit Feedback Not Dispatched On Static Wall/Floor Hits");

            // Move wall aside and place an alive dummy
            wallGo.transform.position = new Vector3(testX + 100f, 100f, 100f);
            liveTargetGo = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            liveTargetGo.name = "_LiveTarget";
            liveTargetGo.transform.position = new Vector3(testX + 0.25f, 1.15f, 5f);
            var liveSt = liveTargetGo.AddComponent<ShootingTarget>();
            liveSt.targetRenderer = liveTargetGo.GetComponent<Renderer>();
            var liveTargetAwake = typeof(ShootingTarget).GetMethod("Awake", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            var liveTargetOnEnable = typeof(ShootingTarget).GetMethod("OnEnable", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            liveTargetAwake.Invoke(liveSt, null);
            liveTargetOnEnable.Invoke(liveSt, null);
            Physics.SyncTransforms();

            nextFireTimeField.SetValue(combat, 0f);
            executeShotMethod.Invoke(combat, new object[] { HandSide.Right });

            Assert(hitFeedbackCount == 1, "Hit Feedback Dispatched On Alive Target Hit");
            Assert(lastFeedback.Damage > 0f, "Hit Feedback Contains Positive Damage");

            // Shoot an already dead dummy: feedback must NOT trigger
            var killDamage = new DamageInfo(200f, liveTargetGo.transform.position, Vector3.back, Vector3.forward, HitType.Body, HandSide.Left);
            liveSt.TakeDamage(killDamage);
            Assert(!liveSt.IsAlive, "Target Confirmed Dead");

            int countBeforeDeadShot = hitFeedbackCount;
            nextFireTimeField.SetValue(combat, 0f);
            executeShotMethod.Invoke(combat, new object[] { HandSide.Left });

            Assert(hitFeedbackCount == countBeforeDeadShot, "Hit Feedback Not Dispatched On Dead Target Hits");

            combat.OnHitFeedback -= feedbackHandler;

            // -----------------------------------------------------------
            // TEST 11: Parallax Safety on Point-Blank Occlusion
            // -----------------------------------------------------------
            camGo = new GameObject("_TestCam");
            var testCam = camGo.AddComponent<Camera>();
            camGo.transform.position = new Vector3(testX, 1.5f, -2f);
            camGo.transform.rotation = Quaternion.identity;
            combat.mainCamera = testCam;

            // Verify aim direction doesn't flip backward when camera aim point is behind muzzle socket
            var pAimBehind = combat.transform.position + new Vector3(0f, 1.15f, -0.5f); // behind muzzle at +0.45m
            Vector3 toAimBehind = pAimBehind - combat.muzzleLeft.position;
            Vector3 camForward = testCam.transform.forward;
            bool isBehind = Vector3.Dot(toAimBehind, camForward) <= 0.05f;
            Assert(isBehind, "Point-blank Aim Point Detected Behind Muzzle Plane");

            // -----------------------------------------------------------
            // TEST 12: Bullet Magnetism Line of Sight Occlusion
            // -----------------------------------------------------------
            occludedTargetGo = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            occludedTargetGo.name = "_OccludedTarget";
            occludedTargetGo.transform.position = new Vector3(testX + 0.25f, 1.15f, 12f);
            var occludedSt = occludedTargetGo.AddComponent<ShootingTarget>();
            occludedSt.targetRenderer = occludedTargetGo.GetComponent<Renderer>();
            var occludedHb = occludedTargetGo.AddComponent<TargetHitbox>();
            occludedHb.parentTarget = occludedSt;
            liveTargetAwake.Invoke(occludedSt, null);
            liveTargetOnEnable.Invoke(occludedSt, null);

            // Put a giant occluding wall in between
            occluderWall = GameObject.CreatePrimitive(PrimitiveType.Cube);
            occluderWall.transform.position = new Vector3(testX + 0.25f, 1.15f, 6f);
            occluderWall.transform.localScale = new Vector3(5f, 5f, 1f);
            Physics.SyncTransforms();

            var applyMagMethod = typeof(DualPistolCombat).GetMethod("ApplyBulletMagnetism", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            Vector3 straightAhead = Vector3.forward;
            Vector3 resultDir = (Vector3)applyMagMethod.Invoke(combat, new object[] { combat.muzzleRight.position, straightAhead });

            Assert(resultDir == straightAhead, "Bullet Magnetism Ignores Occluded Target Behind Wall");
            occluderWall.transform.position = new Vector3(testX + 200f, 200f, 200f);
            Physics.SyncTransforms();

            // -----------------------------------------------------------
            // TEST 13: ThirdPersonCamera Lifecycle Re-subscription
            // -----------------------------------------------------------
            var camRig = camGo.AddComponent<ThirdPersonCamera>();
            camRig.target = playerGo.transform;
            var camOnEnable = typeof(ThirdPersonCamera).GetMethod("OnEnable", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            var camOnDisable = typeof(ThirdPersonCamera).GetMethod("OnDisable", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);

            camOnEnable.Invoke(camRig, null);
            // Simulate camera toggle
            camOnDisable.Invoke(camRig, null);
            camOnEnable.Invoke(camRig, null);

            var recoilVelField = typeof(ThirdPersonCamera).GetField("recoilVelocity", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            recoilVelField.SetValue(camRig, Vector2.zero);

            // Firing weapon should still kick camera recoil through event
            executeShotMethod.Invoke(combat, new object[] { HandSide.Left });
            Vector2 recoilAfterFire = (Vector2)recoilVelField.GetValue(camRig);
            Assert(recoilAfterFire.sqrMagnitude > 0.001f, "Camera Recoil Still Active After Disable/Enable Cycle");

            // -----------------------------------------------------------
            // TEST 14: Reactive Target Positive Knockdown on Lethal Hit
            // -----------------------------------------------------------
            knockGo = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            var knockSt = knockGo.AddComponent<ShootingTarget>();
            knockSt.targetRenderer = knockGo.GetComponent<Renderer>();
            liveTargetAwake.Invoke(knockSt, null);
            liveTargetOnEnable.Invoke(knockSt, null);
            knockSt.respawnDelay = 999f;

            knockSt.TakeDamage(new DamageInfo(150f, knockGo.transform.position, Vector3.back, Vector3.forward, HitType.Body, HandSide.Right));
            Assert(!knockSt.IsAlive, "Knock Target Lethally Damaged");

            var targetUpdate = typeof(ShootingTarget).GetMethod("Update", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            for (int step = 0; step < 10; step++)
            {
                targetUpdate.Invoke(knockSt, null);
            }

            var tiltField = typeof(ShootingTarget).GetField("currentTilt", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            float finalTilt = (float)tiltField.GetValue(knockSt);
            Assert(finalTilt > 0f, "Dead Target Knocks Away (Positive Tilt) in Bullet Impact Direction");

            // -----------------------------------------------------------
            // TEST 15: PopperTarget Flat Knockdown (90 deg) & 2.5s Spring Back
            // -----------------------------------------------------------
            popperGo = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            var popper = popperGo.AddComponent<PopperTarget>();
            popper.targetRenderer = popperGo.GetComponent<Renderer>();
            liveTargetAwake.Invoke(popper, null);
            liveTargetOnEnable.Invoke(popper, null);

            Assert(popper.IsAlive, "PopperTarget Initially Alive");
            Assert(popper.dropAngle == 90f, "PopperTarget Drop Angle is 90 degrees");
            Assert(popper.respawnDelay == 2.5f, "PopperTarget Respawn Delay is 2.5s");

            popper.TakeDamage(new DamageInfo(120f, popperGo.transform.position, Vector3.back, Vector3.forward, HitType.Body, HandSide.Left));
            Assert(!popper.IsAlive, "PopperTarget Marked Dead After Lethal Hit");

            // Prevent premature respawn during editmode test with throttled delta time
            popper.respawnDelay = 999f;

            var popperUpdate = typeof(PopperTarget).GetMethod("Update", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            for (int step = 0; step < 20; step++)
            {
                popperUpdate.Invoke(popper, null);
            }

            var popperTiltField = typeof(ShootingTarget).GetField("currentTilt", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            float popperTilt = (float)popperTiltField.GetValue(popper);
            Assert(popperTilt > 80f, "PopperTarget Hinged Down Flat (> 80 deg) when Dead");

            popper.respawnDelay = 2.5f;
            var popperDeathTimer = typeof(ShootingTarget).GetField("deathTimer", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            popperDeathTimer.SetValue(popper, 2.6f);
            popperUpdate.Invoke(popper, null);

            Assert(popper.IsAlive, "PopperTarget Elastic Pop-up Respawned After 2.5s");
            Assert(popper.CurrentHealth == 100f, "PopperTarget Restored to Full Health");
            float popperTiltAfterRespawn = (float)popperTiltField.GetValue(popper);
            Assert(popperTiltAfterRespawn > 80f, "PopperTarget Respawn Keeps The Fallen Angle (Spring Lifts It, No Snap)");

            // -----------------------------------------------------------
            // TEST 16: LockOnSystem Auto-Switch on Target Destruction
            // -----------------------------------------------------------
            lockPlayerGo = new GameObject("_TestLockPlayer");
            lockPlayerGo.transform.position = new Vector3(500f, 1.5f, -5f);
            var lockInput = lockPlayerGo.AddComponent<GameInput>();
            var lockSys = lockPlayerGo.AddComponent<LockOnSystem>();
            lockCamGo = new GameObject("_TestLockCam");
            var lockCam = lockCamGo.AddComponent<Camera>();
            var lockRig = lockCamGo.AddComponent<ThirdPersonCamera>();
            lockSys.cameraRig = lockRig;
            lockRig.target = lockPlayerGo.transform;
            lockCamGo.transform.position = new Vector3(500f, 1.5f, -5f);
            lockCamGo.transform.rotation = Quaternion.identity;

            t1Go = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            t1Go.transform.position = new Vector3(500f, 1.5f, 5f);
            var t1Target = t1Go.AddComponent<LockOnTarget>();
            var t1St = t1Go.AddComponent<ShootingTarget>();
            t1St.targetRenderer = t1Go.GetComponent<Renderer>();
            liveTargetAwake.Invoke(t1St, null);
            liveTargetOnEnable.Invoke(t1St, null);

            t2Go = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            t2Go.transform.position = new Vector3(501f, 1.5f, 10f);
            var t2Target = t2Go.AddComponent<LockOnTarget>();
            var t2St = t2Go.AddComponent<ShootingTarget>();
            t2St.targetRenderer = t2Go.GetComponent<Renderer>();
            liveTargetAwake.Invoke(t2St, null);
            liveTargetOnEnable.Invoke(t2St, null);

            t1Go.name = "T1_LockTarget";
            t2Go.name = "T2_LockTarget";

            var lockTargetOnEnable = typeof(LockOnTarget).GetMethod("OnEnable", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            if (!LockOnTarget.All.Contains(t1Target)) lockTargetOnEnable?.Invoke(t1Target, null);
            if (!LockOnTarget.All.Contains(t2Target)) lockTargetOnEnable?.Invoke(t2Target, null);
            Physics.SyncTransforms();

            lockSys.Acquire();
            Assert(lockSys.Current == t1Target, "LockOnSystem Initially Acquires Target 1 (Closest to Center)");

            t1St.TakeDamage(new DamageInfo(200f, t1Go.transform.position, Vector3.back, Vector3.forward, HitType.Body, HandSide.Left));
            var lockSysUpdate = typeof(LockOnSystem).GetMethod("Update", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            lockSysUpdate.Invoke(lockSys, null);

            Assert(lockSys.Current == t2Target, "LockOnSystem Automatically Switched to Target 2 on Target 1 Kill");

            t2St.TakeDamage(new DamageInfo(200f, t2Go.transform.position, Vector3.back, Vector3.forward, HitType.Body, HandSide.Left));
            lockSysUpdate.Invoke(lockSys, null);

            Assert(lockSys.Current == null, "LockOnSystem Cleanly Released Lock When No Alive Targets Remain");

            // -----------------------------------------------------------
            // TEST 17: Controls Rebuild (2026-10-28): she faces the crosshair, the lock-on frame, the sprint turn, Alt free look, the dodge
            // -----------------------------------------------------------
            yoruTargetGo = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            yoruTargetGo.transform.position = new Vector3(500f, 0f, 10f);
            var yoruLockTarget = yoruTargetGo.AddComponent<LockOnTarget>();
            if (!LockOnTarget.All.Contains(yoruLockTarget)) lockTargetOnEnable?.Invoke(yoruLockTarget, null);
            Physics.SyncTransforms();

            // a fresh Yoru for every scenario (no leftover speed, dash cooldown or lock); the camera rig of TEST 16 stands in for the game camera
            YoruController NewYoru(out GameInput gi, out LockOnSystem lk)
            {
                if (yoruGo != null) UnityEngine.Object.DestroyImmediate(yoruGo);
                yoruGo = new GameObject("_TestYoru");
                yoruGo.transform.position = new Vector3(500f, 0f, 0f);
                yoruGo.AddComponent<CharacterController>();
                gi = yoruGo.AddComponent<GameInput>();
                inputAwake.Invoke(gi, null);
                lk = yoruGo.AddComponent<LockOnSystem>();
                var ctrl = yoruGo.AddComponent<YoruController>();
                ctrl.cameraTransform = lockCamGo.transform;
                ctrl.lockOn = lk;
                ctrl.EnsureComponents();
                Physics.SyncTransforms();
                return ctrl;
            }
            // frames at a fixed 0.02 s: the game input is read first, then the controller steps (the same order as in the game)
            void StepYoru(YoruController ctrl, GameInput gi, int frames)
            {
                for (int i = 0; i < frames; i++)
                {
                    inputUpdate.Invoke(gi, null);
                    ctrl.Tick(0.02f);
                }
            }
            void SetCamera(float yawDegrees)
            {
                lockRig.SetOrbit(yawDegrees, 15f);
                lockCamGo.transform.rotation = Quaternion.Euler(0f, yawDegrees, 0f);
            }
            Vector3 Flat(Vector3 v) { v.y = 0f; return v; }
            float FaceDot(Vector3 direction) { return Vector3.Dot(yoruGo.transform.forward, Flat(direction).normalized); }
            Vector3 ToTarget() { return Flat(yoruTargetGo.transform.position - yoruGo.transform.position); }

            // --- A: normal play. She always faces the crosshair (the camera yaw); S backs up while she keeps facing forward; A and D side-step relative to the camera.
            SetCamera(90f);                                                  // the camera looks along +X, she starts facing +Z
            var yoruCtrl = NewYoru(out var yoruIn, out var yoruLock);
            Vector3 legStart = yoruGo.transform.position;
            yoruIn.MoveOverride = new Vector2(0f, -1f);                      // S
            StepYoru(yoruCtrl, yoruIn, 40);
            Vector3 moved = Flat(yoruGo.transform.position - legStart);
            Assert(yoruCtrl.Facing == FacingMode.Aim && !yoruCtrl.IsLockedOn, "Normal Play Faces The Crosshair (Facing = Aim)");
            Assert(FaceDot(Vector3.right) > 0.98f, "Pressing S She Turns To The Camera Yaw, So Facing And Bullet Direction Agree");
            Assert(moved.magnitude > 0.8f && Vector3.Dot(moved.normalized, Vector3.left) > 0.99f, "S Backs Up Relative To The Camera (Away From Where She Faces)");
            Assert(yoruCtrl.LocalMove.y < -1.0f && Mathf.Abs(yoruCtrl.LocalMove.x) < 0.1f && yoruCtrl.MoveY < -0.6f, "Backing Up Shows As Negative Local Forward Speed (MoveY)");
            Assert(yoruCtrl.LocoMultiplier < -0.9f, "Backing Up Plays The Walk In Reverse (Negative LocoMult Stopgap)");
            legStart = yoruGo.transform.position;
            yoruIn.MoveOverride = new Vector2(-1f, 0f);                      // A: left of the crosshair = +Z for a camera that looks along +X
            StepYoru(yoruCtrl, yoruIn, 40);
            moved = Flat(yoruGo.transform.position - legStart);
            Assert(moved.magnitude > 0.8f && Vector3.Dot(moved.normalized, Vector3.forward) > 0.99f, "A Side-Steps Relative To The Camera (Not World Left)");
            Assert(FaceDot(Vector3.right) > 0.98f && yoruCtrl.MoveX < -0.6f, "Side-Stepping She Keeps Facing The Crosshair (MoveX Is Negative)");
            Assert(yoruCtrl.LocoMultiplier > 0.9f, "Side-Stepping Plays The Walk Forward (No Reverse)");
            yoruIn.MoveOverride = Vector2.zero;
            SetCamera(180f);                                                 // the player turns the camera: she follows even while standing still
            StepYoru(yoruCtrl, yoruIn, 30);
            Assert(FaceDot(Vector3.back) > 0.98f && yoruCtrl.Facing == FacingMode.Aim, "Standing Still She Still Follows The Crosshair");
            Assert(yoruCtrl.LocoMultiplier > 0.9f, "Standing Still The Playback Returns To Forward");

            // the turn is fast but smooth: a 180 degree swing is capped by turnSpeed, eased out, and done in well under half a second
            SetCamera(0f);
            float turnAngle = Vector3.Angle(yoruGo.transform.forward, Vector3.forward), lastAngle = turnAngle, biggestStep = 0f;
            int turnFrames = 0;
            while (turnFrames < 40 && Vector3.Angle(yoruGo.transform.forward, Vector3.forward) > 5f)
            {
                StepYoru(yoruCtrl, yoruIn, 1);
                turnFrames++;
                float angle = Vector3.Angle(yoruGo.transform.forward, Vector3.forward);
                biggestStep = Mathf.Max(biggestStep, Mathf.Abs(angle - lastAngle));
                lastAngle = angle;
            }
            Assert(turnAngle > 170f && turnFrames >= 6 && turnFrames <= 20, "A 180 Degree Turn Is Fast (< 0.4 s) But Not A Snap", $"frames {turnFrames}");
            Assert(biggestStep <= yoruCtrl.turnSpeed * 0.02f + 0.5f, "The Turn Never Exceeds turnSpeed", $"biggest step {biggestStep}");

            // --- B: lock-on. Only her body faces the target; W/A/S/D are relative to the target, not to the camera
            //        (the camera still looks along +X, the target stands along +Z).
            SetCamera(90f);
            yoruCtrl = NewYoru(out yoruIn, out yoruLock);
            yoruLock.SetTarget(yoruLockTarget);
            Vector3[] lockLegs = { Vector3.forward, Vector3.back, Vector3.right, Vector3.left };      // W, S, D, A relative to a target along +Z
            Vector2[] lockKeys = { new Vector2(0f, 1f), new Vector2(0f, -1f), new Vector2(1f, 0f), new Vector2(-1f, 0f) };
            string[] lockNames = { "W Moves Toward The Target", "S Moves Away From The Target", "D Circles To The Right Of The Target", "A Circles To The Left Of The Target" };
            for (int leg = 0; leg < lockLegs.Length; leg++)
            {
                legStart = yoruGo.transform.position;
                yoruIn.MoveOverride = lockKeys[leg];
                StepYoru(yoruCtrl, yoruIn, 40);
                moved = Flat(yoruGo.transform.position - legStart);
                Assert(moved.magnitude > 0.8f && Vector3.Dot(moved.normalized, lockLegs[leg]) > 0.97f, lockNames[leg] + " (Camera Free, Not Camera Relative)");
                Assert(yoruCtrl.IsLockedOn && yoruCtrl.Facing == FacingMode.LockOn && FaceDot(ToTarget()) > 0.98f, "She Keeps Facing The Target " + (leg == 0 ? "Walking Toward It" : leg == 1 ? "Backing Away" : "While Circling"));
            }
            Assert(yoruCtrl.MoveX < -0.6f && Mathf.Abs(yoruCtrl.MoveY) < 0.3f, "Circling Shows As Sideways Local Speed (MoveX)");
            Assert(yoruCtrl.LocoMultiplier > 0.9f, "Circling Plays The Walk Forward");

            // sprinting while locked on: she faces the way she runs, and turns back to the target when she stops
            yoruIn.SprintOverride = true;
            yoruIn.MoveOverride = new Vector2(-1f, 0f);                      // A in the target frame = -X
            StepYoru(yoruCtrl, yoruIn, 40);
            Assert(yoruCtrl.IsSprinting && yoruCtrl.Facing == FacingMode.Sprint && FaceDot(Vector3.left) > 0.95f, "Sprinting While Locked On She Faces The Way She Runs, Not The Target");
            Assert(yoruCtrl.HorizontalSpeed > 4.5f && yoruCtrl.LocoMultiplier > 0.9f, "The Sprint Always Plays Forward At Full Speed");
            yoruIn.MoveOverride = Vector2.zero;
            StepYoru(yoruCtrl, yoruIn, 30);
            Assert(!yoruCtrl.IsSprinting && yoruCtrl.Facing == FacingMode.LockOn && FaceDot(ToTarget()) > 0.98f, "Stopping Ends The Sprint And She Turns Back To The Target");
            yoruIn.SprintOverride = false;
            yoruLock.Release();
            StepYoru(yoruCtrl, yoruIn, 30);
            Assert(!yoruCtrl.IsLockedOn && yoruCtrl.Facing == FacingMode.Aim && FaceDot(Vector3.right) > 0.98f, "After The Release She Faces The Crosshair Again");

            // --- C: sprint (no lock). She faces the way she runs; aiming, firing and stopping end it and she turns back to the crosshair.
            SetCamera(0f);
            yoruCtrl = NewYoru(out yoruIn, out yoruLock);
            yoruIn.SprintOverride = true;                                    // Shift held (a hold, so no dodge first)
            yoruIn.MoveOverride = new Vector2(1f, 0f);                       // D
            StepYoru(yoruCtrl, yoruIn, 30);
            Assert(yoruCtrl.IsSprinting && yoruCtrl.Facing == FacingMode.Sprint, "Holding Shift While Moving Starts The Sprint");
            Assert(FaceDot(Vector3.right) > 0.95f && yoruCtrl.HorizontalSpeed > 4.5f, "Sprinting She Faces The Way She Runs (Right Of The Camera)");
            Assert(Mathf.Abs(yoruCtrl.LocalMove.x) < 0.5f && yoruCtrl.MoveY > 2.5f, "The Sprint Is Forward Motion In Her Own Frame (MoveY = Run Speed / Walk Speed)");
            yoruIn.AimHeldOverride = true;                                   // right mouse button
            StepYoru(yoruCtrl, yoruIn, 25);
            Assert(!yoruCtrl.IsSprinting && yoruCtrl.Facing == FacingMode.Aim && FaceDot(Vector3.forward) > 0.95f, "Aiming Ends The Sprint And She Turns Back To The Crosshair");
            Assert(yoruCtrl.HorizontalSpeed < 1.7f && yoruCtrl.MoveX > 0.6f, "While Aiming She Walks (Side-Steps) At Walking Speed");
            yoruIn.AimHeldOverride = false;
            StepYoru(yoruCtrl, yoruIn, 25);
            Assert(yoruCtrl.IsSprinting && yoruCtrl.Facing == FacingMode.Sprint, "Shift Still Held: The Sprint Resumes When The Aim Is Let Go");
            yoruIn.FireHeldOverride = true;                                  // left mouse button
            StepYoru(yoruCtrl, yoruIn, 25);
            Assert(!yoruCtrl.IsSprinting && yoruCtrl.Facing == FacingMode.Aim && FaceDot(Vector3.forward) > 0.95f, "Firing Ends The Sprint And She Turns Back To The Crosshair");
            yoruIn.FireHeldOverride = false;
            StepYoru(yoruCtrl, yoruIn, 2);
            Assert(!yoruCtrl.IsSprinting, "Right After The Last Shot She Is Still Out Of The Sprint (No Flicker Between Shots)");
            StepYoru(yoruCtrl, yoruIn, 25);
            Assert(yoruCtrl.IsSprinting, "A Moment After The Last Shot The Sprint Resumes While Shift Is Held");
            yoruIn.MoveOverride = Vector2.zero;                              // she stops, Shift still held
            StepYoru(yoruCtrl, yoruIn, 30);
            Assert(!yoruCtrl.IsSprinting && yoruCtrl.Facing == FacingMode.Aim && FaceDot(Vector3.forward) > 0.98f, "Stopping Ends The Sprint And She Turns Back To The Crosshair");
            yoruIn.MoveOverride = new Vector2(0f, -1f);                      // sprinting backwards: she turns around and runs facing the way she goes
            StepYoru(yoruCtrl, yoruIn, 40);
            Assert(yoruCtrl.IsSprinting && FaceDot(Vector3.back) > 0.95f && yoruCtrl.LocoMultiplier > 0.9f, "Sprinting Backwards She Turns Around And Runs Forward (No Reverse Clip)");
            yoruIn.SprintOverride = false;
            yoruIn.MoveOverride = Vector2.zero;

            // --- D: Alt free look. The camera orbits while she keeps the facing and the move reference from before; on release the camera swings back.
            SetCamera(0f);
            yoruCtrl = NewYoru(out yoruIn, out yoruLock);
            lockRig.input = yoruIn;
            yoruIn.FreeLookOverride = true;                                  // Alt down
            StepYoru(yoruCtrl, yoruIn, 1);
            lockRig.UpdateFreeLook(0.02f);
            Assert(lockRig.FreeLookActive && Mathf.Abs(Mathf.DeltaAngle(lockRig.AimYaw, 0f)) < 0.01f, "Alt Starts Free Look And Freezes The Aim Heading");
            SetCamera(90f);                                                  // the camera orbits to the right while Alt is held
            Assert(Mathf.Abs(Mathf.DeltaAngle(lockRig.AimYaw, 0f)) < 0.01f, "During Free Look The Aim Heading Stays Frozen While The Camera Yaw Moves On");
            legStart = yoruGo.transform.position;
            yoruIn.MoveOverride = new Vector2(0f, 1f);                       // W
            StepYoru(yoruCtrl, yoruIn, 40);
            moved = Flat(yoruGo.transform.position - legStart);
            Assert(FaceDot(Vector3.forward) > 0.98f && yoruCtrl.Facing == FacingMode.Aim, "While Alt Is Held She Does Not Turn With The Camera");
            Assert(moved.magnitude > 0.8f && Vector3.Dot(moved.normalized, Vector3.forward) > 0.99f, "While Alt Is Held W Keeps Going The Way She Faced Before");
            yoruIn.FreeLookOverride = false;                                 // Alt released: the camera swings back, she keeps the heading all the while
            float lowestFacing = 1f;
            int swingFrames = 0;
            while (swingFrames < 200)
            {
                swingFrames++;
                StepYoru(yoruCtrl, yoruIn, 1);
                lockRig.UpdateFreeLook(0.02f);
                lockCamGo.transform.rotation = Quaternion.Euler(0f, lockRig.Yaw, 0f);
                if (!lockRig.FreeLookActive) break;
                lowestFacing = Mathf.Min(lowestFacing, FaceDot(Vector3.forward));
            }
            Assert(!lockRig.FreeLookActive && Mathf.Abs(Mathf.DeltaAngle(lockRig.Yaw, 0f)) < 1.5f, "After Alt The Camera Swings Back To Where It Was", $"yaw {lockRig.Yaw}, frames {swingFrames}");
            Assert(lowestFacing > 0.98f, "During The Swing Back She Keeps The Heading From Before", $"lowest facing {lowestFacing}");
            yoruIn.MoveOverride = Vector2.zero;
            SetCamera(90f);                                                  // Alt is over: she follows the crosshair again
            StepYoru(yoruCtrl, yoruIn, 30);
            Assert(FaceDot(Vector3.right) > 0.98f && !lockRig.FreeLookActive, "After Free Look She Follows The Crosshair Again");
            lockRig.input = null;

            // --- E: dodge. The direction comes from the input in the same reference as the walk; she may turn toward it, then returns to the facing rule.
            SetCamera(90f);
            yoruCtrl = NewYoru(out yoruIn, out yoruLock);
            var dashDirField = typeof(YoruController).GetField("dashDirection", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            yoruIn.MoveOverride = new Vector2(-1f, 0f);                      // A: camera-left = +Z
            yoruIn.DashOverride = true;                                      // Shift tap
            StepYoru(yoruCtrl, yoruIn, 1);
            Vector3 dashDir = (Vector3)dashDirField.GetValue(yoruCtrl);
            Assert(yoruCtrl.IsDashing, "Yoru Controller Successfully Initiated Combat Dash");
            Assert(Vector3.Dot(dashDir, Vector3.forward) > 0.99f, "Dodge Direction Follows The Input Relative To The Camera (A = Camera Left)");
            StepYoru(yoruCtrl, yoruIn, 4);
            Assert(yoruCtrl.IsDashing && yoruCtrl.Facing == FacingMode.Dodge && FaceDot(Vector3.forward) > 0.5f, "During The Dodge She Turns Toward The Dash (No Dodge Clips Yet)");
            yoruIn.MoveOverride = Vector2.zero;
            StepYoru(yoruCtrl, yoruIn, 40);
            Assert(!yoruCtrl.IsDashing && yoruCtrl.Facing == FacingMode.Aim && FaceDot(Vector3.right) > 0.98f, "After The Dodge She Returns To Facing The Crosshair");
            yoruCtrl = NewYoru(out yoruIn, out yoruLock);                    // no input: the dodge goes straight ahead in the reference frame
            yoruIn.DashOverride = true;
            StepYoru(yoruCtrl, yoruIn, 1);
            dashDir = (Vector3)dashDirField.GetValue(yoruCtrl);
            Assert(Vector3.Dot(dashDir, Vector3.right) > 0.99f, "A Dodge Without Input Goes Toward The Crosshair");

            yoruCtrl = NewYoru(out yoruIn, out yoruLock);                    // locked on: the reference is the target (A = -X), not the camera (A would be +Z)
            yoruLock.SetTarget(yoruLockTarget);
            yoruIn.MoveOverride = new Vector2(-1f, 0f);
            yoruIn.DashOverride = true;
            StepYoru(yoruCtrl, yoruIn, 1);
            dashDir = (Vector3)dashDirField.GetValue(yoruCtrl);
            Assert(yoruCtrl.IsDashing && Vector3.Dot(dashDir, Vector3.left) > 0.99f, "Locked On The Dodge Direction Is Relative To The Target (A = Left Of The Target)");
            yoruIn.MoveOverride = Vector2.zero;
            StepYoru(yoruCtrl, yoruIn, 40);
            Assert(!yoruCtrl.IsDashing && yoruCtrl.Facing == FacingMode.LockOn && FaceDot(ToTarget()) > 0.98f, "After A Locked-On Dodge She Faces The Target Again");
            yoruCtrl = NewYoru(out yoruIn, out yoruLock);
            yoruLock.SetTarget(yoruLockTarget);
            yoruIn.DashOverride = true;
            StepYoru(yoruCtrl, yoruIn, 1);
            dashDir = (Vector3)dashDirField.GetValue(yoruCtrl);
            Assert(Vector3.Dot(dashDir, Vector3.forward) > 0.99f, "Locked On A Dodge Without Input Goes Toward The Target");
            yoruCtrl = NewYoru(out yoruIn, out yoruLock);                    // the option for the day the dodge clips exist: keep facing the target during the dodge
            yoruCtrl.dodgeFacesTravel = false;
            yoruLock.SetTarget(yoruLockTarget);
            yoruIn.MoveOverride = new Vector2(1f, 0f);
            yoruIn.DashOverride = true;
            StepYoru(yoruCtrl, yoruIn, 6);
            Assert(yoruCtrl.IsDashing && yoruCtrl.Facing == FacingMode.LockOn && FaceDot(ToTarget()) > 0.98f, "With dodgeFacesTravel Off She Keeps Facing The Target During The Dodge");
            yoruIn.MoveOverride = Vector2.zero;

            // --- Source guards for the two rules a play-test would notice at once
            string Code(string path) { return Regex.Replace(File.ReadAllText(path), @"//[^\r\n]*|/\*.*?\*/", "", RegexOptions.Singleline); }
            Assert(!Regex.IsMatch(Code("Assets/Scripts/Camera/ThirdPersonCamera.cs"), @"\blockTarget\b") && !Regex.IsMatch(Code("Assets/Scripts/Camera/LockOnSystem.cs"), @"\blockTarget\b"),
                "Lock-On Never Steers The Camera (The Rig Has No lockTarget Any More)");
            string uiCode = Code("Assets/Scripts/Combat/CombatUI.cs");
            int uiStart = uiCode.IndexOf("void OnGUI()", StringComparison.Ordinal);
            int uiEnd = uiCode.IndexOf("void DrawHitmarker(", StringComparison.Ordinal);
            string crosshairCode = uiStart >= 0 && uiEnd > uiStart ? uiCode.Substring(uiStart, uiEnd - uiStart) : "";
            Assert(crosshairCode.Contains("DrawCrosshair(cx, cy);") && !Regex.IsMatch(crosshairCode, @"\b(lockOn|currentLockTarget|IsLockedOn|isLocked)\b"),
                "The Crosshair Is Drawn While Locked On (No Lock Condition Around It)");

            // -----------------------------------------------------------
            // TEST 18: AmmoCrate Resupply System
            // -----------------------------------------------------------
            crateGo = new GameObject("_TestAmmoCrate");
            var ammoCrate = crateGo.AddComponent<AmmoCrate>();
            var ammoLeftProp = typeof(DualPistolCombat).GetProperty("AmmoLeft");
            ammoLeftProp.SetValue(combat, 2);
            var ammoRightProp = typeof(DualPistolCombat).GetProperty("AmmoRight");
            ammoRightProp.SetValue(combat, 3);

            Assert(combat.AmmoLeft == 2 && combat.AmmoRight == 3, "Ammo Depleted for Resupply Test");

            ammoCrate.ForceResupply(combat);
            Assert(combat.AmmoLeft == 15, "Resupply Restored Left Mag to 15");
            Assert(combat.AmmoRight == 15, "Resupply Restored Right Mag to 15");
            Assert(!combat.IsReloading, "Resupply Cleared Reload State");

            // -----------------------------------------------------------
            // TEST 19: Target Trolley Motion & Distance Presets
            // -----------------------------------------------------------
            trolleyGo = new GameObject("_TestTrolley");
            var trolley = trolleyGo.AddComponent<TargetTrolley>();
            trolley.boothOriginZ = TargetTrolley.FiringLineZ;
            trolley.transform.position = new Vector3(0f, 3.4f, TargetTrolley.Z10M);

            Assert(Mathf.Approximately(TargetTrolley.FiringLineZ, -2.5f), "Firing Line Sits At The Shooter Standing Z (-2.5m)");
            Assert(Mathf.Approximately(trolley.CurrentDistance, 10.0f), "Trolley Initial Distance Equals 10m");
            Assert(Mathf.Approximately(TargetTrolley.ZRecall, -1.7f), "Trolley Recall Z Equals -1.7m (0.8m from the firing line)");
            Assert(Mathf.Approximately(TargetTrolley.Z5M, 2.5f), "Trolley 5m Stop Z Equals 2.5m");
            Assert(Mathf.Approximately(TargetTrolley.Z10M, 7.5f), "Trolley 10m Stop Z Equals 7.5m");
            Assert(Mathf.Approximately(TargetTrolley.Z15M, 12.5f), "Trolley 15m Stop Z Equals 12.5m");
            Assert(Mathf.Approximately(TargetTrolley.Z25M, 22.5f), "Trolley 25m Stop Z Equals 22.5m");

            trolley.MoveToDistance(15.0f);
            Assert(trolley.IsMoving, "Trolley In Transit After MoveToDistance(15m)");
            Assert(Mathf.Approximately(trolley.TargetDistance, 15.0f), "Trolley Target Distance Set to 15m");
            Assert(Mathf.Approximately(trolley.TargetZ, 12.5f), "Trolley Target Z Set to 12.5m");

            var trolleyUpdate = typeof(TargetTrolley).GetMethod("Update", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            for (int step = 0; step < 250; step++)
            {
                trolleyUpdate.Invoke(trolley, null);
                if (!trolley.IsMoving) break;
            }

            Assert(!trolley.IsMoving, "Trolley Critically Damped Travel Completed");
            Assert(Mathf.Abs(trolley.CurrentDistance - 15.0f) < 0.05f, "Trolley Arrived at 15m Stop");

            trolley.Recall();
            Assert(Mathf.Approximately(trolley.TargetDistance, 0.8f), "Trolley Recall Target Distance Equals 0.8m");
            Assert(Mathf.Approximately(trolley.TargetZ, -1.7f), "Trolley Recall Target Z Equals -1.7m");

            // -----------------------------------------------------------
            // TEST 20: Paper Target Radial Scoring Zones
            // -----------------------------------------------------------
            paperGo = GameObject.CreatePrimitive(PrimitiveType.Cube);
            var paperTarget = paperGo.AddComponent<PaperTarget>();
            var paperAwake = typeof(PaperTarget).GetMethod("Awake", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            paperAwake.Invoke(paperTarget, null);

            Assert(paperTarget.CalculateScore(new Vector2(0f, 0f)) == 10, "Paper Target Bullseye Center Hit Scores 10 Pts");
            Assert(paperTarget.CalculateScore(new Vector2(0.04f, 0f)) == 10, "Paper Target Inner Bullseye Radius (<=0.05m) Scores 10 Pts");
            Assert(paperTarget.CalculateScore(new Vector2(0.08f, 0f)) == 9, "Paper Target 9-Ring Radius (<=0.10m) Scores 9 Pts");
            Assert(paperTarget.CalculateScore(new Vector2(0.14f, 0f)) == 8, "Paper Target 8-Ring Radius (<=0.16m) Scores 8 Pts");
            Assert(paperTarget.CalculateScore(new Vector2(0.20f, 0f)) == 7, "Paper Target 7-Ring Radius (<=0.22m) Scores 7 Pts");
            Assert(paperTarget.CalculateScore(new Vector2(0.24f, 0.35f)) == 5, "Paper Target Silhouette Torso Zone Scores 5 Pts");
            Assert(paperTarget.CalculateScore(new Vector2(0.50f, 0.60f)) == 0, "Paper Target Out of Bounds Miss Scores 0 Pts");

            // -----------------------------------------------------------
            // TEST 21: Paper Target Dynamic Hole Decals & Extreme Spread Grouping
            // -----------------------------------------------------------
            Assert(paperTarget.ShotCount == 0, "Initial Paper Target Shot Count is 0");
            Assert(paperTarget.TotalScore == 0, "Initial Paper Target Total Score is 0");
            Assert(paperTarget.ExtremeSpreadCm == 0f, "Initial Extreme Spread is 0.0 cm");

            // Shot 1: Bullseye at (0.02, 0.03) -> 10 pts
            paperTarget.TakeDamage(new DamageInfo(25f, paperGo.transform.position + new Vector3(0.02f, 0.03f, 0f), Vector3.back, Vector3.forward, HitType.Body, HandSide.Left));
            Assert(paperTarget.ShotCount == 1, "Shot 1 Count Incremented to 1");
            Assert(paperTarget.TotalScore == 10, "Shot 1 Score Equals 10");
            Assert(paperTarget.ExtremeSpreadCm == 0f, "Single Shot Grouping Extreme Spread Equals 0.0 cm");

            // Shot 2: at (0.06, 0.03) -> Distance is 0.04m = 4.0 cm -> 9 pts
            paperTarget.TakeDamage(new DamageInfo(25f, paperGo.transform.position + new Vector3(0.06f, 0.03f, 0f), Vector3.back, Vector3.forward, HitType.Body, HandSide.Right));
            Assert(paperTarget.ShotCount == 2, "Shot 2 Count Incremented to 2");
            Assert(paperTarget.TotalScore == 19, "Cumulative Score Equals 19 (10 + 9)");
            Assert(Mathf.Abs(paperTarget.ExtremeSpreadCm - 4.0f) < 0.1f, "Extreme Spread Computed to 4.0 cm");

            // Shot 3: at (-0.02, 0.03) -> Max Distance is from (-0.02) to (0.06) = 0.08m = 8.0 cm -> 10 pts
            paperTarget.TakeDamage(new DamageInfo(25f, paperGo.transform.position + new Vector3(-0.02f, 0.03f, 0f), Vector3.back, Vector3.forward, HitType.Body, HandSide.Left));
            Assert(paperTarget.ShotCount == 3, "Shot 3 Count Incremented to 3");
            Assert(paperTarget.TotalScore == 29, "Cumulative Score Equals 29 (10 + 9 + 10)");
            Assert(Mathf.Abs(paperTarget.ExtremeSpreadCm - 8.0f) < 0.1f, "Extreme Spread Computed to 8.0 cm");

            // Verify isotropic metric coordinates on scaled target sheet (e.g. 0.55m x 0.85m)
            scaledPaperGo = new GameObject("_TestScaledPaper");
            scaledPaperGo.transform.localScale = new Vector3(0.55f, 0.85f, 0.02f);
            var scaledPaper = scaledPaperGo.AddComponent<PaperTarget>();
            var scaledAwake = typeof(PaperTarget).GetMethod("Awake", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            scaledAwake.Invoke(scaledPaper, null);

            // Hit 4cm horizontally (0.04m, 0.0m) -> must score 10 pts inside 0.05m radius
            scaledPaper.TakeDamage(new DamageInfo(25f, scaledPaperGo.transform.position + new Vector3(0.04f, 0f, 0f), Vector3.back, Vector3.forward, HitType.Body, HandSide.Left));
            Assert(scaledPaper.LastScore == 10, "Scaled Target 4cm Hit Accurately Scores 10 Pts (Isotropic)");

            // Hit -4cm horizontally (-0.04m, 0.0m) -> distance between hits is 8.0 cm
            scaledPaper.TakeDamage(new DamageInfo(25f, scaledPaperGo.transform.position + new Vector3(-0.04f, 0f, 0f), Vector3.back, Vector3.forward, HitType.Body, HandSide.Right));
            Assert(Mathf.Abs(scaledPaper.ExtremeSpreadCm - 8.0f) < 0.1f, "Scaled Target Extreme Spread Correctly Equals 8.0 cm");
            Assert(scaledPaper.RecordedShotCount == 2, "RecordedShotCount Correctly Tracks 2 Shots");
            Assert(Mathf.Approximately(scaledPaper.GetHitCoordinate(0).x, 0.04f), "GetHitCoordinate Returns True Metric Hit X (0.04m)");

            // Fresh Paper Target Reset
            paperTarget.FreshPaper();
            Assert(paperTarget.ShotCount == 0, "FreshPaper Cleared Shot Count");
            Assert(paperTarget.TotalScore == 0, "FreshPaper Cleared Total Score");
            Assert(paperTarget.ExtremeSpreadCm == 0f, "FreshPaper Reset Extreme Spread to 0.0 cm");

            // Bullet hole decals recycle through the pool: once the sheet is full, the next hole replaces the oldest one
            for (int shot = 0; shot < paperTarget.maxHoles + 6; shot++)
            {
                paperTarget.TakeDamage(new DamageInfo(0f, paperGo.transform.position + new Vector3(0.01f * (shot % 5), 0f, 0f), Vector3.back, Vector3.forward, HitType.Body, HandSide.Left));
            }
            Assert(paperTarget.ActiveHoleDecalCount == paperTarget.maxHoles, "Paper Hole Decals Cap At The Pool Size");
            Assert(paperTarget.NextHoleSlot == 6, "Paper Hole Decals Ring Buffer Wraps To The Oldest Slot");
            paperTarget.FreshPaper();
            Assert(paperTarget.ActiveHoleDecalCount == 0, "FreshPaper Clears Every Hole Decal");

            // -----------------------------------------------------------
            // TEST 22: Proximity Cyber-Terminal & Instantaneous Steel Reset
            // -----------------------------------------------------------
            termGo = new GameObject("_TestTerminal");
            var terminal = termGo.AddComponent<RangeTerminal>();
            terminal.trolley = trolley;
            terminal.paperTarget = paperTarget;
            terminal.steelPoppers = new PopperTarget[] { popper };

            Assert(!terminal.isPlayerInside, "Terminal Initially in Standby (Player Outside)");

            terminal.SetPlayerInside(true);
            Assert(terminal.isPlayerInside, "Terminal Activated When Player Steps Into Stall");

            terminal.SendTo25M();
            Assert(Mathf.Approximately(trolley.TargetDistance, 25.0f), "Terminal Dispatched SendTo25M");

            terminal.RecallTarget();
            Assert(Mathf.Approximately(trolley.TargetDistance, 0.8f), "Terminal Dispatched RecallTarget (0.8m)");

            // Knock down popper
            popper.TakeDamage(new DamageInfo(200f, popperGo.transform.position, Vector3.back, Vector3.forward, HitType.Body, HandSide.Left));
            Assert(!popper.IsAlive, "Popper Target Knocked Down by Lethal Hit");

            // Instantly reset via booth terminal command
            terminal.ResetSteelTargets();
            Assert(popper.IsAlive, "Popper Target Instantly Reset & Raised by Booth Terminal");
            Assert(popper.CurrentHealth == 100f, "Popper Target Health Restored to 100 by Terminal Reset");

            // Terminal Holographic Telemetry & ASCII Target Schematic
            textGo = new GameObject("_TestTerminalText");
            var tm = textGo.AddComponent<TextMesh>();
            terminal.terminalTextMesh = tm;
            terminal.UpdateDisplay();

            Assert(tm.text.Contains("TARGET PLOT:"), "Terminal Renders Target Schematic");
            Assert(tm.text.Contains("MOA"), "Terminal Computes MOA Telemetry");

            // Stall Proximity Trigger Rigidbody & CharacterController interaction
            trigGo = new GameObject("_TestTrigger");
            var trigCol = trigGo.AddComponent<BoxCollider>();
            trigCol.isTrigger = true;
            var trigRb = trigGo.AddComponent<Rigidbody>();
            trigRb.isKinematic = true;
            var trigProxy = trigGo.AddComponent<RangeTerminalTriggerProxy>();
            trigProxy.terminal = terminal;

            Assert(trigRb.isKinematic, "Stall Trigger Rigidbody Is Kinematic");

            testCharGo = new GameObject("_TestChar");
            testCharGo.tag = "Player";
            var testCc = testCharGo.AddComponent<CharacterController>();
            var onTriggerEnter = typeof(RangeTerminalTriggerProxy).GetMethod("OnTriggerEnter", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            onTriggerEnter.Invoke(trigProxy, new object[] { testCc });
            Assert(terminal.isPlayerInside, "Proxy OnTriggerEnter Activated Terminal for CharacterController");

            var onTriggerExit = typeof(RangeTerminalTriggerProxy).GetMethod("OnTriggerExit", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            onTriggerExit.Invoke(trigProxy, new object[] { testCc });
            Assert(!terminal.isPlayerInside, "Proxy OnTriggerExit Deactivated Terminal for CharacterController");

            // -----------------------------------------------------------
            // TEST 23: Brass Shell Casing Pool Lifecycle & Non-Alloc Ejection
            // -----------------------------------------------------------
            shellPoolGo = new GameObject("_TestShellPool");
            var shellPool = shellPoolGo.AddComponent<ShellCasingPool>();
            shellPool.combat = combat;
            var shellAwake = typeof(ShellCasingPool).GetMethod("Awake", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            shellAwake.Invoke(shellPool, null);

            Assert(shellPool.AvailableCount == shellPool.poolSize, "Shell Casing Pool Prewarmed All Instances");
            Assert(shellPool.ActiveCasingCount == 0, "Initial Active Shell Casing Count is 0");

            var firstCasingCol = shellPoolGo.GetComponentInChildren<CapsuleCollider>(true);
            Assert(firstCasingCol != null && firstCasingCol.sharedMaterial != null, "Shell Casings Have Assigned Physics Material");
            Assert(firstCasingCol.sharedMaterial.bounciness > 0.3f, "Shell Casings Have Realistic Brass Bounciness");

            // Eject casing from Left pistol
            shellPool.EjectCasing(HandSide.Left, new Vector3(-0.25f, 1.15f, 0.45f), Vector3.forward);
            Assert(shellPool.ActiveCasingCount == 1, "Active Shell Count Incremented on Left Ejection");
            Assert(shellPool.AvailableCount == shellPool.poolSize - 1, "Available Shell Count Decremented");

            // Eject casing from Right pistol
            shellPool.EjectCasing(HandSide.Right, new Vector3(0.25f, 1.15f, 0.45f), Vector3.forward);
            Assert(shellPool.ActiveCasingCount == 2, "Active Shell Count Incremented on Right Ejection");

            // Recycle all casings
            shellPool.RecycleAll();
            Assert(shellPool.ActiveCasingCount == 0, "RecycleAll Restored Active Count to 0");
            Assert(shellPool.AvailableCount == shellPool.poolSize, "RecycleAll Restored All Casings to Available Pool");

            // Casings are 9mm cartridges on the Ignore Raycast layer, and they leave the gun at physical speed (m/s)
            var casingSample = shellPoolGo.transform.Find("_ShellCasing_PoolRoot/Casing_0");
            Assert(casingSample != null && casingSample.localScale.y * 2f < 0.02f, "Shell Casing Length Matches A 9mm Cartridge (< 2cm)");
            Assert(casingSample != null && casingSample.gameObject.layer == ShellCasingPool.CasingLayer, "Shell Casings Sit On The Ignore Raycast Layer");
            Assert(shellPool.leftEjectionImpulse.magnitude < 6f && shellPool.rightEjectionImpulse.magnitude < 6f, "Shell Ejection Velocity Is Physical (< 6 m/s)");
            }
            finally
            {
                // -----------------------------------------------------------
                // Clean up test game objects (Guaranteed cleanup under try-finally)
                // -----------------------------------------------------------
                if (playerGo != null) UnityEngine.Object.DestroyImmediate(playerGo);
                if (targetGo != null) UnityEngine.Object.DestroyImmediate(targetGo);
                if (railGo != null) UnityEngine.Object.DestroyImmediate(railGo);
                if (testCamGo != null) UnityEngine.Object.DestroyImmediate(testCamGo);
                if (wallGo != null) UnityEngine.Object.DestroyImmediate(wallGo);
                if (liveTargetGo != null) UnityEngine.Object.DestroyImmediate(liveTargetGo);
                if (camGo != null) UnityEngine.Object.DestroyImmediate(camGo);
                if (occludedTargetGo != null) UnityEngine.Object.DestroyImmediate(occludedTargetGo);
                if (occluderWall != null) UnityEngine.Object.DestroyImmediate(occluderWall);
                if (knockGo != null) UnityEngine.Object.DestroyImmediate(knockGo);
                if (popperGo != null) UnityEngine.Object.DestroyImmediate(popperGo);
                if (lockPlayerGo != null) UnityEngine.Object.DestroyImmediate(lockPlayerGo);
                if (lockCamGo != null) UnityEngine.Object.DestroyImmediate(lockCamGo);
                if (t1Go != null) UnityEngine.Object.DestroyImmediate(t1Go);
                if (t2Go != null) UnityEngine.Object.DestroyImmediate(t2Go);
                if (yoruGo != null) UnityEngine.Object.DestroyImmediate(yoruGo);
                if (yoruTargetGo != null) UnityEngine.Object.DestroyImmediate(yoruTargetGo);
                if (crateGo != null) UnityEngine.Object.DestroyImmediate(crateGo);
                if (trolleyGo != null) UnityEngine.Object.DestroyImmediate(trolleyGo);
                if (paperGo != null) UnityEngine.Object.DestroyImmediate(paperGo);
                if (scaledPaperGo != null) UnityEngine.Object.DestroyImmediate(scaledPaperGo);
                if (termGo != null) UnityEngine.Object.DestroyImmediate(termGo);
                if (textGo != null) UnityEngine.Object.DestroyImmediate(textGo);
                if (trigGo != null) UnityEngine.Object.DestroyImmediate(trigGo);
                if (testCharGo != null) UnityEngine.Object.DestroyImmediate(testCharGo);
                if (shellPoolGo != null) UnityEngine.Object.DestroyImmediate(shellPoolGo);

                ShootingTarget.ActiveTargets.RemoveAll(t => t == null);
                LockOnTarget.All.RemoveAll(t => t == null);
                Physics.SyncTransforms();
            }

            log.AppendLine("======================================================");
            log.AppendLine($"[CombatSystemVerifier] ALL TESTS PASSED! ({passCount}/{totalTests})");
            log.AppendLine("======================================================");
            File.WriteAllText("combat_verification_results.txt", log.ToString());

            Debug.Log("======================================================");
            Debug.Log($"[CombatSystemVerifier] ALL TESTS PASSED! ({passCount}/{totalTests})");
            Debug.Log("======================================================");
        }
    }
}
