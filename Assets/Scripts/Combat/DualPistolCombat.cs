using System;
using UnityEngine;
using ZeroProtocol.Player;

namespace ZeroProtocol.Combat
{
    public struct FireEventData
    {
        public HandSide Hand;
        public Vector3 MuzzlePosition;
        public Vector3 FireDirection;
        public Vector3 HitPoint;
        public Vector3 HitNormal;
        public bool DidHit;
        public HitType HitType;
    }

    public struct HitFeedbackData
    {
        public HitType HitType;
        public bool IsKill;
        public Vector3 HitPoint;
        public float Damage;
    }

    /// <summary>
    /// Commercial-grade Gun-Fu dual pistol combat system.
    /// Strictly decoupled architecture: communicates via C# events only.
    /// Zero direct references to UI or visual systems. Zero runtime GC allocations.
    /// </summary>
    public class DualPistolCombat : MonoBehaviour
    {
        [Header("Muzzle Sockets (Logical Transforms)")]
        [Tooltip("Transform representing the left pistol muzzle socket")]
        public Transform muzzleLeft;
        [Tooltip("Transform representing the right pistol muzzle socket")]
        public Transform muzzleRight;

        [Header("Dual Cadence & Ballistics")]
        [Tooltip("Interval between alternating shots in seconds (e.g. 0.12s = 500 RPM)")]
        public float fireInterval = 0.12f;
        public float maxRange = 120f;
        public LayerMask hitLayers = ~0;
        public float bodyDamage = 25f;
        public float headshotDamage = 75f;

        [Header("Ammunition & Reloading")]
        public int maxAmmoPerMag = 15;
        public float reloadDuration = 1.25f;

        [Header("Aim Assist Tier 2: Bullet Magnetism")]
        [Tooltip("Hipfire maximum cone angle for body magnetism targeting (degrees)")]
        public float magnetismMaxConeAngle = 2.5f;
        [Tooltip("Hipfire prioritized head hitbox cone angle (degrees)")]
        public float magnetismHeadConeAngle = 1.2f;
        [Tooltip("Hipfire trajectory bending weight toward target")]
        [Range(0f, 1f)]
        public float magnetismWeight = 0.40f;

        [Header("Aim Assist Tier 2: ADS Bullet Magnetism")]
        [Tooltip("ADS maximum cone angle for body magnetism targeting (degrees)")]
        public float magnetismAdsMaxConeAngle = 3.8f;
        [Tooltip("ADS prioritized head hitbox cone angle (degrees)")]
        public float magnetismAdsHeadConeAngle = 2.0f;
        [Tooltip("ADS trajectory bending weight toward target")]
        [Range(0f, 1f)]
        public float magnetismAdsWeight = 0.55f;

        [Header("Dynamic Bloom")]
        public float thetaBase = 0.9f;
        public float deltaBloom = 0.45f;
        public float thetaMove = 1.8f;
        public float thetaMin = 0.5f;
        public float thetaMax = 5.0f;
        public float mAds = 0.4f;
        public float bloomRecoverySpeed = 5.5f;
        public float referenceRunSpeed = 5.0f;

        [Header("Input & Camera")]
        public GameInput input;
        public Camera mainCamera;

        // Decoupled Events / Delegates
        public event Action<FireEventData> OnWeaponFired;
        public event Action<int, int, int> OnAmmoChanged; // (ammoLeft, ammoRight, maxAmmoPerMag)
        public event Action<float> OnReloadStarted;       // (reloadDuration)
        public event Action OnReloadCompleted;
        public event Action<bool> OnAimStateChanged;      // (isAiming)
        public event Action<HitFeedbackData> OnHitFeedback;
        public event Action<float> OnBloomChanged;        // (currentSpreadAngle)

        // State
        public int AmmoLeft { get; private set; }
        public int AmmoRight { get; private set; }
        public bool IsReloading { get; private set; }
        public bool IsAiming { get; private set; }
        public float CurrentBloomAngle { get; private set; }

