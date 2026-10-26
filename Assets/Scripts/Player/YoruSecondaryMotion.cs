using UnityEngine;
using VRM;

namespace ZeroProtocol.Player
{
    /// <summary>
    /// Everything on Yoru that swings and is not part of the humanoid clips: cat tail, cat ears, and a little
    /// "wind of movement" for hair / tail / coat. It matches the idle and the walk that were made in Blender
    /// (Blender/scripts/build_idle.py, build_walk.py): same resting curves of the tail, same kind of lazy S-sway while standing,
    /// a J-shaped tail with a travelling wave while walking, ears that flick one at a time.
    ///
    /// Tail: the VRoid tail is a straight rod without gravity. Here it gets
    ///   - a resting curve (bent a little per joint): the compact C while she stands, the J of the walk while she moves (blended in 0.35 s),
    ///   - a smaller size (root bone scale 0.72, the user found the tail hung out too far),
    ///   - a light gravity and less damping, so the VRM spring-bone physics moves it,
    ///   - a driver transform between hips and tail root that is animated: slow lazy sway while standing, while walking a sideways
    ///     swing against the pelvis yaw and a nod against the pelvis bounce (the spring chain adds the travelling wave),
    ///     lifted tail while running, raised in the air, straight back while dashing,
    ///   - now and then a flick of the tip (short sideways force) and a small kick when landing.
    /// Ears: the base joint of each ear twitches (fold back + out) now and then and sways a little; the VRM physics
    /// adds the lag of the upper joint.
    /// Spring-bone values for bust, hair and ears are the ones tuned in the Blender walk simulation (jelly bust, heavier hair, calm ears).
    ///
    /// Must run before the spring bones set themselves up (they read the rest pose in Awake), hence the early order.
    /// </summary>
    [DefaultExecutionOrder(-300)]
    public class YoruSecondaryMotion : MonoBehaviour
    {
        [Header("Tail rest shape (standing)")]
        [Tooltip("Bend per tail joint in degrees (+ = up, - = down). 8 joints from base to tip: leaves the back, arcs back and down in a compact C and rolls the tip in towards the body (special agent, not kawaii). Fitted in Blender against the body mesh (Blender/Yoru_Idle_tail.json), same values as the Blender idle.")]
        public float[] restPitch = { 8f, -13f, -23f, -30f, -32f, -35f, 0f, -40f };
        [Tooltip("Whole tail raised at the base, degrees above horizontal.")]
        public float baseLift = 0f;

        [Header("Standing tail of the Blender idle v2 (hangs calm down the middle, the tip rolls in)")]
        [Tooltip("On: the standing tail takes the exact shape of the Blender idle v2 (mean over its loop, with the sideways roll of the tip), 'restPitch' is not used for standing. Off: the old compact C.")]
        public bool useIdleV2TailShape = true;
        [Tooltip("Rotation of every tail joint (x, y, z, w; model axes, hips rotation removed) for the standing shape. From Blender/Yoru_Idle_v2_tailrest.json (Blender/scripts/export_tail_rest_v2.py); checked in Unity: joint positions within 1.2 mm of Blender.")]
        public Vector4[] idleV2TailRotation =
        {
            new Vector4(-0.04983f, -0.00000f, 0.00000f, 0.99876f),
            new Vector4(-0.22550f, -0.00000f, -0.00000f, 0.97424f),
            new Vector4(-0.50088f, -0.00000f, 0.00000f, 0.86552f),
            new Vector4(-0.66276f, -0.01338f, 0.00000f, 0.74871f),
            new Vector4(-0.71129f, -0.04261f, -0.00000f, 0.70161f),
            new Vector4(-0.61202f, -0.41824f, -0.00000f, 0.67120f),
            new Vector4(-0.61179f, -0.41807f, -0.00000f, 0.67152f),
            new Vector4(0.50689f, -0.58085f, -0.00000f, 0.63693f)
        };
        [Tooltip("Scale of the lazy sway of the tail base while she stands, with the idle v2 shape (the hanging tail has a longer lever than the old compact C).")]
        public float idleV2SwayScale = 0.45f;
        [Tooltip("Scale of the tip flick while she stands, with the idle v2 shape (the hanging tail flicks much further than the old C; Blender: a small flick of about 10 degrees).")]
        public float idleV2FlickScale = 0.4f;

