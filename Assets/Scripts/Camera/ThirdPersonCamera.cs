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

        [Header("Collision")]
        public float collisionRadius = 0.25f;
        public float collisionPadding = 0.1f;

        [Header("Lock-on")]
        public Transform lockTarget;
        public float lockTurnSpeed = 7f;
        public float lockPitch = 14f;

        public float Yaw { get { return yaw; } }

        float yaw, pitch = 15f;
        float currentDistance;
        Vector3 smoothedPivot;
        readonly RaycastHit[] hits = new RaycastHit[8];

        void Start()
        {
            if (target != null)
            {
                yaw = target.eulerAngles.y;
                smoothedPivot = target.position + Vector3.up * pivotHeight;
            }
            currentDistance = distance;
            if (input == null && target != null) input = target.GetComponent<GameInput>();
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

            Vector3 pivot = target.position + Vector3.up * pivotHeight;
            smoothedPivot = Vector3.Lerp(smoothedPivot, pivot, 1f - Mathf.Exp(-followSmoothing * dt));

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
            else if (input != null)
            {
                yaw += input.Look.x;
                pitch = Mathf.Clamp(pitch - input.Look.y, minPitch, maxPitch);
            }

            Quaternion rot = Quaternion.Euler(pitch, yaw, 0f);
            Vector3 back = rot * Vector3.back;
            Vector3 right = rot * Vector3.right;
            Vector3 origin = smoothedPivot + right * shoulderOffset;

            // pull in when something is between the pivot and the wanted camera spot
            float wanted = distance;
            int n = Physics.SphereCastNonAlloc(origin, collisionRadius, back, hits, distance + collisionPadding,
                                               ~0, QueryTriggerInteraction.Ignore);
            float nearest = wanted;
            for (int i = 0; i < n; i++)
            {
                if (hits[i].transform.IsChildOf(target)) continue;
                if (hits[i].distance < nearest) nearest = hits[i].distance - collisionPadding;
            }
            nearest = Mathf.Max(nearest, 0.4f);
            // go in fast, come back out slowly
            currentDistance = nearest < currentDistance
                ? nearest
                : Mathf.Lerp(currentDistance, nearest, 1f - Mathf.Exp(-6f * dt));

            transform.position = origin + back * currentDistance;
            transform.rotation = Quaternion.LookRotation(origin - transform.position + Vector3.up * 0.15f, Vector3.up);
        }
    }
}