        HandSide nextHand = HandSide.Left;
        float nextFireTime;
        float reloadTimer;
        float shotHeat;
        YoruController playerController;

        // Pre-allocated collision query buffers for Zero GC
        readonly RaycastHit[] camHits = new RaycastHit[16];
        readonly RaycastHit[] muzzleHits = new RaycastHit[16];
        readonly RaycastHit[] losHits = new RaycastHit[8];

        void Awake()
        {
            AmmoLeft = maxAmmoPerMag;
            AmmoRight = maxAmmoPerMag;
            CurrentBloomAngle = thetaBase;

            if (input == null) input = GetComponent<GameInput>();
            playerController = GetComponent<YoruController>();
            if (mainCamera == null) mainCamera = Camera.main;

            EnsureMuzzleSockets();
        }

        void Start()
        {
            OnAmmoChanged?.Invoke(AmmoLeft, AmmoRight, maxAmmoPerMag);
            OnBloomChanged?.Invoke(CurrentBloomAngle);
        }

        void Update()
        {
            float dt = Time.deltaTime;
            if (dt <= 0f && Application.isPlaying) return;
            if (dt <= 0f) dt = 0.016f;

            // Handle ADS aiming state
            bool aimInput = input != null && input.AimHeld;
            if (aimInput != IsAiming)
            {
                IsAiming = aimInput;
                OnAimStateChanged?.Invoke(IsAiming);
            }

            // Handle Reload
            if (IsReloading)
            {
                reloadTimer += dt;
                if (reloadTimer >= reloadDuration)
                {
                    CompleteReload();
                }
            }
            else if (input != null && input.ReloadPressed)
            {
                if (AmmoLeft < maxAmmoPerMag || AmmoRight < maxAmmoPerMag)
                {
                    StartReload();
                }
            }

            // Handle Bloom Decay
            if (shotHeat > 0f)
            {
                shotHeat = Mathf.Max(0f, shotHeat - bloomRecoverySpeed * dt);
            }

            float currentSpeed = playerController != null ? playerController.HorizontalSpeed : 0f;
            float speedRatio = Mathf.Clamp01(currentSpeed / Mathf.Max(0.1f, referenceRunSpeed));
            float rawSpread = thetaBase + (shotHeat * deltaBloom) + (speedRatio * thetaMove);
            CurrentBloomAngle = Mathf.Clamp(rawSpread, thetaMin, thetaMax) * (IsAiming ? mAds : 1f);
            OnBloomChanged?.Invoke(CurrentBloomAngle);

            // Handle Firing Input
            if (input != null && (input.FireHeld || input.FirePressed))
            {
                if (!IsReloading && (Time.time >= nextFireTime || !Application.isPlaying))
                {
                    TryFireNextShot();
                }
            }
        }

        void TryFireNextShot()
        {
            // Determine active hand
            HandSide firingHand = nextHand;

            // Check if firing hand has ammo
            if (firingHand == HandSide.Left && AmmoLeft <= 0)
            {
                if (AmmoRight > 0) firingHand = HandSide.Right;
                else
                {
                    StartReload();
                    return;
                }
            }
            else if (firingHand == HandSide.Right && AmmoRight <= 0)
            {
                if (AmmoLeft > 0) firingHand = HandSide.Left;
                else
                {
                    StartReload();
                    return;
                }
            }

            // Execute shot
            ExecuteShot(firingHand);

            // Decrement ammo
            if (firingHand == HandSide.Left) AmmoLeft--;
            else AmmoRight--;

            OnAmmoChanged?.Invoke(AmmoLeft, AmmoRight, maxAmmoPerMag);

            // Step cadence
            nextHand = (firingHand == HandSide.Left) ? HandSide.Right : HandSide.Left;
            nextFireTime = Time.time + fireInterval;
            shotHeat += 1f;

            // If completely dry after shot, auto start reload
            if (AmmoLeft <= 0 && AmmoRight <= 0)
            {
                StartReload();
            }
        }

