using System.Collections.Generic;
using UnityEngine;

namespace ZeroProtocol.Player
{
    /// <summary>
    /// Third-person movement for Yoru: camera-relative walk and sprint, jump (with coyote time and input buffer),
    /// and a short dodge (the dash). Feeds the Animator (see YoruAnimatorBuilder for the meaning of the parameters);
    /// parameters that the Animator does not have are skipped.
    /// Moving (W, or the stick) plays the walk: the clip Yoru_Walk was made for walkSpeed. A light stick tilt walks proportionally slower.
    /// Shift: a press is the DODGE (the dash starts at once), holding it on goes into the SPRINT as soon as the dodge is over (sprintHoldDelay);
    /// letting go ends the sprint. Ctrl is reserved for its own animation later.
    /// The ground speed wobbles a little within every step, like the speed of a real walker (see gaitSpeedVariation).
    /// </summary>
    [RequireComponent(typeof(CharacterController), typeof(GameInput))]
    public class YoruController : MonoBehaviour
    {
        [Header("Walk")]
        [Tooltip("Mean ground speed (m/s) of the walk cycle: Blender/Yoru_Walk_gait.json speed, the same number as WalkSpeed in YoruAnimatorBuilder. This is the speed of W.")]
        public float walkSpeed = 1.5f;
        [Tooltip("Stick tilt (pad) that already gives the full walking speed; a lighter tilt walks proportionally slower. The keyboard always gives 1.")]
        [Range(0.2f, 0.9f)] public float walkTilt = 0.5f;
        [Tooltip("Seconds the animator speed needs to follow the real speed (no pop between idle and walk).")]
        public float animSpeedDamp = 0.09f;
        [Tooltip("The ground speed of a real walker is not constant: she is a little faster while both feet are on the ground and a little slower while the body rises over the stance leg. +- this share of walkSpeed, twice per cycle. Same numbers as speed_var / speed_var_phase of the Blender walk (Blender/Yoru_Walk_gait.json speed_variation), the planted feet of the clip depend on them.")]
        [Range(0f, 0.15f)] public float gaitSpeedVariation = 0.05f;
        [Tooltip("Phase of the walk cycle with the highest speed: where the pelvis is lowest (heel strike).")]
        public float gaitSpeedPhase = 0f;

        [Header("Sprint (hold Shift)")]
        [Tooltip("Ground speed (m/s) of the sprint = the speed of the run clip (Blender/Yoru_Run_gait.json). It is also the largest animator speed of the dodge.")]
        public float runSpeed = 5f;
        [Tooltip("Seconds Shift has to be held before the sprint starts: the length of the dodge, so the sprint takes over when the dodge is over. A shorter press is only the dodge.")]
        public float sprintHoldDelay = 0.24f;
        public float acceleration = 30f;
        public float deceleration = 40f;
        public float turnSpeed = 900f;
        [Tooltip("The ground speed of the sprint is not constant either: it dips by this share of runSpeed while a foot is on the ground (slowest at mid stance) and is steady in the flight. Same number as speed_var of the Blender run (Blender/Yoru_Run_gait.json speed_variation); the planted feet of the clip depend on it.")]
        [Range(0f, 0.15f)] public float runGaitSpeedVariation = 0.08f;
        [Tooltip("Share of the run cycle a foot is on the ground (PH_TO of the Blender run, 8 of 36 frames).")]
        public float runStanceShare = 0.2222f;
        [Tooltip("Ground speed (m/s) at which the fastest locomotion clip plays at normal speed: the sprint clip Yoru_Run (Blender/Yoru_Run_gait.json speed 5.0).")]
        public float clipRunSpeed = 5f;
        [Tooltip("Largest playback speed factor of the locomotion clips.")]
        public float maxLocoMult = 2f;

        [Header("Air")]
        public float gravity = -30f;
        public float jumpHeight = 1.7f;
        [Range(0f, 1f)] public float airControl = 0.55f;
        public float coyoteTime = 0.12f;
        public float jumpBuffer = 0.12f;
        [Tooltip("Short drops (stairs, curbs) do not count as falling for the animation.")]
        public float fallAnimDelay = 0.15f;