        [Header("Tail while walking")]
        [Tooltip("Bend per tail joint while she moves (same convention as restPitch): down from the hips, then rising to the tip in a J. Blender/Yoru_Walk_tail.json walkRestPitch (the clearance lift of 16 degrees is in it).")]
        public float[] walkRestPitch = { -24.4f, 12f, -2f, 4f, 14f, 20f, 26f, 20f };
        [Tooltip("Uniform scale of the tail root bone: 0.72 = the tail reaches 0.47 m behind the hips instead of 0.66 m (Blender tail_scale).")]
        public float tailScale = 0.72f;
        [Tooltip("Seconds the tail needs to change between the standing curve and the walking curve.")]
        public float restBlendTime = 0.35f;
        [Tooltip("Sideways swing of the tail base against the pelvis yaw, degrees at full pelvis yaw (Blender tail_lat 6, 9 here makes the physical tail swing as far as the authored one).")]
        public float walkYaw = 9f;
        [Tooltip("Stiffness of the tail spring while she walks (the standing tail uses 'stiffness'). Tuned with TailTuneTest against the Blender walk at 1.5 m/s (171 steps/min): the tip swings about 150 mm sideways and 115 mm up and down in a 10 s window (Blender 147 / 107). The first, slower walk (138 steps/min) needed 1.5.")]
        public float walkStiffness = 2.2f;
        [Tooltip("Nod of the tail base against the pelvis bounce, degrees (Blender tail_vert).")]
        public float walkPitch = 3f;

        [Header("Tail while sprinting (Blender run: an aerodynamic arch with travelling waves)")]
        [Tooltip("Bend per tail joint in the sprint (same convention as restPitch): rises +30 degrees over the rump and levels out towards the tip. Blender/Yoru_Run_tail.json runRestPitch.")]
        public float[] runRestPitch = { 24f, -3f, -5f, -7f, -7f, -6f, 0f, 0f };
        [Tooltip("Sideways swing of the tail base against the pelvis yaw in the sprint, degrees at full pelvis yaw (like walkYaw). Tuned with TailTuneTest (sprint mode) against the Blender sprint: yaw 18 / stiffness 3.5 / drag 0.65 gives a tip swing of 181 mm sideways and 179 mm up and down (Blender 176 / 110; the height does not come lower in any setting of the sweep).")]
        public float sprintYaw = 18f;
        [Tooltip("Stiffness of the tail spring in the sprint.")]
        public float sprintStiffness = 3.5f;
        [Tooltip("Nod of the tail base against the pelvis bounce in the sprint, degrees.")]
        public float sprintPitch = 2f;
        [Tooltip("Damping of the tail spring in the sprint (the standing and walking tail use 'drag').")]
        [Range(0f, 1f)] public float sprintDrag = 0.65f;

        [Header("Tail physics")]
        public float gravity = 0.035f;
        [Range(0f, 1f)] public float drag = 0.45f;
        public float stiffness = 0.95f;

        [Header("Idle sway (period 6 s like the idle loop)")]
        public float swayYaw = 30f;
        public float swayPeriod = 6f;
        public float swayPitch = 4f;

        [Header("Movement")]
        public float runYaw = 0f;
        public float runLift = 0f;
        public float airLiftRising = 12f;
        public float airLiftFalling = 20f;
        public float dashPitch = 18f;
        public float smoothTime = 0.14f;

        [Header("Wind of movement (hair, tail, coat stream back a little when she moves)")]
        public float windTail = 0.02f;
        public float windHair = 0.008f;
        public float windOther = 0.008f;
        [Tooltip("Falling pulls hair up, so vertical speed counts a bit less than horizontal.")]
        public float verticalWindFactor = 0.5f;

        [Header("Tail flick")]
        public Vector2 flickInterval = new Vector2(5f, 9f);
        public float flickForce = 0.4f;
        public float flickDuration = 0.3f;
        public float landKick = 1.2f;