        void ExecuteShot(HandSide hand)
        {
            Transform socket = (hand == HandSide.Left) ? muzzleLeft : muzzleRight;
            Vector3 muzzlePos = socket != null ? socket.position : transform.position + Vector3.up * 1.15f;

            // 1. Center-screen camera ray determines aim point P_aim
            Vector3 pAim = GetCenterCameraAimPoint(muzzlePos);

            // 2. Line of sight from muzzle to aim point & Parallax handling
            Vector3 toAim = pAim - muzzlePos;
            float aimDist = toAim.magnitude;
            Vector3 camForward = (mainCamera != null) ? mainCamera.transform.forward : transform.forward;

            // Parallax check: if aim point is behind or planar to muzzle, fall back to camera forward
            Vector3 aimDir;
            if (aimDist <= 0.001f || Vector3.Dot(toAim, camForward) <= 0.05f)
            {
                aimDir = camForward;
                aimDist = maxRange;
            }
            else
            {
                aimDir = toAim / aimDist;
            }

            // Line-of-sight verification from active muzzle socket P_muzzle to P_aim via Physics.RaycastNonAlloc
            int losCheckCount = Physics.RaycastNonAlloc(muzzlePos, aimDir, losHits, aimDist, hitLayers, QueryTriggerInteraction.Ignore);
            for (int i = 0; i < losCheckCount; i++)
            {
                RaycastHit lh = losHits[i];
                if (lh.collider == null || lh.transform.IsChildOf(transform)) continue;
                if (lh.distance < aimDist - 0.05f)
                {
                    // Intervening obstruction verified: trajectory is truncated to obstacle
                    aimDist = lh.distance;
                    break;
                }
            }

            // 3. Aim Assist Tier 2: Bullet Magnetism Cone Solver (with line of sight check)
            Vector3 magnetizedDir = ApplyBulletMagnetism(muzzlePos, aimDir);

            // 4. Dynamic Bloom dispersion
            Vector3 finalFireDir = ApplyBloom(magnetizedDir, CurrentBloomAngle);

            // 5. Physics query from muzzle along finalFireDir (Zero GC RaycastNonAlloc)
            int hitCount = Physics.RaycastNonAlloc(muzzlePos, finalFireDir, muzzleHits, maxRange, hitLayers, QueryTriggerInteraction.Ignore);

            RaycastHit closestValidHit = default;
            float closestDist = float.MaxValue;
            bool didHit = false;

            for (int i = 0; i < hitCount; i++)
            {
                RaycastHit hit = muzzleHits[i];
                if (hit.collider == null) continue;
                // Exclude self/player colliders
                if (hit.transform.IsChildOf(transform)) continue;

                if (hit.distance < closestDist)
                {
                    closestDist = hit.distance;
                    closestValidHit = hit;
                    didHit = true;
                }
            }

            Vector3 hitPoint = didHit ? closestValidHit.point : muzzlePos + finalFireDir * maxRange;
            Vector3 hitNormal = didHit ? closestValidHit.normal : -finalFireDir;
            HitType hitType = HitType.Body;

            if (didHit)
            {
                IDamageable damageable = closestValidHit.collider.GetComponentInParent<IDamageable>();
                TargetHitbox hitbox = closestValidHit.collider.GetComponent<TargetHitbox>();

                if (hitbox != null)
                {
                    hitType = hitbox.hitboxType;
                }
                else
                {
                    // Fallback headshot height check if hitting a dummy directly
                    ShootingTarget st = closestValidHit.collider.GetComponentInParent<ShootingTarget>();
                    if (st != null && hitPoint.y >= st.HeadPosition.y - 0.22f)
                    {
                        hitType = HitType.Headshot;
                    }
                }

                float damage = (hitType == HitType.Headshot) ? headshotDamage : bodyDamage;
                bool wasAlive = damageable != null && damageable.IsAlive;

                if (damageable != null && wasAlive)
                {
                    DamageInfo dInfo = new DamageInfo(damage, hitPoint, hitNormal, finalFireDir, hitType, hand, gameObject);
                    damageable.TakeDamage(dInfo);

                    bool isKill = !damageable.IsAlive;
                    OnHitFeedback?.Invoke(new HitFeedbackData
                    {
                        HitType = hitType,
                        IsKill = isKill,
                        HitPoint = hitPoint,
                        Damage = damage
                    });
                }
            }

            // Emit fire event for decoupled VFX, Audio, Camera recoil, HUD
            OnWeaponFired?.Invoke(new FireEventData
            {
                Hand = hand,
                MuzzlePosition = muzzlePos,
                FireDirection = finalFireDir,
                HitPoint = hitPoint,
                HitNormal = hitNormal,
                DidHit = didHit,
                HitType = hitType
            });
        }