        [Header("Dash")]
        public float dashSpeed = 14f;
        public float dashDuration = 0.24f;
        public float dashCooldown = 0.6f;

        [Header("References")]
        public Transform cameraTransform;
        public Animator animator;
        public CameraSystem.LockOnSystem lockOn;

        public bool IsGrounded { get; private set; }
        public bool IsDashing { get { return dashTimer > 0f; } }
        /// <summary>True while she is walking on purpose (a move input, not a dash).</summary>
        public bool IsWalking { get; private set; }
        /// <summary>True while she sprints: Shift held for sprintHoldDelay (the dodge is over) and a move input.</summary>
        public bool IsSprinting { get; private set; }
        /// <summary>Walk cycle phase 0..1 (0 = right heel strike) as the animator plays it, and the factor the ground speed has right now (1 = mean speed).</summary>
        public float GaitPhase { get; private set; }
        public float GaitSpeedFactor { get; private set; } = 1f;
        /// <summary>0 = at walking speed or slower, 1 = at the sprint speed (how much of the sprint is in the pose).</summary>
        public float SprintBlend { get { return Mathf.Clamp01((HorizontalSpeed - walkSpeed) / Mathf.Max(0.01f, runSpeed - walkSpeed)); } }
        /// <summary>Playback speed factor of the locomotion clips (1 = as authored).</summary>
        public float LocoMultiplier { get; private set; } = 1f;
        public Vector3 Velocity { get { return horizontalVelocity + Vector3.up * verticalVelocity; } }
        public float HorizontalSpeed { get { return new Vector2(horizontalVelocity.x, horizontalVelocity.z).magnitude; } }

        CharacterController cc;
        GameInput input;
        Vector3 horizontalVelocity;
        float verticalVelocity;
        float coyoteTimer, jumpBufferTimer, dashTimer, dashCooldownTimer, shiftHeldTime;
        float airTime;
        bool jumpedThisAir, animGroundedPrev = true, runJump;
        Vector3 dashDirection;
        readonly HashSet<int> animParams = new HashSet<int>();

        static readonly int SpeedHash = Animator.StringToHash("Speed");
        static readonly int LocoMultHash = Animator.StringToHash("LocoMult");
        static readonly int GroundedHash = Animator.StringToHash("Grounded");
        static readonly int VerticalHash = Animator.StringToHash("VerticalVelocity");
        static readonly int AirPhaseHash = Animator.StringToHash("AirPhase");
        static readonly int RunJumpHash = Animator.StringToHash("RunJump");
        static readonly int DashingHash = Animator.StringToHash("Dashing");

        void Awake()
        {
            EnsureComponents();
        }

        public void EnsureComponents()
        {
            if (cc == null) cc = GetComponent<CharacterController>();
            if (input == null) input = GetComponent<GameInput>();
            if (animator == null) animator = GetComponentInChildren<Animator>();
            if (cameraTransform == null && Camera.main != null) cameraTransform = Camera.main.transform;
            if (lockOn == null) lockOn = GetComponent<CameraSystem.LockOnSystem>();
            if (animator != null)
            {
                animator.applyRootMotion = false;
                if (animator.runtimeAnimatorController != null && animParams.Count == 0)
                    foreach (var p in animator.parameters) animParams.Add(p.nameHash);
            }
        }