        [Header("Idle breeze (the hair moves a little in the wind while she stands; Blender idle v2: steady lean of about 6 degrees at the tips, two gusts per 12 s)")]
        [Tooltip("Steady push on the hair spring bones while standing (same unit as windHair * speed). Measured in Play Mode against no wind: 0.02 = 4 degrees, 0.03 = about 6 degrees (the Blender idle), 0.04 = 8 degrees, 0.08 = 17 degrees at the tips of the long strands.")]
        public float idleWindHair = 0.027f;
        [Tooltip("Direction the wind pushes, in the model's axes: a breeze from front right blowing to back left.")]
        public Vector3 idleWindDirection = new Vector3(-0.6f, 0f, -0.8f);
        [Tooltip("Extra push at the peak of a gust, as a share of the steady wind (1 = twice as strong).")]
        public float idleGustStrength = 2f;
        public float idleGustPeriod = 12f;
        public Vector2 idleGustTimes = new Vector2(3.9f, 9.3f);
        public float idleGustWidth = 0.55f;

        [Header("Ears")]
        [Tooltip("Resting angle of both ears, tilted back from the model's neutral (degrees). Expression B of the Blender idle v2: about 9 degrees (measured in the finished idle).")]
        public float earBaseBack = 9f;
        public Vector2 earFlickInterval = new Vector2(4f, 9f);
        public float earFoldBack = 10f;
        public float earOut = 3.5f;
        public float earSway = 1.5f;

        [Header("Spring bones (tuned in the Blender walk: Blender/Yoru_Walk_gait.json spring_params)")]
        [Tooltip("UniVRM's spring bones are not frame-rate independent (the damping is applied once per update), and everything here was tuned at 60 updates per second. So they are stepped at a fixed rate, whatever the frame rate of the game is.")]
        public float springStepsPerSecond = 60f;
        public bool tuneSprings = true;
        [Tooltip("Jelly bust: softer than the VRoid default (0.74).")]
        public float bustStiffness = 0.40f;
        public float bustDrag = 0.05f;
        [Tooltip("Hair: the stiffness of every strand times this (VRoid 0.4 .. 1.0), and less damping than the VRoid 0.4.")]
        public float hairStiffnessFactor = 1.4f;
        public float hairDrag = 0.28f;
        [Tooltip("Cat ears: stiffer and more damped than the VRoid default (1.5 / 0.05), they should not wobble with every step.")]
        public float earStiffness = 2.2f;
        public float earDrag = 0.30f;

        [Header("Spring bones in the sprint (Blender/Yoru_Run_gait.json spring_params; blended in with the sprint)")]
        [Tooltip("The bust needs more stiffness at the sprint, 0.4 would swing it 94 degrees.")]
        public float bustStiffnessSprint = 0.80f;
        public float hairDragSprint = 0.40f;
        public float earStiffnessSprint = 1.6f;
        public float earDragSprint = 0.14f;
        [Tooltip("Headwind of the sprint (push in m/s at the sprint speed, backwards and a little up): hair 0.19, ears 0.30 in the Blender run.")]
        public float windHairSprint = 0.19f;
        public float windEarSprint = 0.30f;
        [Range(0f, 1f)] public float windLift = 0.25f;

        /// <summary>Length of the walk cycle in the Blender clip: 21 frames at 30 fps (the first, slower walk had 26).</summary>
        const float WalkCycleSeconds = 21f / 30f;
        /// <summary>Peak vertical speed of the pelvis in the walk (m/s), used to normalise the nod of the tail: 11.4 mm * 4 pi / 0.7 s.</summary>
        const float PelvisPeakSpeed = 0.205f;
        /// <summary>Peak vertical speed of the pelvis in the sprint (m/s): 11.4 mm per frame at 60 fps (Blender run).</summary>
        const float RunPelvisPeakSpeed = 0.68f;