        Vector3 GetCenterCameraAimPoint(Vector3 muzzlePos)
        {
            if (mainCamera == null)
            {
                mainCamera = Camera.main;
                if (mainCamera == null) return muzzlePos + transform.forward * maxRange;
            }

            Ray centerRay = mainCamera.ViewportPointToRay(new Vector3(0.5f, 0.5f, 0f));
            int hitCount = Physics.RaycastNonAlloc(centerRay, camHits, maxRange, hitLayers, QueryTriggerInteraction.Ignore);

            float nearest = float.MaxValue;
            Vector3 aimPoint = centerRay.origin + centerRay.direction * maxRange;

            for (int i = 0; i < hitCount; i++)
            {
                RaycastHit h = camHits[i];
                if (h.collider == null) continue;
                if (h.transform.IsChildOf(transform)) continue;

                if (h.distance < nearest)
                {
                    nearest = h.distance;
                    aimPoint = h.point;
                }
            }

            return aimPoint;
        }

        bool HasLineOfSight(Vector3 from, Vector3 to, Transform targetTransform)
        {
            Vector3 diff = to - from;
            float dist = diff.magnitude;
            if (dist <= 0.05f) return true;
            Vector3 dir = diff / dist;

            int count = Physics.RaycastNonAlloc(from, dir, losHits, dist, hitLayers, QueryTriggerInteraction.Ignore);
            for (int i = 0; i < count; i++)
            {
                RaycastHit h = losHits[i];
                if (h.collider == null || h.transform.IsChildOf(transform)) continue;
                if (targetTransform != null && (h.transform == targetTransform || h.transform.IsChildOf(targetTransform))) continue;
                if (h.distance < dist - 0.05f)
                {
                    // Blocked by opaque geometry
                    return false;
                }
            }
            return true;
        }

        Vector3 ApplyBulletMagnetism(Vector3 muzzlePos, Vector3 aimDir)
        {
            var targets = ShootingTarget.ActiveTargets;
            if (targets == null || targets.Count == 0) return aimDir;

            float activeHeadCone = IsAiming ? magnetismAdsHeadConeAngle : magnetismHeadConeAngle;
            float activeBodyCone = IsAiming ? magnetismAdsMaxConeAngle : magnetismMaxConeAngle;
            float activeWeight = IsAiming ? magnetismAdsWeight : magnetismWeight;

            Vector3 bestTargetPos = Vector3.zero;
            float bestHeadAngle = float.MaxValue;
            float bestBodyAngle = float.MaxValue;
            bool foundHead = false;
            bool foundBody = false;

            for (int i = 0; i < targets.Count; i++)
            {
                ShootingTarget t = targets[i];
                if (t == null || !t.IsAlive) continue;

                // Test Head angle
                Vector3 toHead = t.HeadPosition - muzzlePos;
                float distHead = toHead.magnitude;
                if (distHead > 0.01f && distHead <= maxRange)
                {
                    float angleHead = Vector3.Angle(aimDir, toHead / distHead);
                    if (angleHead <= activeHeadCone && angleHead < bestHeadAngle)
                    {
                        if (HasLineOfSight(muzzlePos, t.HeadPosition, t.transform))
                        {
                            bestHeadAngle = angleHead;
                            bestTargetPos = t.HeadPosition;
                            foundHead = true;
                        }
                    }
                }

                // Test Body angle if head not already satisfied
                if (!foundHead)
                {
                    Vector3 toBody = t.BodyPosition - muzzlePos;
                    float distBody = toBody.magnitude;
                    if (distBody > 0.01f && distBody <= maxRange)
                    {
                        float angleBody = Vector3.Angle(aimDir, toBody / distBody);
                        if (angleBody <= activeBodyCone && angleBody < bestBodyAngle)
                        {
                            if (HasLineOfSight(muzzlePos, t.BodyPosition, t.transform))
                            {
                                bestBodyAngle = angleBody;
                                bestTargetPos = t.BodyPosition;
                                foundBody = true;
                            }
                        }
                    }
                }
            }

            if (foundHead || foundBody)
            {
                Vector3 dirToTarget = (bestTargetPos - muzzlePos).normalized;
                return Vector3.Slerp(aimDir, dirToTarget, activeWeight);
            }

            return aimDir;
        }

