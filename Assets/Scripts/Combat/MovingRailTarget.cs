using UnityEngine;

namespace ZeroProtocol.Combat
{
    /// <summary>
    /// Moving target platform along a rail with sinusoidal velocity profile
    /// and configurable pause duration at each turning point.
    /// </summary>
    public class MovingRailTarget : MonoBehaviour
    {
        [Header("Rail Configuration")]
        [Tooltip("Offset from initial starting position to end of rail")]
        public Vector3 railOffset = new Vector3(10f, 0f, 0f);

        [Tooltip("Seconds required to traverse from one end to the other")]
        public float travelDuration = 3.5f;

        [Tooltip("Seconds to hold position at each end before turning back")]
        public float pauseDuration = 0.75f;

        [Header("Attached Target")]
        public ShootingTarget attachedTarget;

        Vector3 startPosition;
        Vector3 endPosition;
        float stateTimer;
        bool movingToEnd = true;
        bool isPausing;

        void Start()
        {
            startPosition = transform.position;
            endPosition = startPosition + railOffset;
            if (attachedTarget == null)
            {
                attachedTarget = GetComponentInChildren<ShootingTarget>();
            }
        }

        void Update()
        {
            float dt = Time.deltaTime;
            if (dt <= 0f) return;

            stateTimer += dt;

            if (isPausing)
            {
                if (stateTimer >= pauseDuration)
                {
                    isPausing = false;
                    stateTimer = 0f;
                    movingToEnd = !movingToEnd;
                }
                return;
            }

            // Sinusoidal smooth motion
            float u = Mathf.Clamp01(stateTimer / Mathf.Max(0.01f, travelDuration));
            // S-curve: 0.5 * (1 - cos(pi * u)) yields true sinusoidal velocity v(t) ~ sin(pi * u)
            float s = 0.5f * (1f - Mathf.Cos(Mathf.PI * u));

            Vector3 from = movingToEnd ? startPosition : endPosition;
            Vector3 to = movingToEnd ? endPosition : startPosition;
            transform.position = Vector3.Lerp(from, to, s);

            if (u >= 1f)
            {
                isPausing = true;
                stateTimer = 0f;
            }
        }

        void OnDrawGizmosSelected()
        {
            Vector3 p0 = Application.isPlaying ? startPosition : transform.position;
            Vector3 p1 = p0 + railOffset;
            Gizmos.color = new Color(0f, 0.94f, 1f, 0.8f);
            Gizmos.DrawLine(p0, p1);
            Gizmos.DrawWireSphere(p0, 0.25f);
            Gizmos.DrawWireSphere(p1, 0.25f);
        }
    }
}