        Transform hips, driver;
        VRMSpringBone tailSpring;
        readonly System.Collections.Generic.List<VRMSpringBone> hairSprings = new System.Collections.Generic.List<VRMSpringBone>();
        readonly System.Collections.Generic.List<VRMSpringBone> otherSprings = new System.Collections.Generic.List<VRMSpringBone>();
        readonly System.Collections.Generic.List<VRMSpringBone> bustSprings = new System.Collections.Generic.List<VRMSpringBone>();
        readonly System.Collections.Generic.List<VRMSpringBone> earSprings = new System.Collections.Generic.List<VRMSpringBone>();
        float sprintK;                      // 0 = walk values, 1 = sprint values of the springs (smoothed sprint blend)
        float runBlend, runBlendApplied;    // tail rest curve: 0 = walking J, 1 = sprint arch
        readonly System.Collections.Generic.List<VRMSpringBone> allSprings = new System.Collections.Generic.List<VRMSpringBone>();
        float springClock;
        YoruController controller;
        Vector3 wind, windVel;
        float yaw, pitch, yawVel, pitchVel;
        float nextFlick, flickTimer, flickSign = 1f, kickTimer;
        bool wasGrounded = true;
        float phase;
        float gaitPhase;
        float restBlend, restBlendApplied;
        Transform[] tailJoints;
        Quaternion[] tailBaseRotation;
        Quaternion[] idleV2Delta;           // standing tail shape of the Blender idle v2 as a local rotation per joint (null = old C)
        float lastHipsY;
        float bounceSpeed;

        /// <summary>0 = standing curve, 1 = walking curve (what the tail rest shape is right now).</summary>
        public float TailRestBlend { get { return restBlend; } }

        class Ear
        {
            public Transform bone;
            public Quaternion restLocal;
            public float sideSign;              // left ear tip goes to -X when it turns out
            public float nextFlick, flickStart = -10f, earPhase;
        }
        readonly Ear[] ears = new Ear[2];
        const float EarFlickLength = 0.28f;

        void Awake()
        {
            var anim = GetComponent<Animator>();
            controller = GetComponentInParent<YoruController>();
            hips = anim != null ? anim.GetBoneTransform(HumanBodyBones.Hips) : null;
            Transform tailRoot = FindDeep(hips, "J_Opt_C_CatTail1_01");

            foreach (var sb in GetComponentsInChildren<VRMSpringBone>(true))
            {
                if (sb.m_comment == "CatTail") tailSpring = sb;
                else if (sb.m_comment == "Hair") hairSprings.Add(sb);
                else if (sb.m_comment == "Bust") { bustSprings.Add(sb); otherSprings.Add(sb); }
                else if (sb.m_comment == "CatEar") earSprings.Add(sb);
                else otherSprings.Add(sb);
                if (tuneSprings) TuneSpring(sb);
                sb.m_updateType = VRMSpringBone.SpringBoneUpdateType.Manual;               // stepped from LateUpdate below at a fixed rate
                allSprings.Add(sb);
            }

            SetupEars();

            if (tailRoot == null || tailSpring == null) return;

            // resting curve (standing): remember the T-pose rotation of every joint, the walking curve is blended in later
            var joints = new System.Collections.Generic.List<Transform>();
            for (Transform t = tailRoot; t != null && joints.Count < restPitch.Length; t = t.childCount > 0 ? t.GetChild(0) : null) joints.Add(t);
            tailJoints = joints.ToArray();
            tailBaseRotation = new Quaternion[tailJoints.Length];
            for (int i = 0; i < tailJoints.Length; i++) tailBaseRotation[i] = tailJoints[i].localRotation;
            ComputeIdleV2TailShape();
            ApplyTailRest(0f, 0f, false);

            // driver between hips and tail root, so the base of the tail can be animated
            driver = new GameObject("CatTailDriver").transform;
            driver.SetParent(hips, false);
            driver.position = tailRoot.position;
            driver.rotation = hips.rotation;
            tailRoot.SetParent(driver, true);
            tailRoot.localScale = Vector3.one * tailScale;

            // the VRM only has collision spheres for torso, head and arms: add some for the thighs and give them to the tail,
            // so a swinging tail does not go through the legs
            // (the torso sphere of the VRM sits right at the tail base, so only the new thigh spheres are used here)
            var groups = new System.Collections.Generic.List<VRMSpringBoneColliderGroup>();
            foreach (var legBone in new[] { HumanBodyBones.LeftUpperLeg, HumanBodyBones.RightUpperLeg })
            {
                var leg = anim.GetBoneTransform(legBone);
                if (leg == null) continue;
                var g = leg.gameObject.AddComponent<VRMSpringBoneColliderGroup>();
                g.Colliders = new[]
                {
                    new VRMSpringBoneColliderGroup.SphereCollider { Offset = new Vector3(0f, -0.09f, -0.01f), Radius = 0.095f },
                    new VRMSpringBoneColliderGroup.SphereCollider { Offset = new Vector3(0f, -0.22f, -0.01f), Radius = 0.085f },
                    new VRMSpringBoneColliderGroup.SphereCollider { Offset = new Vector3(0f, -0.34f, -0.01f), Radius = 0.075f },
                };
                groups.Add(g);
            }
            tailSpring.ColliderGroups = groups.ToArray();

            tailSpring.m_gravityDir = Vector3.down;
            tailSpring.m_gravityPower = gravity;
            tailSpring.m_dragForce = drag;
            tailSpring.m_stiffnessForce = stiffness;

            phase = Random.value * 10f;
            nextFlick = Time.time + Random.Range(flickInterval.x, flickInterval.y);
            pitch = baseLift;
            lastHipsY = hips.position.y;
        }