        void Update()
        {
            EnsureComponents();
            float dt = Time.deltaTime;
            if (dt <= 0f)
            {
                if (Application.isPlaying) return;
                dt = 0.02f;
            }

            Vector3 wish = CameraRelative(input != null ? input.Move : Vector2.zero);
            IsGrounded = cc != null && cc.isGrounded;
#if UNITY_EDITOR
            if (!Application.isPlaying) IsGrounded = true;
#endif

            // timers
            coyoteTimer = IsGrounded ? coyoteTime : coyoteTimer - dt;
            jumpBufferTimer = (input != null && input.JumpPressed) ? jumpBuffer : jumpBufferTimer - dt;
            dashCooldownTimer -= dt;
            if (dashTimer > 0f) dashTimer -= dt;
            shiftHeldTime = (input != null && input.SprintHeld) ? shiftHeldTime + dt : 0f;      // a press is the dodge, holding it on is the sprint
            if (IsGrounded) { airTime = 0f; if (verticalVelocity <= 0f) jumpedThisAir = false; }
            else airTime += dt;

            Vector3 toLockTarget = Vector3.zero;
            bool isLockedOn = false;
            if (lockOn != null && lockOn.Current != null)
            {
                toLockTarget = lockOn.Current.AimPoint - transform.position;
                toLockTarget.y = 0f;
                if (toLockTarget.sqrMagnitude > 0.01f) isLockedOn = true;
            }
            Vector3 lockForward = isLockedOn ? toLockTarget.normalized : transform.forward;

            // dash
            if (input != null && input.DashPressed && dashCooldownTimer <= 0f && !IsDashing && IsGrounded)
            {
                dashDirection = wish.sqrMagnitude > 0.01f ? wish.normalized : (isLockedOn ? lockForward : transform.forward);
                dashTimer = dashDuration;
                dashCooldownTimer = dashCooldown;
            }

            // horizontal velocity
            if (IsDashing)
            {
                IsSprinting = false;
                float t = 1f - dashTimer / dashDuration;                 // 0 -> 1
                float ease = Mathf.Lerp(1f, 0.35f, t * t);               // fast start, soft end
                horizontalVelocity = dashDirection * (dashSpeed * ease);
                if (isLockedOn)
                {
                    RotateTowards(lockForward, dt);
                }
                else
                {
                    RotateTowards(dashDirection, dt);
                }
            }
            else
            {
                float tilt = wish.magnitude;                              // 0..1, the keyboard always gives 1
                IsSprinting = input.SprintHeld && shiftHeldTime >= sprintHoldDelay && tilt > 0.1f;
                float wanted = WantedSpeed(tilt);
                IsWalking = tilt > 0.1f;
                Vector3 target = tilt > 0.0001f ? wish / tilt * wanted : Vector3.zero;
                float rate = (wish.sqrMagnitude > 0.01f ? acceleration : deceleration) * (IsGrounded ? 1f : airControl);
                horizontalVelocity = Vector3.MoveTowards(horizontalVelocity, target, rate * dt);
                if (isLockedOn)
                {
                    RotateTowards(lockForward, dt);
                }
                else if (wish.sqrMagnitude > 0.01f)
                {
                    RotateTowards(wish, dt);
                }
            }

            // vertical velocity
            if (IsGrounded && verticalVelocity < 0f) verticalVelocity = -2f;
            if (jumpBufferTimer > 0f && coyoteTimer > 0f && !IsDashing)
            {
                runJump = HorizontalSpeed > 0.5f * runSpeed;
                verticalVelocity = JumpSpeed;
                jumpBufferTimer = 0f;
                coyoteTimer = 0f;
                jumpedThisAir = true;
            }
            // average velocity over the frame: the jump reaches the same height at any frame rate
            float vyStart = verticalVelocity;
            verticalVelocity += gravity * dt * (IsDashing ? 0.25f : 1f);
            float vyMove = 0.5f * (vyStart + verticalVelocity);

            // the walk speed is not constant within a step (the planted feet of the clip were made for this wobble)
            GaitSpeedFactor = IsGrounded && !IsDashing ? GaitFactor() : 1f;
            if (cc != null) cc.Move((horizontalVelocity * GaitSpeedFactor + Vector3.up * vyMove) * dt);

            UpdateAnimator();
        }

        float JumpSpeed { get { return Mathf.Sqrt(2f * -gravity * jumpHeight); } }

        /// <summary>Wanted ground speed for a stick tilt (0..1): the walking speed from a tilt of walkTilt on, slower below (W = tilt 1); while sprinting always the sprint speed.</summary>
        float WantedSpeed(float tilt)
        {
            if (tilt <= 0.0001f) return 0f;
            if (IsSprinting) return runSpeed;                                         // the sprint is one speed: between the walk clip and the run clip the feet slide (measured, LocomotionQualityTest)
            return walkSpeed * Mathf.Min(1f, tilt / walkTilt);
        }

