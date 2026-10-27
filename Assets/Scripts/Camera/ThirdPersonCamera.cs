using UnityEngine;
using ZeroProtocol.Player;

namespace ZeroProtocol.CameraSystem
{
    /// <summary>
    /// Orbit camera behind the player (free look with the mouse). When a lock target is set the camera
    /// swings behind the player so the target stays in view, like the lock-on of Wuthering Waves.
    /// Walls pull the camera in so it never sits inside geometry.
    /// </summary>
    [DefaultExecutionOrder(100)]
    public class ThirdPersonCamera : MonoBehaviour
    {
        [Header("Follow")]
        public Transform target;
        public GameInput input;
        public float pivotHeight = 1.35f;
        public float shoulderOffset = 0.35f;

        [Header("Orbit")]
        public float distance = 4.4f;
        public float minDistance = 2.2f;
        public float maxDistance = 7.5f;
        public float minPitch = -22f;
        public float maxPitch = 62f;
        public float followSmoothing = 18f;

        [Header("Speed feel")]
        [Tooltip("The field of view opens by this many degrees at the sprint speed (the world rushes past), and the camera drops back a little. Smooth, no pop between walk and sprint.")]
        public float sprintFovBoost = 6f;
        public float sprintDistanceBoost = 0.35f;
        [Tooltip("Seconds the speed feel needs to follow the speed.")]
        public float speedFeelTime = 0.35f;

        [Header("Over-the-shoulder Aim (ADS)")]
        public float aimFov = 42f;
        public float aimDistance = 2.4f;
        public float aimShoulderOffset = 0.58f;
        public float aimPivotHeight = 1.30f;
        public float aimSmoothTime = 0.12f;

        [Header("Harmonic Recoil Kick")]
        public float recoilOmega = 28f;
        public float recoilZeta = 0.75f;

        [Header("Aim Assist Tier 1: Crosshair Friction & Subtle Magnetic Nudge")]
        public float frictionRadius = 0.4f;
        public float frictionMaxRange = 60f;
        public float frictionMin = 0.65f;
        public float alphaOuter = 6.0f;
        public float nudgeConeAngle = 3.0f;
        public float nudgeMaxRate = 1.5f;

        [Header("Collision")]
        public float collisionRadius = 0.25f;
        public float collisionPadding = 0.1f;

        [Header("Lock-on")]
        public Transform lockTarget;
        public float lockTurnSpeed = 7f;
        public float lockPitch = 14f;

        public float Yaw { get { return yaw; } }

        float yaw, pitch = 15f;
        float baseFov, speedFeel;
        float aimBlend, aimVelocity;
        Vector2 recoilOffset, recoilVelocity;
        Camera cam;
        YoruController mover;
        ZeroProtocol.Combat.DualPistolCombat combat;
        float currentDistance;
        Vector3 smoothedPivot;
        readonly RaycastHit[] hits = new RaycastHit[8];
        readonly RaycastHit[] frictionHits = new RaycastHit[16];

        void OnEnable()
        {
            if (combat == null && target != null)
            {
                combat = target.GetComponent<ZeroProtocol.Combat.DualPistolCombat>();
            }
            if (combat != null)
            {
                combat.OnWeaponFired -= HandleWeaponFired;
                combat.OnWeaponFired += HandleWeaponFired;
            }
        }

        void Start()
        {
            if (target != null)
            {
                yaw = target.eulerAngles.y;
                smoothedPivot = target.position + Vector3.up * pivotHeight;
                if (combat == null) combat = target.GetComponent<ZeroProtocol.Combat.DualPistolCombat>();
            }
            if (combat != null)
            {
                combat.OnWeaponFired -= HandleWeaponFired;
                combat.OnWeaponFired += HandleWeaponFired;
            }
            currentDistance = distance;
            if (input == null && target != null) input = target.GetComponent<GameInput>();
            cam = GetComponent<Camera>();
            if (cam != null) baseFov = cam.fieldOfView;
            if (target != null) mover = target.GetComponent<YoruController>();
        }

        void OnDisable()
        {
            if (combat != null) combat.OnWeaponFired -= HandleWeaponFired;
        }

        void OnDestroy()
        {
            if (combat != null) combat.OnWeaponFired -= HandleWeaponFired;
        }

        public void AddRecoil(Vector2 kickAngles)
        {
            recoilVelocity.x += kickAngles.x * recoilOmega;
            recoilVelocity.y += kickAngles.y * recoilOmega;
        }

