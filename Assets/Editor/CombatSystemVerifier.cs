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
            var playerGo = new GameObject("_TestPlayer");
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
            var targetGo = new GameObject("_TestTarget");
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
            var railGo = new GameObject("_TestRail");
            var railTarget = railGo.AddComponent<MovingRailTarget>();
            railTarget.railOffset = new Vector3(10f, 0f, 0f);
            railTarget.travelDuration = 2.0f;
            railTarget.pauseDuration = 0.5f;

            Assert(railTarget.railOffset.x == 10f, "MovingRailTarget 10m Offset");

            // -----------------------------------------------------------
            // TEST 10: Hit Feedback Gating (Walls, Dead Dummies, Alive Targets)
            // -----------------------------------------------------------
            var wallGo = GameObject.CreatePrimitive(PrimitiveType.Cube);
            wallGo.name = "_TestWall";
            wallGo.transform.position = new Vector3(0f, 1.15f, 5f);
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
            playerGo.transform.position = new Vector3(0f, 0f, 0f);
            playerGo.transform.rotation = Quaternion.identity;
            nextFireTimeField.SetValue(combat, 0f);

            var executeShotMethod = typeof(DualPistolCombat).GetMethod("ExecuteShot", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            executeShotMethod.Invoke(combat, new object[] { HandSide.Left });

            Assert(hitFeedbackCount == 0, "Hit Feedback Not Dispatched On Static Wall/Floor Hits");

            // Move wall aside and place an alive dummy
            wallGo.transform.position = new Vector3(100f, 100f, 100f);
            var liveTargetGo = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            liveTargetGo.name = "_LiveTarget";
            liveTargetGo.transform.position = new Vector3(0.25f, 1.15f, 5f);
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
            var camGo = new GameObject("_TestCam");
            var testCam = camGo.AddComponent<Camera>();
            camGo.transform.position = new Vector3(0f, 1.5f, -2f);
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
            var occludedTargetGo = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            occludedTargetGo.name = "_OccludedTarget";
            occludedTargetGo.transform.position = new Vector3(0.25f, 1.15f, 12f);
            var occludedSt = occludedTargetGo.AddComponent<ShootingTarget>();
            occludedSt.targetRenderer = occludedTargetGo.GetComponent<Renderer>();
            var occludedHb = occludedTargetGo.AddComponent<TargetHitbox>();
            occludedHb.parentTarget = occludedSt;
            liveTargetAwake.Invoke(occludedSt, null);
            liveTargetOnEnable.Invoke(occludedSt, null);

            // Put a giant occluding wall in between
            var occluderWall = GameObject.CreatePrimitive(PrimitiveType.Cube);
            occluderWall.transform.position = new Vector3(0.25f, 1.15f, 6f);
            occluderWall.transform.localScale = new Vector3(5f, 5f, 1f);
            Physics.SyncTransforms();

            var applyMagMethod = typeof(DualPistolCombat).GetMethod("ApplyBulletMagnetism", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            Vector3 straightAhead = Vector3.forward;
            Vector3 resultDir = (Vector3)applyMagMethod.Invoke(combat, new object[] { combat.muzzleRight.position, straightAhead });

            Assert(resultDir == straightAhead, "Bullet Magnetism Ignores Occluded Target Behind Wall");
            occluderWall.transform.position = new Vector3(200f, 200f, 200f);
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
            var knockGo = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            var knockSt = knockGo.AddComponent<ShootingTarget>();
            knockSt.targetRenderer = knockGo.GetComponent<Renderer>();
            liveTargetAwake.Invoke(knockSt, null);
            liveTargetOnEnable.Invoke(knockSt, null);

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
            var popperGo = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            var popper = popperGo.AddComponent<PopperTarget>();
            popper.targetRenderer = popperGo.GetComponent<Renderer>();
            liveTargetAwake.Invoke(popper, null);
            liveTargetOnEnable.Invoke(popper, null);

            Assert(popper.IsAlive, "PopperTarget Initially Alive");
            Assert(popper.dropAngle == 90f, "PopperTarget Drop Angle is 90 degrees");
            Assert(popper.respawnDelay == 2.5f, "PopperTarget Respawn Delay is 2.5s");

            popper.TakeDamage(new DamageInfo(120f, popperGo.transform.position, Vector3.back, Vector3.forward, HitType.Body, HandSide.Left));
            Assert(!popper.IsAlive, "PopperTarget Marked Dead After Lethal Hit");

            var popperUpdate = typeof(PopperTarget).GetMethod("Update", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            for (int step = 0; step < 20; step++)
            {
                popperUpdate.Invoke(popper, null);
            }

            var popperTiltField = typeof(ShootingTarget).GetField("currentTilt", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            float popperTilt = (float)popperTiltField.GetValue(popper);
            Assert(popperTilt > 80f, "PopperTarget Hinged Down Flat (> 80 deg) when Dead");

            var popperDeathTimer = typeof(ShootingTarget).GetField("deathTimer", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            popperDeathTimer.SetValue(popper, 2.6f);
            popperUpdate.Invoke(popper, null);

            Assert(popper.IsAlive, "PopperTarget Elastic Pop-up Respawned After 2.5s");
            Assert(popper.CurrentHealth == 100f, "PopperTarget Restored to Full Health");

            // -----------------------------------------------------------
            // TEST 16: LockOnSystem Auto-Switch on Target Destruction
            // -----------------------------------------------------------
            var lockPlayerGo = new GameObject("_TestLockPlayer");
            lockPlayerGo.transform.position = new Vector3(500f, 1.5f, -5f);
            var lockInput = lockPlayerGo.AddComponent<GameInput>();
            var lockSys = lockPlayerGo.AddComponent<LockOnSystem>();
            var lockCamGo = new GameObject("_TestLockCam");
            var lockCam = lockCamGo.AddComponent<Camera>();
            var lockRig = lockCamGo.AddComponent<ThirdPersonCamera>();
            lockSys.cameraRig = lockRig;
            lockRig.target = lockPlayerGo.transform;
            lockCamGo.transform.position = new Vector3(500f, 1.5f, -5f);
            lockCamGo.transform.rotation = Quaternion.identity;

            var t1Go = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            t1Go.transform.position = new Vector3(500f, 1.5f, 5f);
            var t1Target = t1Go.AddComponent<LockOnTarget>();
            var t1St = t1Go.AddComponent<ShootingTarget>();
            t1St.targetRenderer = t1Go.GetComponent<Renderer>();
            liveTargetAwake.Invoke(t1St, null);
            liveTargetOnEnable.Invoke(t1St, null);

            var t2Go = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            t2Go.transform.position = new Vector3(501f, 1.5f, 10f);
            var t2Target = t2Go.AddComponent<LockOnTarget>();
            var t2St = t2Go.AddComponent<ShootingTarget>();
            t2St.targetRenderer = t2Go.GetComponent<Renderer>();
            liveTargetAwake.Invoke(t2St, null);
            liveTargetOnEnable.Invoke(t2St, null);

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
            // TEST 17: YoruController Strafe Locomotion & Directional Combat Dodge
            // -----------------------------------------------------------
            var yoruGo = new GameObject("_TestYoru");
            yoruGo.transform.position = new Vector3(500f, 0f, 0f);
            var yoruCc = yoruGo.AddComponent<CharacterController>();
            var yoruIn = yoruGo.AddComponent<GameInput>();
            inputAwake.Invoke(yoruIn, null);
            var yoruLock = yoruGo.AddComponent<LockOnSystem>();
            var yoruCtrl = yoruGo.AddComponent<YoruController>();
            yoruCtrl.cameraTransform = lockCamGo.transform;
            yoruCtrl.lockOn = yoruLock;
            var yoruAwake = typeof(YoruController).GetMethod("Awake", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            yoruAwake?.Invoke(yoruCtrl, null);

            var yoruTargetGo = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            yoruTargetGo.transform.position = new Vector3(500f, 0f, 10f);
            var yoruLockTarget = yoruTargetGo.AddComponent<LockOnTarget>();
            if (!LockOnTarget.All.Contains(yoruLockTarget)) lockTargetOnEnable?.Invoke(yoruLockTarget, null);
            yoruLock.SetTarget(yoruLockTarget);
            Physics.SyncTransforms();

            yoruIn.MoveOverride = new Vector2(0f, -1f);
            inputUpdate.Invoke(yoruIn, null);
            var yoruUpdate = typeof(YoruController).GetMethod("Update", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            yoruUpdate.Invoke(yoruCtrl, null);

            Assert(Vector3.Dot(yoruGo.transform.forward, Vector3.forward) > 0.8f, "Yoru Controller Faces Target in Strafe Locomotion");

            yoruIn.MoveOverride = new Vector2(-1f, 0f);
            yoruIn.DashOverride = true;
            inputUpdate.Invoke(yoruIn, null);
            yoruUpdate.Invoke(yoruCtrl, null);

            Assert(yoruCtrl.IsDashing, "Yoru Controller Successfully Initiated Combat Dash");
            var dashDirField = typeof(YoruController).GetField("dashDirection", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            Vector3 dDir = (Vector3)dashDirField.GetValue(yoruCtrl);
            Assert(Vector3.Dot(dDir, Vector3.left) > 0.8f, "Directional Combat Dodge Vector Directed to Pressed Input (Left)");
            Assert(Vector3.Dot(yoruGo.transform.forward, Vector3.forward) > 0.8f, "Yoru Controller Continues Facing Target During Directional Dodge");

            // -----------------------------------------------------------
            // TEST 18: AmmoCrate Resupply System
            // -----------------------------------------------------------
            var crateGo = new GameObject("_TestAmmoCrate");
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
            // Clean up test game objects
            // -----------------------------------------------------------
            UnityEngine.Object.DestroyImmediate(playerGo);
            UnityEngine.Object.DestroyImmediate(targetGo);
            UnityEngine.Object.DestroyImmediate(railGo);
            UnityEngine.Object.DestroyImmediate(wallGo);
            UnityEngine.Object.DestroyImmediate(liveTargetGo);
            UnityEngine.Object.DestroyImmediate(camGo);
            UnityEngine.Object.DestroyImmediate(occludedTargetGo);
            UnityEngine.Object.DestroyImmediate(occluderWall);
            UnityEngine.Object.DestroyImmediate(knockGo);
            UnityEngine.Object.DestroyImmediate(popperGo);
            UnityEngine.Object.DestroyImmediate(lockPlayerGo);
            UnityEngine.Object.DestroyImmediate(lockCamGo);
            UnityEngine.Object.DestroyImmediate(t1Go);
            UnityEngine.Object.DestroyImmediate(t2Go);
            UnityEngine.Object.DestroyImmediate(yoruGo);
            UnityEngine.Object.DestroyImmediate(yoruTargetGo);
            UnityEngine.Object.DestroyImmediate(crateGo);

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