        /// <summary>Values from the Blender walk simulation: jelly bust, hair a little stiffer and freer, calm ears. Runs before the spring bones read their settings.</summary>
        void TuneSpring(VRMSpringBone sb)
        {
            switch (sb.m_comment)
            {
                case "Bust":
                    sb.m_stiffnessForce = bustStiffness; sb.m_dragForce = bustDrag; sb.m_gravityPower = 0f;
                    break;
                case "Hair":
                    sb.m_stiffnessForce *= hairStiffnessFactor; sb.m_dragForce = hairDrag; sb.m_gravityPower = 0f;
                    break;
                case "CatEar":
                    sb.m_stiffnessForce = earStiffness; sb.m_dragForce = earDrag; sb.m_gravityPower = 0f;
                    break;
            }
        }

        /// <summary>
        /// Bends the tail joints to the rest curve between the standing (k = 0) and the walking (k = 1) shape. The spring bones take the local
        /// rotations they find at Setup as their rest pose, so while the shape changes Setup(true) is called with the new rest pose
        /// (the physics restarts from the shape, which is no problem during the short blend).
        /// </summary>
        void ApplyTailRest(float k, float kRun, bool resetSpring)
        {
            for (int i = 0; i < tailJoints.Length; i++)
            {
                float walk = i < walkRestPitch.Length ? walkRestPitch[i] : restPitch[i];
                float run = i < runRestPitch.Length ? runRestPitch[i] : walk;
                if (idleV2Delta != null)
                {
                    // standing = the Blender idle v2 shape (a full rotation), walking and running = pitch only; same axis, so the blend is the same as before
                    var q = Quaternion.Slerp(Quaternion.Slerp(idleV2Delta[i], Quaternion.Euler(walk, 0f, 0f), k), Quaternion.Euler(run, 0f, 0f), kRun);
                    tailJoints[i].localRotation = q * tailBaseRotation[i];
                    continue;
                }
                float p = Mathf.Lerp(Mathf.Lerp(restPitch[i], walk, k), run, kRun);
                tailJoints[i].localRotation = Quaternion.Euler(p, 0f, 0f) * tailBaseRotation[i];
            }
            if (resetSpring && tailSpring != null) tailSpring.Setup(true);
        }

        /// <summary>
        /// Turns the world rotations of the Blender idle v2 tail (idleV2TailRotation, model axes) into a local rotation per joint, relative to the
        /// T-pose, once at the start: the joints are set joint by joint (parent first) as the Blender shape says, read back and put back to the T-pose.
        /// </summary>
        void ComputeIdleV2TailShape()
        {
            idleV2Delta = null;
            if (!useIdleV2TailShape || idleV2TailRotation == null || idleV2TailRotation.Length < tailJoints.Length) return;
            int n = tailJoints.Length;
            var restWorld = new Quaternion[n];
            for (int i = 0; i < n; i++) restWorld[i] = tailJoints[i].rotation;
            Quaternion model = transform.rotation, modelInv = Quaternion.Inverse(model);
            for (int i = 0; i < n; i++)
            {
                var e = idleV2TailRotation[i];
                tailJoints[i].rotation = model * new Quaternion(e.x, e.y, e.z, e.w) * modelInv * restWorld[i];
            }
            idleV2Delta = new Quaternion[n];
            for (int i = 0; i < n; i++) idleV2Delta[i] = tailJoints[i].localRotation * Quaternion.Inverse(tailBaseRotation[i]);
            for (int i = 0; i < n; i++) tailJoints[i].localRotation = tailBaseRotation[i];
        }