        /// <summary>
        /// Factor of the ground speed at the phase of the gait cycle the animator is at (both clips start at the right touchdown), weighted by how much
        /// of each clip is in the pose (the blend tree weights):
        ///   walk  1 + gaitSpeedVariation * cos(4 pi (phase - gaitSpeedPhase))
        ///   run   1 + runGaitSpeedVariation * (4 b / pi - dip),  dip = sin(pi q / b) while a foot is on the ground (q = time since its touchdown, period half a cycle, b = runStanceShare), 0 in the flight
        /// The animator phase is the one of the last frame.
        /// </summary>
        float GaitFactor()
        {
            if (animator == null) return 1f;
            GaitPhase = Mathf.Repeat(animator.GetCurrentAnimatorStateInfo(0).normalizedTime, 1f);
            float speed = HorizontalSpeed;
            float wRun = Mathf.Clamp01((speed - walkSpeed) / Mathf.Max(0.01f, runSpeed - walkSpeed));
            float wWalk = speed <= walkSpeed ? Mathf.Clamp01(speed / Mathf.Max(0.01f, walkSpeed)) : 1f - wRun;
            float walkTerm = gaitSpeedVariation * Mathf.Cos(4f * Mathf.PI * (GaitPhase - gaitSpeedPhase));
            float b = Mathf.Max(0.05f, runStanceShare);
            float q = Mathf.Repeat(GaitPhase, 0.5f);
            float dip = q < b ? Mathf.Sin(Mathf.PI * q / b) : 0f;
            float runTerm = runGaitSpeedVariation * (4f * b / Mathf.PI - dip);
            return 1f + wWalk * walkTerm + wRun * runTerm;
        }

        Vector3 CameraRelative(Vector2 stick)
        {
            if (stick.sqrMagnitude < 0.0001f) return Vector3.zero;
            Vector3 f = cameraTransform != null ? cameraTransform.forward : Vector3.forward;
            f.y = 0f; f.Normalize();
            Vector3 r = Vector3.Cross(Vector3.up, f);
            return Vector3.ClampMagnitude(f * stick.y + r * stick.x, 1f);
        }

        void RotateTowards(Vector3 direction, float dt)
        {
            direction.y = 0f;
            if (direction.sqrMagnitude < 0.0001f) return;
            Quaternion goal = Quaternion.LookRotation(direction, Vector3.up);
            transform.rotation = Quaternion.RotateTowards(transform.rotation, goal, turnSpeed * dt);
        }

        void UpdateAnimator()
        {
            if (animator == null || animParams.Count == 0) return;

            // a jump counts as "in the air" at once; a plain drop only after a short delay (stairs must not flicker)
            bool animGrounded = IsGrounded || (!jumpedThisAir && airTime < fallAnimDelay);
            if (animGroundedPrev && !animGrounded && !jumpedThisAir) runJump = HorizontalSpeed > 0.5f * runSpeed;
            animGroundedPrev = animGrounded;

            float speed = IsDashing ? Mathf.Min(HorizontalSpeed, runSpeed) : HorizontalSpeed;
            LocoMultiplier = speed > clipRunSpeed ? Mathf.Min(speed / clipRunSpeed, maxLocoMult) : 1f;
            SetFloatDamped(SpeedHash, speed, animSpeedDamp);
            SetFloat(LocoMultHash, LocoMultiplier);
            SetFloat(VerticalHash, verticalVelocity);
            // 0 = leaving the ground, 0.5 = top of the arc, 1 = touching down (clamped for long falls)
            SetFloat(AirPhaseHash, 0.5f - 0.5f * Mathf.Clamp(verticalVelocity / JumpSpeed, -1f, 1f));
            SetBool(GroundedHash, animGrounded);
            SetBool(RunJumpHash, runJump);
            SetBool(DashingHash, IsDashing);
        }

        void SetFloat(int hash, float value) { if (animParams.Contains(hash)) animator.SetFloat(hash, value); }
        void SetFloatDamped(int hash, float value, float damp) { if (animParams.Contains(hash)) animator.SetFloat(hash, value, damp, Time.deltaTime); }
        void SetBool(int hash, bool value) { if (animParams.Contains(hash)) animator.SetBool(hash, value); }
    }
}
