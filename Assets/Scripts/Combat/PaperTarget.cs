using System;
using UnityEngine;

namespace ZeroProtocol.Combat
{
    /// <summary>
    /// Paper bullseye target sheet with dynamic perforated bullet hole decals,
    /// harmonic oscillator wobble physics, radial ring scoring (10/9/8/7/5 pts),
    /// and real-time extreme spread grouping computation in cm.
    /// Zero runtime GC allocations.
    /// </summary>
    public class PaperTarget : MonoBehaviour, IDamageable
    {
        [Header("Target Graphic & Dimensions")]
        public Renderer paperRenderer;
        public float sheetWidth = 0.55f;
        public float sheetHeight = 0.85f;

        [Header("Scoring Zone Radii (Meters)")]
        [Tooltip("Bullseye 10 pts radius (5cm)")]
        public float radius10 = 0.05f;
        [Tooltip("9-Ring 9 pts radius (10cm)")]
        public float radius9 = 0.10f;
        [Tooltip("8-Ring 8 pts radius (16cm)")]
        public float radius8 = 0.16f;
        [Tooltip("7-Ring 7 pts radius (22cm)")]
        public float radius7 = 0.22f;
        [Tooltip("Silhouette Torso half-width for 5 pts zone")]
        public float torsoHalfWidth = 0.26f;
        [Tooltip("Silhouette Torso half-height for 5 pts zone")]
        public float torsoHalfHeight = 0.42f;

        [Header("Harmonic Oscillator Wobble Physics")]
        public float omega = 22f;
        public float zeta = 0.32f;
        public float impactImpulse = 16f;

        [Header("Bullet Hole Decal Pool")]
        public int maxHoles = 64;
        public float holeDiameter = 0.018f;

        // Telemetry Properties
        public int ShotCount { get; private set; }
        public int TotalScore { get; private set; }
        public int LastScore { get; private set; }
        public float ExtremeSpreadCm { get; private set; }
        public float MeanRadiusCm { get; private set; }
        public bool IsAlive => true;
        public int RecordedShotCount => Mathf.Min(ShotCount, hitCoordinates.Length);

        public Vector2 GetHitCoordinate(int index)
        {
            if (index >= 0 && index < RecordedShotCount)
                return hitCoordinates[index];
            return Vector2.zero;
        }

        // Events
        public event Action<PaperTarget, Vector2, int> OnTargetHit;
        public event Action<PaperTarget> OnPaperRefreshed;

        // Pre-allocated buffers (Zero GC)
        readonly Vector2[] hitCoordinates = new Vector2[128];
        GameObject[] holeDecalPool;
        int activeHoleCount;
        Transform decalRoot;
        Material sharedHoleMat;

        Quaternion baseLocalRotation;
        float currentTilt;
        float tiltVelocity;
        Vector3 tiltAxis = Vector3.right;

        void Awake()
        {
            baseLocalRotation = transform.localRotation;
            if (paperRenderer == null) paperRenderer = GetComponent<Renderer>();
            if (paperRenderer == null) paperRenderer = GetComponentInChildren<Renderer>();

            InitializeHoleDecalPool();
        }

        void OnDestroy()
        {
            if (sharedHoleMat != null) Destroy(sharedHoleMat);
        }

        void Update()
        {
            float dt = Time.deltaTime;
            if (dt <= 0f && Application.isPlaying) return;
            if (dt <= 0f) dt = 0.016f;

            // Harmonic oscillator simulation: d2theta/dt2 + 2*zeta*omega*dtheta/dt + omega^2*theta = 0
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
        }

        public void TakeDamage(DamageInfo info)
        {
            // Convert world hit point into exact metric local target sheet coordinates (meters)
            // Using normalized basis vectors ensures isotropic metric coordinates regardless of transform scaling
            Vector3 worldOffset = info.hitPoint - transform.position;
            float localX = Vector3.Dot(worldOffset, transform.right);
            float localY = Vector3.Dot(worldOffset, transform.up);
            Vector2 hitCoord = new Vector2(localX, localY);

            int score = CalculateScore(hitCoord);

            // Record shot telemetry into pre-allocated circular buffer (Zero GC)
            int index = ShotCount % hitCoordinates.Length;
            hitCoordinates[index] = hitCoord;
            ShotCount++;
            TotalScore += score;
            LastScore = score;

            ComputeGrouping();

            // Spawn dynamic bullet hole decal
            SpawnHoleDecal(hitCoord);

            // Wobble impulse
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
            tiltVelocity += impactImpulse;

            OnTargetHit?.Invoke(this, hitCoord, score);
        }