        void SetupEars()
        {
            string[] names = { "J_Opt_L_CatEar1_01", "J_Opt_R_CatEar1_01" };
            for (int i = 0; i < 2; i++)
            {
                var b = FindDeep(transform, names[i]);
                if (b == null) continue;
                ears[i] = new Ear
                {
                    bone = b,
                    restLocal = b.localRotation,
                    sideSign = i == 0 ? 1f : -1f,
                    nextFlick = Time.time + Random.Range(earFlickInterval.x, earFlickInterval.y) + i * 2f,
                    earPhase = i == 0 ? 0.6f : 2.1f
                };
            }
        }

        void LateUpdate()
        {
            float dt = Time.deltaTime;
            if (dt <= 0f) return;
            UpdateEars();
            if (driver != null) UpdateTailAndWind(dt);
            StepSprings(dt);
        }

        /// <summary>Steps every spring bone with a fixed time step (springStepsPerSecond), as often as the elapsed time needs.</summary>
        void StepSprings(float dt)
        {
            float h = 1f / Mathf.Max(10f, springStepsPerSecond);
            springClock += dt;
            int steps = 0;
            while (springClock >= h && steps < 6)
            {
                for (int i = 0; i < allSprings.Count; i++) allSprings[i].ManualUpdate(h);
                springClock -= h;
                steps++;
            }
            if (steps == 6) springClock = 0f;                                                // far behind (a long hitch): do not catch up
        }

