using System.Collections.Generic;
using UnityEngine;

namespace ZeroProtocol.Combat
{
    /// <summary>
    /// Hitbox proxy component placed on child colliders (Head, Body) to route damage
    /// and report distinct hit types to the parent ShootingTarget.
    /// </summary>
    public class TargetHitbox : MonoBehaviour, IDamageable
    {
        public ShootingTarget parentTarget;
        public HitType hitboxType = HitType.Body;

        public bool IsAlive => parentTarget != null && parentTarget.IsAlive;

        public void TakeDamage(DamageInfo info)
        {
            if (parentTarget != null)
            {
                info.hitType = hitboxType;
                parentTarget.TakeDamage(info);
            }
        }
    }

    /// <summary>
    /// Reactive combat target dummy with underdamped harmonic oscillator tilt physics,
    /// MaterialPropertyBlock hit flashes (zero GC allocations), and automatic respawn.
    /// </summary>
    public class ShootingTarget : MonoBehaviour, IDamageable
    {
        public static readonly List<ShootingTarget> ActiveTargets = new List<ShootingTarget>();

        [Header("Health & Combat")]
        public float maxHealth = 100f;
        public float respawnDelay = 2.0f;

        [Header("Harmonic Oscillator Physics")]
        [Tooltip("Natural frequency (rad/s). Specification: omega = 25 rad/s")]
        public float omega = 25f;
        [Tooltip("Damping ratio. Specification: zeta = 0.35 (underdamped harmonic wobble)")]
        public float zeta = 0.35f;
        public float bodyImpactImpulse = 14f;
        public float headImpactImpulse = 24f;

        [Header("Hitbox Anchors")]
        public Transform headTransform;
        public Transform bodyTransform;

        [Header("Visuals & Colors")]
        public Renderer targetRenderer;
        public Renderer headRenderer;
        public float flashDuration = 0.22f;

        // Cyberpunk Palette from specification
        public static readonly Color ColorIdle = new Color(0.169f, 0.176f, 0.259f, 1f);       // #2B2D42
        public static readonly Color ColorBodyFlash = new Color(0.937f, 0.137f, 0.235f, 1f);   // #EF233C
        public static readonly Color ColorHeadshot = new Color(1.0f, 0.745f, 0.043f, 1f);      // #FFBE0B
        public static readonly Color ColorHover = new Color(1.0f, 0.200f, 0.400f, 1f);         // #FF3366
        public static readonly Color ColorKillMarker = new Color(1.0f, 0.0f, 0.267f, 1f);      // #FF0044

        static readonly int BaseColorId = Shader.PropertyToID("_BaseColor");
        static readonly int ColorId = Shader.PropertyToID("_Color");

        public bool IsAlive { get; protected set; } = true;
        public float CurrentHealth { get; protected set; } = 100f;

        public Vector3 HeadPosition => headTransform != null ? headTransform.position : transform.position + Vector3.up * 1.6f;
        public Vector3 BodyPosition => bodyTransform != null ? bodyTransform.position : transform.position + Vector3.up * 0.9f;

        protected Quaternion baseLocalRotation;
        protected float currentTilt;
        protected float tiltVelocity;
        protected Vector3 tiltAxis = Vector3.right;

        protected MaterialPropertyBlock propBlock;
        protected Color currentFlashColor = ColorIdle;
        protected float flashTimer;
        protected bool isHovered;
        protected float deathTimer;

        protected virtual void Awake()
        {
            propBlock = new MaterialPropertyBlock();
            baseLocalRotation = transform.localRotation;
            CurrentHealth = maxHealth;

            if (targetRenderer == null) targetRenderer = GetComponent<Renderer>();
            ApplyColor(ColorIdle);
        }

        void OnEnable()
        {
            if (!ActiveTargets.Contains(this))
            {
                ActiveTargets.Add(this);
            }
        }

        void OnDisable()
        {
            ActiveTargets.Remove(this);
        }

        protected virtual void Update()
        {
            float dt = Time.deltaTime;
            if (dt <= 0f && Application.isPlaying) return;
            if (dt <= 0f) dt = 0.016f;

            // Handle death and respawn
            if (!IsAlive)
            {
                deathTimer += dt;
                // Animate falling back along bullet impact axis (positive tilt knocks away from impact)
                currentTilt = Mathf.Lerp(currentTilt, 85f, 1f - Mathf.Exp(-12f * dt));
                transform.localRotation = baseLocalRotation * Quaternion.AngleAxis(currentTilt, tiltAxis);

                if (deathTimer >= respawnDelay)
                {
                    Respawn();
                }
                return;
            }

            // Harmonic oscillator simulation: d2theta/dt2 + 2*zeta*omega*dtheta/dt + omega^2*theta = 0
            // Substep dt to guarantee stability under sub-60 FPS delta spikes (max sub-step 0.02s)
            float simTime = dt;
            while (simTime > 0f)
            {
                float step = Mathf.Min(simTime, 0.02f);
                float accel = -2f * zeta * omega * tiltVelocity - (omega * omega) * currentTilt;
                tiltVelocity += accel * step;
                currentTilt += tiltVelocity * step;
                simTime -= step;
            }

            transform.localRotation = baseLocalRotation * Quaternion.AngleAxis(currentTilt, tiltAxis);

            // Hit flash color fade
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

            // Reset hover state every frame (re-asserted by aim assist)
            isHovered = false;
        }

        public virtual void TakeDamage(DamageInfo info)
        {
            if (!IsAlive) return;

            CurrentHealth -= info.damage;

            // Calculate tilt axis perpendicular to incoming shot direction
            Vector3 localHitDir = transform.InverseTransformDirection(info.hitDirection);
            localHitDir.y = 0f;
            if (localHitDir.sqrMagnitude > 0.01f)
            {
                tiltAxis = Vector3.Cross(Vector3.up, localHitDir.normalized);
            }
            else
            {
                tiltAxis = Vector3.right;
            }

            float impulse = (info.hitType == HitType.Headshot) ? headImpactImpulse : bodyImpactImpulse;
            tiltVelocity += impulse;

            // Trigger flash color
            currentFlashColor = (info.hitType == HitType.Headshot) ? ColorHeadshot : ColorBodyFlash;
            flashTimer = flashDuration;

            if (CurrentHealth <= 0f)
            {
                Die();
            }
        }

        public void SetHovered(bool hovered)
        {
            if (!IsAlive) return;
            isHovered = hovered;
        }

        protected virtual void Die()
        {
            IsAlive = false;
            CurrentHealth = 0f;
            deathTimer = 0f;
            tiltVelocity = 0f;
            currentFlashColor = ColorKillMarker;
            flashTimer = flashDuration;
        }

        protected virtual void Respawn()
        {
            IsAlive = true;
            CurrentHealth = maxHealth;
            deathTimer = 0f;
            currentTilt = 0f;
            tiltVelocity = 12f; // Pop-up spring wobble
            tiltAxis = Vector3.right;
            flashTimer = 0.3f;
            currentFlashColor = ColorHeadshot;
        }

        protected virtual void ApplyColor(Color col)
        {
            if (propBlock == null) propBlock = new MaterialPropertyBlock();
            propBlock.SetColor(BaseColorId, col);
            propBlock.SetColor(ColorId, col);

            if (targetRenderer != null)
            {
                targetRenderer.SetPropertyBlock(propBlock);
            }
            if (headRenderer != null)
            {
                headRenderer.SetPropertyBlock(propBlock);
            }
        }
    }
}