        public int CalculateScore(Vector2 coord)
        {
            float r = coord.magnitude;

            if (r <= radius10) return 10;
            if (r <= radius9) return 9;
            if (r <= radius8) return 8;
            if (r <= radius7) return 7;

            // Outer silhouette torso
            if (Mathf.Abs(coord.x) <= torsoHalfWidth && Mathf.Abs(coord.y) <= torsoHalfHeight)
            {
                return 5;
            }

            return 0; // Miss or paper frame
        }

        public void FreshPaper()
        {
            // Recycle all active hole decals
            for (int i = 0; i < activeHoleCount; i++)
            {
                if (holeDecalPool[i] != null)
                {
                    holeDecalPool[i].SetActive(false);
                }
            }
            activeHoleCount = 0;

            ShotCount = 0;
            TotalScore = 0;
            LastScore = 0;
            ExtremeSpreadCm = 0f;
            MeanRadiusCm = 0f;
            currentTilt = 0f;
            tiltVelocity = 0f;

            OnPaperRefreshed?.Invoke(this);
        }

        void ComputeGrouping()
        {
            int n = Mathf.Min(ShotCount, hitCoordinates.Length);
            if (n < 2)
            {
                ExtremeSpreadCm = 0f;
                MeanRadiusCm = (n == 1) ? hitCoordinates[0].magnitude * 100f : 0f;
                return;
            }

            float maxDistSq = 0f;
            float sumRadius = 0f;

            for (int i = 0; i < n; i++)
            {
                sumRadius += hitCoordinates[i].magnitude;

                for (int j = i + 1; j < n; j++)
                {
                    float dSq = (hitCoordinates[i] - hitCoordinates[j]).sqrMagnitude;
                    if (dSq > maxDistSq)
                    {
                        maxDistSq = dSq;
                    }
                }
            }

            ExtremeSpreadCm = Mathf.Sqrt(maxDistSq) * 100f; // meters to cm
            MeanRadiusCm = (sumRadius / n) * 100f;
        }

        void SpawnHoleDecal(Vector2 hitCoord)
        {
            if (holeDecalPool == null || holeDecalPool.Length == 0) return;

            int holeIndex;
            if (activeHoleCount < holeDecalPool.Length)
            {
                holeIndex = activeHoleCount++;
            }
            else
            {
                // Recycle oldest
                holeIndex = (activeHoleCount - 1) % holeDecalPool.Length;
            }

            GameObject hole = holeDecalPool[holeIndex];
            if (hole != null)
            {
                // Position decal slightly in front of front face (-Z local in true meters) to prevent z-fighting
                hole.transform.localPosition = new Vector3(hitCoord.x, hitCoord.y, -0.012f);
                hole.transform.localRotation = Quaternion.Euler(0f, 0f, UnityEngine.Random.Range(0f, 360f));
                hole.SetActive(true);
            }
        }

        void InitializeHoleDecalPool()
        {
            GameObject root = new GameObject("_PaperTarget_DecalRoot");
            decalRoot = root.transform;
            decalRoot.SetParent(transform, false);

            // Counteract parent non-uniform scaling to ensure decals remain perfectly circular without shearing
            Vector3 s = transform.localScale;
            decalRoot.localScale = new Vector3(
                Mathf.Abs(s.x) > 0.0001f ? 1f / s.x : 1f,
                Mathf.Abs(s.y) > 0.0001f ? 1f / s.y : 1f,
                Mathf.Abs(s.z) > 0.0001f ? 1f / s.z : 1f
            );

            Shader unlit = Shader.Find("Universal Render Pipeline/Unlit");
            if (unlit == null) unlit = Shader.Find("Sprites/Default");

            sharedHoleMat = new Material(unlit);
            sharedHoleMat.name = "BulletHoleDecal_Mat";
            Color burntDark = new Color(0.04f, 0.04f, 0.05f, 1f);
            sharedHoleMat.SetColor("_BaseColor", burntDark);
            sharedHoleMat.SetColor("_Color", burntDark);

            holeDecalPool = new GameObject[maxHoles];
            for (int i = 0; i < maxHoles; i++)
            {
                GameObject holeGo = GameObject.CreatePrimitive(PrimitiveType.Quad);
                holeGo.name = $"Hole_{i}";
                holeGo.transform.SetParent(decalRoot, false);
                holeGo.transform.localScale = new Vector3(holeDiameter, holeDiameter, holeDiameter);

                Collider col = holeGo.GetComponent<Collider>();
                if (col != null) DestroyImmediate(col);

                Renderer rend = holeGo.GetComponent<Renderer>();
                rend.sharedMaterial = sharedHoleMat;
                rend.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                rend.receiveShadows = false;

                holeGo.SetActive(false);
                holeDecalPool[i] = holeGo;
            }
        }
    }
}