        void UpdateTailAndWind(float dt)
        {
            float time = Time.time + phase;

            float speed = controller != null ? controller.HorizontalSpeed : 0f;
            float walkRef = controller != null ? controller.walkSpeed : 1.5f;
            float runRef = controller != null ? controller.runSpeed : 4.4f;
            float walkN = Mathf.Clamp01(speed / walkRef);                                           // 0 standing .. 1 at walking speed
            float runN = Mathf.Clamp01((speed - walkRef) / Mathf.Max(0.1f, runRef - walkRef));      // 0 at walking speed .. 1 running
            bool grounded = controller == null || controller.IsGrounded;
            float vy = controller != null ? controller.Velocity.y : 0f;
            bool dash = controller != null && controller.IsDashing;

            // tail rest curve: standing C <-> walking J
            float restTarget = speed > 0.3f * walkRef ? 1f : 0f;
            restBlend = Mathf.MoveTowards(restBlend, restTarget, dt / Mathf.Max(0.05f, restBlendTime));
            float runTarget = speed > walkRef + 0.55f * (runRef - walkRef) ? 1f : 0f;                // the arch only in the real sprint
            runBlend = Mathf.MoveTowards(runBlend, runTarget, dt / Mathf.Max(0.05f, restBlendTime));
            if (Mathf.Abs(restBlend - restBlendApplied) > 0.002f || Mathf.Abs(runBlend - runBlendApplied) > 0.002f)
            {
                ApplyTailRest(restBlend, runBlend, true);
                restBlendApplied = restBlend;
                runBlendApplied = runBlend;
            }
            tailSpring.m_stiffnessForce = Mathf.Lerp(Mathf.Lerp(stiffness, walkStiffness, restBlend), sprintStiffness, runBlend);
            tailSpring.m_dragForce = Mathf.Lerp(drag, sprintDrag, runBlend);
            UpdateSpringBlend(dt);

            // how fast the pelvis is going up (smoothed) and how far it is turned against the character, for the walking swing of the tail base
            float hy = hips.position.y;
            bounceSpeed = Mathf.Lerp(bounceSpeed, (hy - lastHipsY) / dt, 1f - Mathf.Exp(-dt / 0.03f));
            lastHipsY = hy;
            Vector3 flatForward = Vector3.ProjectOnPlane(hips.forward, transform.up);
            float pelvisYaw = flatForward.sqrMagnitude > 1e-6f ? Vector3.SignedAngle(transform.forward, flatForward, transform.up) : 0f;
            float stepRate = controller != null ? controller.LocoMultiplier / WalkCycleSeconds : 1f / WalkCycleSeconds;
            gaitPhase += stepRate * dt;

            // lazy sway while standing; while walking the base swings against the pelvis (Blender: -tail_lat * pelvis yaw / max yaw) and nods against its bounce;
            // faster and smaller side sway while running
            float lazy = (Mathf.Sin(6.2832f * time / swayPeriod) + 0.35f * Mathf.Sin(6.2832f * time / (swayPeriod * 0.5f) + 1.3f)) / 1.35f;
            float standing = 1f - walkN;
            float swayK = idleV2Delta != null ? idleV2SwayScale : 1f;                               // the hanging idle v2 tail has a longer lever
            float targetYaw = swayYaw * swayK * standing * lazy
                              - Mathf.Lerp(walkYaw, sprintYaw, runBlend) * walkN * Mathf.Clamp(pelvisYaw / 8f, -1.5f, 1.5f)
                              + runYaw * runN * Mathf.Sin(6.2832f * gaitPhase);
            float targetPitch = baseLift + swayPitch * swayK * standing * Mathf.Sin(6.2832f * 2f * time / swayPeriod + 0.8f)
                                - Mathf.Lerp(walkPitch, sprintPitch, runBlend) * walkN * Mathf.Clamp(bounceSpeed / Mathf.Lerp(PelvisPeakSpeed, RunPelvisPeakSpeed, runBlend), -1.5f, 1.5f) + runLift * runN;
            if (!grounded) targetPitch += vy > 0f ? airLiftRising : airLiftFalling;
            if (dash) { targetPitch = dashPitch; targetYaw = 0f; }

            yaw = Mathf.SmoothDamp(yaw, targetYaw, ref yawVel, walkN > 0.5f ? 0.03f : smoothTime);
            pitch = Mathf.SmoothDamp(pitch, targetPitch, ref pitchVel, walkN > 0.5f ? 0.03f : smoothTime);
            driver.localRotation = Quaternion.Euler(pitch, yaw, 0f);

            // tip flick now and then (only when standing or walking slowly), kick when landing
            if (flickTimer > 0f) flickTimer -= dt;
            if (kickTimer > 0f) kickTimer -= dt;
            if (Time.time >= nextFlick)
            {
                nextFlick = Time.time + Random.Range(flickInterval.x, flickInterval.y);
                if (walkN < 0.5f && grounded) TriggerFlick();
            }
            if (!wasGrounded && grounded && vy < 0.5f) kickTimer = 0.18f;
            wasGrounded = grounded;

            // wind of movement: everything streams back against the direction she moves
            Vector3 v = controller != null ? controller.Velocity : Vector3.zero;
            v.y *= verticalWindFactor;
            wind = Vector3.SmoothDamp(wind, -v, ref windVel, 0.08f);
            // the headwind grows into the sprint push of the Blender run (hair 0.19, ears 0.30 m/s at 5 m/s, a share of it lifting)
            float hairGain = Mathf.Lerp(windHair, windHairSprint / Mathf.Max(0.1f, runRef), sprintK);
            float earGain = Mathf.Lerp(windOther, windEarSprint / Mathf.Max(0.1f, runRef), sprintK);
            Vector3 lift = Vector3.up * (wind.magnitude * windLift * sprintK);
            // idle breeze: a steady, slowly waving push on the hair while she stands, two gusts per loop (only standing, not while she moves)
            float breezeK = 1f - Mathf.Clamp01(speed / (0.5f * walkRef));
            float gust = GustBump(Time.time, idleGustTimes.x) + GustBump(Time.time, idleGustTimes.y);
            float waves = 1f + 0.25f * Mathf.Sin(6.2832f * Time.time / 6f + 0.9f);
            Vector3 breeze = transform.TransformDirection(idleWindDirection.normalized) * (idleWindHair * breezeK * waves * (1f + idleGustStrength * gust));
            foreach (var sb in hairSprings) sb.ExternalForce = (wind + lift) * hairGain + breeze;
            foreach (var sb in earSprings) sb.ExternalForce = (wind + lift) * earGain;
            foreach (var sb in otherSprings) sb.ExternalForce = wind * windOther;

            Vector3 force = wind * windTail;
            if (flickTimer > 0f)
            {
                float k = Mathf.Sin(Mathf.PI * (1f - flickTimer / flickDuration));          // 0 -> 1 -> 0
                float flickScale = idleV2Delta != null ? Mathf.Lerp(idleV2FlickScale, 1f, walkN) : 1f;
                force += driver.right * (flickSign * flickForce * flickScale * k);
            }
            if (kickTimer > 0f) force += Vector3.down * (landKick * (kickTimer / 0.18f));
            tailSpring.ExternalForce = force;
        }