        Vector3 ApplyBloom(Vector3 forward, float spreadAngleDeg)
        {
            if (spreadAngleDeg <= 0.001f) return forward;

            float randomRoll = UnityEngine.Random.Range(0f, 360f);
            float randomPitch = UnityEngine.Random.Range(0f, spreadAngleDeg);

            Vector3 right = Vector3.Cross(forward, Vector3.up);
            if (right.sqrMagnitude < 0.001f) right = Vector3.Cross(forward, Vector3.right);
            right.Normalize();

            Quaternion rollRot = Quaternion.AngleAxis(randomRoll, forward);
            Vector3 pitchAxis = rollRot * right;
            Quaternion pitchRot = Quaternion.AngleAxis(randomPitch, pitchAxis);

            return (pitchRot * forward).normalized;
        }

        void StartReload()
        {
            if (IsReloading) return;
            IsReloading = true;
            reloadTimer = 0f;
            OnReloadStarted?.Invoke(reloadDuration);
        }

        void CompleteReload()
        {
            IsReloading = false;
            reloadTimer = 0f;
            AmmoLeft = maxAmmoPerMag;
            AmmoRight = maxAmmoPerMag;
            OnReloadCompleted?.Invoke();
            OnAmmoChanged?.Invoke(AmmoLeft, AmmoRight, maxAmmoPerMag);
        }

        public void ResupplyAmmo()
        {
            AmmoLeft = maxAmmoPerMag;
            AmmoRight = maxAmmoPerMag;
            IsReloading = false;
            reloadTimer = 0f;
            shotHeat = 0f;
            OnAmmoChanged?.Invoke(AmmoLeft, AmmoRight, maxAmmoPerMag);
        }

        public void EnsureMuzzleSockets()
        {
            Transform socketsRoot = transform.Find("Sockets");
            if (socketsRoot == null)
            {
                GameObject rootGo = new GameObject("Sockets");
                rootGo.transform.SetParent(transform, false);
                socketsRoot = rootGo.transform;
            }

            if (muzzleLeft == null)
            {
                Transform left = socketsRoot.Find("Muzzle_L");
                if (left == null)
                {
                    GameObject go = new GameObject("Muzzle_L");
                    go.transform.SetParent(socketsRoot, false);
                    go.transform.localPosition = new Vector3(-0.25f, 1.15f, 0.45f);
                    left = go.transform;
                }
                muzzleLeft = left;
            }

            if (muzzleRight == null)
            {
                Transform right = socketsRoot.Find("Muzzle_R");
                if (right == null)
                {
                    GameObject go = new GameObject("Muzzle_R");
                    go.transform.SetParent(socketsRoot, false);
                    go.transform.localPosition = new Vector3(0.25f, 1.15f, 0.45f);
                    right = go.transform;
                }
                muzzleRight = right;
            }
        }
    }
}
