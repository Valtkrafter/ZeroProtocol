using UnityEngine;

namespace ZeroProtocol.Combat
{
    /// <summary>
    /// Steel popper target for Lane 3 (30m).
    /// Heavy circular steel plate on a motorized hinge base.
    /// When HP reaches 0, drops down flat 90 degrees with metallic reaction.
    /// Automatically springs back upright after 2.5 seconds with an elastic pop-up.
    /// </summary>
    public class PopperTarget : ShootingTarget
    {
        [Header("Popper Target Hinge Configuration")]
        [Tooltip("Angle in degrees the steel plate drops back when knocked down (Specification: 90 degrees)")]
        public float dropAngle = 90f;

        [Tooltip("Speed multiplier for the knockdown drop animation")]
        public float dropSpeed = 16f;

        [Tooltip("Elastic spring velocity when popping back up")]
        public float springUpImpulse = 20f;

        protected override void Awake()
        {
            base.Awake();
            respawnDelay = 2.5f;
            omega = 28f;
            zeta = 0.40f;
        }

        protected override void Update()
        {
            float dt = Time.deltaTime;
            if (dt <= 0f && Application.isPlaying) return;
            if (dt <= 0f) dt = 0.016f;

            if (!IsAlive)
            {
                deathTimer += dt;
                // Hinges back flat 90 degrees
                currentTilt = Mathf.Lerp(currentTilt, dropAngle, 1f - Mathf.Exp(-dropSpeed * dt));
                transform.localRotation = baseLocalRotation * Quaternion.AngleAxis(currentTilt, Vector3.right);

                if (deathTimer >= respawnDelay)
                {
                    Respawn();
                }
                return;
            }

            // Alive: underdamped harmonic wobble around hinge base when struck
            float simTime = dt;
            while (simTime > 0f)
            {
                float step = Mathf.Min(simTime, 0.02f);
                float accel = -2f * zeta * omega * tiltVelocity - (omega * omega) * currentTilt;
                tiltVelocity += accel * step;
                currentTilt += tiltVelocity * step;
                simTime -= step;
            }

            transform.localRotation = baseLocalRotation * Quaternion.AngleAxis(currentTilt, Vector3.right);

            // Hit flash color
            if (flashTimer > 0f)
            {
                flashTimer -= dt;
                float t = Mathf.Clamp01(flashTimer / flashDuration);
                Color blended = Color.Lerp(isHovered ? ColorHover : ColorIdle, currentFlashColor, t);
                ApplyColor(blended);
            }
            else if (isHovered)
            {
                ApplyColor(ColorHover);
            }
            else
            {
                ApplyColor(ColorIdle);
            }

            isHovered = false;
        }

        protected override void Die()
        {
            base.Die();
            // Force drop along hinge X-axis
            tiltAxis = Vector3.right;
            tiltVelocity = 0f;
        }

        public override void ResetTarget()
        {
            Respawn();
        }

        protected override void Respawn()
        {
            IsAlive = true;
            CurrentHealth = maxHealth;
            deathTimer = 0f;
            currentTilt = 0f;
            tiltVelocity = springUpImpulse; // Elastic spring pop-up
            tiltAxis = Vector3.right;
            flashTimer = 0.35f;
            currentFlashColor = ColorHeadshot;
        }
    }
}