        void HandleWeaponFired(ZeroProtocol.Combat.FireEventData fireData)
        {
            float yawKick = (fireData.Hand == ZeroProtocol.Combat.HandSide.Left) ? -0.32f : 0.32f;
            // Negative pitch kicks camera upward in this coordinate setup
            AddRecoil(new Vector2(-1.3f, yawKick));
        }

        void LateUpdate()
        {
            if (target == null) return;
            float dt = Time.deltaTime;
            if (dt <= 0f) return;

            if (input != null)
            {
                distance = Mathf.Clamp(distance + input.Zoom, minDistance, maxDistance);
            }

            // ADS Over-the-shoulder SmoothDamp Spring
            float targetAim = (input != null && input.AimHeld) ? 1f : 0f;
            aimBlend = Mathf.SmoothDamp(aimBlend, targetAim, ref aimVelocity, aimSmoothTime);

            float currentPivotHeight = Mathf.Lerp(pivotHeight, aimPivotHeight, aimBlend);
            float currentShoulder = Mathf.Lerp(shoulderOffset, aimShoulderOffset, aimBlend);
            float targetWantedDist = Mathf.Lerp(distance, aimDistance, aimBlend);

            // Speed feel & FOV blending
            float feelTarget = mover != null ? mover.SprintBlend : 0f;
            speedFeel = Mathf.Lerp(speedFeel, feelTarget, 1f - Mathf.Exp(-dt / Mathf.Max(0.02f, speedFeelTime)));
            if (cam != null && baseFov > 0f)
            {
                float baseOrSprintFov = baseFov + sprintFovBoost * speedFeel;
                cam.fieldOfView = Mathf.Lerp(baseOrSprintFov, aimFov, aimBlend);
            }

            Vector3 pivot = target.position + Vector3.up * currentPivotHeight;
            smoothedPivot = Vector3.Lerp(smoothedPivot, pivot, 1f - Mathf.Exp(-followSmoothing * dt));

            // Harmonic Recoil Spring Simulation with substepping for low-FPS numerical stability
            float simTime = dt;
            while (simTime > 0f)
            {
                float step = Mathf.Min(simTime, 0.02f);
                Vector2 recoilAccel = -2f * recoilZeta * recoilOmega * recoilVelocity - (recoilOmega * recoilOmega) * recoilOffset;
                recoilVelocity += recoilAccel * step;
                recoilOffset += recoilVelocity * step;
                simTime -= step;
            }

            // Tier 1 Aim Assist: Crosshair Friction & Subtle Magnetic Nudge
            float frictionFactor = 1.0f;
            Vector3 camForward = Quaternion.Euler(pitch, yaw, 0f) * Vector3.forward;
            Vector3 camOrigin = (cam != null) ? cam.transform.position : smoothedPivot;

            float bestAlpha = float.MaxValue;
            Vector3 bestTargetCenter = Vector3.zero;

            var activeTargets = ZeroProtocol.Combat.ShootingTarget.ActiveTargets;
            if (activeTargets != null)
            {
                for (int i = 0; i < activeTargets.Count; i++)
                {
                    var st = activeTargets[i];
                    if (st == null || !st.IsAlive) continue;

                    // Evaluate Head
                    Vector3 toHead = st.HeadPosition - camOrigin;
                    float distHead = toHead.magnitude;
                    if (distHead > 0.1f && distHead <= frictionMaxRange)
                    {
                        Vector3 dirHead = toHead / distHead;
                        float aHead = Vector3.Angle(camForward, dirHead);
                        if (aHead <= alphaOuter && aHead < bestAlpha)
                        {
                            if (CheckFrictionLineOfSight(camOrigin, dirHead, distHead, st.transform))
                            {
                                bestAlpha = aHead;
                                bestTargetCenter = st.HeadPosition;
                            }
                        }
                    }

                    // Evaluate Body
                    Vector3 toBody = st.BodyPosition - camOrigin;
                    float distBody = toBody.magnitude;
                    if (distBody > 0.1f && distBody <= frictionMaxRange)
                    {
                        Vector3 dirBody = toBody / distBody;
                        float aBody = Vector3.Angle(camForward, dirBody);
                        if (aBody <= alphaOuter && aBody < bestAlpha)
                        {
                            if (CheckFrictionLineOfSight(camOrigin, dirBody, distBody, st.transform))
                            {
                                bestAlpha = aBody;
                                bestTargetCenter = st.BodyPosition;
                            }
                        }
                    }
                }
            }

            if (bestAlpha <= alphaOuter)
            {
                float sStep = Mathf.SmoothStep(0f, alphaOuter, bestAlpha);
                // S_effective = S_base * lerp(frictionMin, 1.0, smoothstep(0, alpha_outer, alpha))
                frictionFactor = Mathf.Lerp(frictionMin, 1.0f, sStep);
            }

            if (lockTarget != null)
            {
                Vector3 toTarget = lockTarget.position - target.position;
                toTarget.y = 0f;
                if (toTarget.sqrMagnitude > 0.01f)
                {
                    float goalYaw = Mathf.Atan2(toTarget.x, toTarget.z) * Mathf.Rad2Deg;
                    float k = 1f - Mathf.Exp(-lockTurnSpeed * dt);
                    yaw = Mathf.LerpAngle(yaw, goalYaw, k);
                    pitch = Mathf.Lerp(pitch, lockPitch, k);
                }
            }
            else
            {
                // Subtle magnetic nudge when near target center (microscopic gentle pull <= 1.5 deg/s)
                if (bestAlpha <= nudgeConeAngle && bestTargetCenter != Vector3.zero)
                {
                    Vector3 toBest = (bestTargetCenter - camOrigin).normalized;
                    float targetYaw = Mathf.Atan2(toBest.x, toBest.z) * Mathf.Rad2Deg;
                    float targetPitch = -Mathf.Asin(Mathf.Clamp(toBest.y, -1f, 1f)) * Mathf.Rad2Deg;
                    float deltaYaw = Mathf.DeltaAngle(yaw, targetYaw);
                    float deltaPitch = Mathf.DeltaAngle(pitch, targetPitch);
                    float maxNudge = nudgeMaxRate * dt;
                    yaw += Mathf.Clamp(deltaYaw, -maxNudge, maxNudge);
                    pitch = Mathf.Clamp(pitch + Mathf.Clamp(deltaPitch, -maxNudge, maxNudge), minPitch, maxPitch);
                }

                if (input != null)
                {
                    yaw += input.Look.x * frictionFactor;
                    pitch = Mathf.Clamp(pitch - input.Look.y * frictionFactor, minPitch, maxPitch);
                }
            }

            float finalPitch = Mathf.Clamp(pitch + recoilOffset.x, minPitch, maxPitch);
            float finalYaw = yaw + recoilOffset.y;
            Quaternion rot = Quaternion.Euler(finalPitch, finalYaw, 0f);
            Vector3 back = rot * Vector3.back;
            Vector3 right = rot * Vector3.right;
            Vector3 origin = smoothedPivot + right * currentShoulder;

            // Collision pull-in
            float wanted = targetWantedDist + sprintDistanceBoost * speedFeel;
            int n = Physics.SphereCastNonAlloc(origin, collisionRadius, back, hits, wanted + collisionPadding,
                                               ~0, QueryTriggerInteraction.Ignore);
            float nearest = wanted;
            for (int i = 0; i < n; i++)
            {
                if (hits[i].transform.IsChildOf(target)) continue;
                if (hits[i].distance < nearest) nearest = hits[i].distance - collisionPadding;
            }
            nearest = Mathf.Max(nearest, 0.4f);
            currentDistance = nearest < currentDistance
                ? nearest
                : Mathf.Lerp(currentDistance, nearest, 1f - Mathf.Exp(-6f * dt));

            transform.position = origin + back * currentDistance;
            transform.rotation = Quaternion.LookRotation(origin - transform.position + Vector3.up * 0.15f, Vector3.up);
        }

        bool CheckFrictionLineOfSight(Vector3 from, Vector3 dir, float dist, Transform targetTransform)
        {
            int count = Physics.RaycastNonAlloc(from, dir, frictionHits, dist, ~0, QueryTriggerInteraction.Ignore);
            for (int i = 0; i < count; i++)
            {
                RaycastHit h = frictionHits[i];
                if (h.collider == null) continue;
                if (target != null && h.transform.IsChildOf(target)) continue;
                if (targetTransform != null && (h.transform == targetTransform || h.transform.IsChildOf(targetTransform))) continue;
                if (h.collider.GetComponentInParent<ZeroProtocol.Combat.IDamageable>() != null) continue;

                if (h.distance < dist - 0.05f)
                {
                    return false;
                }
            }
            return true;
        }
    }
}
