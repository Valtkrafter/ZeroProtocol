using System;
using UnityEngine;
using ZeroProtocol.Player;
using ZeroProtocol.Combat;

namespace ZeroProtocol.CameraSystem
{
    /// <summary>
    /// True Combat Lock-On System (Middle Mouse Button toggle).
    /// Manages target acquisition, auto-switching on target death/destruction,
    /// and camera rig targeting.
    /// </summary>
    [RequireComponent(typeof(GameInput))]
    public class LockOnSystem : MonoBehaviour
    {
        public ThirdPersonCamera cameraRig;
        public float maxLockDistance = 35f;
        public float breakDistance = 42f;
        [Range(10f, 90f)] public float maxViewAngle = 65f;

        public LockOnTarget Current { get; private set; }
        public bool IsLockedOn => Current != null;

        public event Action<LockOnTarget> OnLockTargetChanged;

        GameInput input;
        readonly RaycastHit[] losHits = new RaycastHit[8];

        void Awake()
        {
            EnsureComponents();
        }

        public void EnsureComponents()
        {
            if (input == null) input = GetComponent<GameInput>();
            if (cameraRig == null && Camera.main != null)
            {
                cameraRig = Camera.main.GetComponent<ThirdPersonCamera>();
            }
        }

        void Update()
        {
            EnsureComponents();

            // Check if current target is invalid, dead, or out of range
            if (Current != null)
            {
                bool targetInvalid = !Current.isActiveAndEnabled;
                if (!targetInvalid)
                {
                    IDamageable damageable = Current.GetComponentInParent<IDamageable>();
                    if (damageable != null && !damageable.IsAlive)
                    {
                        targetInvalid = true;
                    }
                    else
                    {
                        float sqrDist = (Current.transform.position - transform.position).sqrMagnitude;
                        if (sqrDist > breakDistance * breakDistance)
                        {
                            targetInvalid = true;
                        }
                    }
                }

                if (targetInvalid)
                {
                    // Auto-switch to next closest valid target on kill / break
                    AutoSwitchTarget();
                }
            }

            if (input != null && input.LockOnPressed)
            {
                if (Current != null)
                {
                    Release();
                }
                else
                {
                    Acquire();
                }
            }
        }

        public void Acquire()
        {
            EnsureComponents();
            if (cameraRig == null && Camera.main != null)
            {
                cameraRig = Camera.main.GetComponent<ThirdPersonCamera>();
            }
            if (cameraRig == null) return;

            Transform cam = cameraRig.transform;
            LockOnTarget best = FindBestTarget(cam, null);

            if (best != null)
            {
                SetTarget(best);
            }
        }

        void AutoSwitchTarget()
        {
            EnsureComponents();
            Transform cam = cameraRig != null ? cameraRig.transform : (Camera.main != null ? Camera.main.transform : null);
            LockOnTarget oldTarget = Current;
            LockOnTarget best = cam != null ? FindBestTarget(cam, oldTarget) : null;

            if (best != null)
            {
                SetTarget(best);
            }
            else
            {
                Release();
            }
        }

        LockOnTarget FindBestTarget(Transform cam, LockOnTarget excludeTarget)
        {
            LockOnTarget best = null;
            float bestScore = float.MaxValue;

            for (int i = LockOnTarget.All.Count - 1; i >= 0; i--)
            {
                LockOnTarget t = LockOnTarget.All[i];
                if (t == null)
                {
                    LockOnTarget.All.RemoveAt(i);
                    continue;
                }
                if (t == excludeTarget || !t.isActiveAndEnabled) continue;

                IDamageable damageable = t.GetComponentInParent<IDamageable>();
                if (damageable != null && !damageable.IsAlive) continue;

                Vector3 to = t.AimPoint - cam.position;
                float dist = to.magnitude;
                if (dist > maxLockDistance || dist < 0.5f) continue;

                float angle = Vector3.Angle(cam.forward, to / dist);
                if (angle > maxViewAngle) continue;

                // Line of sight check
                if (!HasLineOfSight(cam.position, t.AimPoint, t.transform)) continue;

                float score = angle + dist * 0.2f; // Prefer screen center, then closer distance
                if (score < bestScore)
                {
                    bestScore = score;
                    best = t;
                }
            }

            return best;
        }

        bool HasLineOfSight(Vector3 from, Vector3 to, Transform targetT)
        {
            Vector3 diff = to - from;
            float dist = diff.magnitude;
            if (dist <= 0.05f) return true;
            Vector3 dir = diff / dist;

            int count = Physics.RaycastNonAlloc(from, dir, losHits, dist, ~0, QueryTriggerInteraction.Ignore);
            for (int i = 0; i < count; i++)
            {
                RaycastHit h = losHits[i];
                if (h.collider == null) continue;
                if (h.transform.IsChildOf(transform)) continue;
                if (targetT != null && (h.transform == targetT || h.transform.IsChildOf(targetT))) continue;
                if (h.collider.GetComponentInParent<IDamageable>() != null) continue;

                if (h.distance < dist - 0.05f)
                {
                    return false;
                }
            }
            return true;
        }

        public void SetTarget(LockOnTarget target)
        {
            Current = target;
            if (cameraRig != null)
            {
                cameraRig.lockTarget = target != null ? target.transform : null;
            }
            OnLockTargetChanged?.Invoke(Current);
        }

        public void Release()
        {
            Current = null;
            if (cameraRig != null)
            {
                cameraRig.lockTarget = null;
            }
            OnLockTargetChanged?.Invoke(null);
        }
    }
}