        /// <summary>0..1 bump around a gust time of the idle loop (periodic, so the gusts repeat every idleGustPeriod seconds).</summary>
        float GustBump(float time, float center)
        {
            float half = idleGustPeriod * 0.5f;
            float d = Mathf.Abs(Mathf.Repeat(time - center + half, idleGustPeriod) - half);
            return Mathf.Exp(-(d / Mathf.Max(0.05f, idleGustWidth)) * (d / Mathf.Max(0.05f, idleGustWidth)));
        }

        /// <summary>Blends the spring values between the walk and the sprint values of the Blender simulations (the springs read their values at every step).</summary>
        void UpdateSpringBlend(float dt)
        {
            float target = controller != null ? controller.SprintBlend : 0f;
            sprintK = Mathf.Lerp(sprintK, target, 1f - Mathf.Exp(-dt / 0.25f));
            if (!tuneSprings) return;
            foreach (var sb in bustSprings) sb.m_stiffnessForce = Mathf.Lerp(bustStiffness, bustStiffnessSprint, sprintK);
            foreach (var sb in hairSprings) sb.m_dragForce = Mathf.Lerp(hairDrag, hairDragSprint, sprintK);
            foreach (var sb in earSprings)
            {
                sb.m_stiffnessForce = Mathf.Lerp(earStiffness, earStiffnessSprint, sprintK);
                sb.m_dragForce = Mathf.Lerp(earDrag, earDragSprint, sprintK);
            }
        }

        void UpdateEars()
        {
            for (int i = 0; i < 2; i++)
            {
                var e = ears[i];
                if (e == null) continue;
                if (Time.time >= e.nextFlick)
                {
                    e.flickStart = Time.time;
                    e.nextFlick = Time.time + Random.Range(earFlickInterval.x, earFlickInterval.y);
                }
                float u = (Time.time - e.flickStart) / EarFlickLength;
                float bump = u >= 0f && u <= 1f ? Mathf.Sin(Mathf.PI * u) : 0f;           // 0 -> 1 -> 0
                float sway = earSway * Mathf.Sin(6.2832f * Time.time / (swayPeriod * 0.5f) + e.earPhase);
                // fold back = tilt the ear tip to -Z (negative turn about the right axis), out = tilt it sideways
                var q = Quaternion.AngleAxis(-(sway + earFoldBack * bump + earBaseBack), transform.right)
                        * Quaternion.AngleAxis(e.sideSign * earOut * bump, transform.forward);
                e.bone.localRotation = e.restLocal;
                e.bone.rotation = q * e.bone.rotation;
            }
        }

        /// <summary>Flicks the tip of the tail once (also used by tests and later by emotes).</summary>
        public void TriggerFlick()
        {
            flickTimer = flickDuration;
            flickSign = Random.value < 0.5f ? -1f : 1f;
        }

        static Transform FindDeep(Transform root, string name)
        {
            if (root == null) return null;
            if (root.name == name) return root;
            for (int i = 0; i < root.childCount; i++)
            {
                var r = FindDeep(root.GetChild(i), name);
                if (r != null) return r;
            }
            return null;
        }
    }
}
