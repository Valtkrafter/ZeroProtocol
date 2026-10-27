using System.Collections.Generic;
using UnityEngine;

namespace ZeroProtocol.Combat
{
    /// <summary>
    /// Object-pooled weapon visual effects (bullet tracers, impact sparks, muzzle lights/flashes).
    /// Subscribes to DualPistolCombat events. Zero runtime GC allocations.
    /// </summary>
    public class GunVFX : MonoBehaviour
    {
        public DualPistolCombat combat;

        [Header("Pool Sizes")]
        public int tracerPoolSize = 24;
        public int sparkPoolSize = 24;
        public int muzzleFlashPoolSize = 12;

        [Header("Tracer Settings")]
        public float tracerDuration = 0.05f;
        public float tracerStartWidth = 0.04f;
        public float tracerEndWidth = 0.015f;
        public Color tracerColor = new Color(0.2f, 0.9f, 1.0f, 1.0f); // Cyberpunk neon cyan

        [Header("Impact Settings")]
        public float sparkDuration = 0.25f;
        public Color sparkColor = new Color(1.0f, 0.65f, 0.2f, 1.0f); // Bright spark orange

        [Header("Muzzle Flash Settings")]
        public float flashDuration = 0.035f;
        public float lightRange = 3.5f;
        public float lightIntensity = 2.5f;
        public Color muzzleColor = new Color(0.3f, 0.85f, 1.0f, 1.0f);

        // Pre-allocated Pools (Queues)
        readonly Queue<TracerItem> tracerPool = new Queue<TracerItem>();
        readonly List<TracerItem> activeTracers = new List<TracerItem>();

        readonly Queue<SparkItem> sparkPool = new Queue<SparkItem>();
        readonly List<SparkItem> activeSparks = new List<SparkItem>();

        readonly Queue<FlashItem> flashPool = new Queue<FlashItem>();
        readonly List<FlashItem> activeFlashes = new List<FlashItem>();

        Transform poolRoot;
        Material sharedTracerMat;
        Material sharedSparkMat;

        class TracerItem
        {
            public GameObject go;
            public LineRenderer line;
            public float timer;
        }

        class SparkItem
        {
            public GameObject go;
            public ParticleSystem particles;
            public float timer;
        }

        class FlashItem
        {
            public GameObject go;
            public Light light;
            public float timer;
        }

        void Awake()
        {
            if (combat == null) combat = GetComponentInParent<DualPistolCombat>();
            if (combat == null) combat = FindFirstObjectByType<DualPistolCombat>();

            InitializeMaterials();
            CreatePoolHierarchy();
            PrewarmPools();
        }

        void OnEnable()
        {
            if (combat == null)
            {
                combat = GetComponentInParent<DualPistolCombat>();
                if (combat == null) combat = FindFirstObjectByType<DualPistolCombat>();
            }

            if (combat != null)
            {
                combat.OnWeaponFired -= HandleWeaponFired;
                combat.OnWeaponFired += HandleWeaponFired;
            }
        }

        void OnDisable()
        {
            if (combat != null)
            {
                combat.OnWeaponFired -= HandleWeaponFired;
            }
        }

        void OnDestroy()
        {
            if (combat != null)
            {
                combat.OnWeaponFired -= HandleWeaponFired;
            }

            if (sharedTracerMat != null) Destroy(sharedTracerMat);
            if (sharedSparkMat != null) Destroy(sharedSparkMat);
        }

        void Update()
        {
            float dt = Time.deltaTime;
            if (dt <= 0f) return;

            // Update active tracers
            for (int i = activeTracers.Count - 1; i >= 0; i--)
            {
                TracerItem t = activeTracers[i];
                t.timer -= dt;
                if (t.timer <= 0f)
                {
                    t.go.SetActive(false);
                    activeTracers.RemoveAt(i);
                    tracerPool.Enqueue(t);
                }
            }

            // Update active sparks
            for (int i = activeSparks.Count - 1; i >= 0; i--)
            {
                SparkItem s = activeSparks[i];
                s.timer -= dt;
                if (s.timer <= 0f)
                {
                    s.go.SetActive(false);
                    activeSparks.RemoveAt(i);
                    sparkPool.Enqueue(s);
                }
            }

            // Update active muzzle flashes
            for (int i = activeFlashes.Count - 1; i >= 0; i--)
            {
                FlashItem f = activeFlashes[i];
                f.timer -= dt;
                if (f.timer <= 0f)
                {
                    f.go.SetActive(false);
                    activeFlashes.RemoveAt(i);
                    flashPool.Enqueue(f);
                }
            }
        }

        void HandleWeaponFired(FireEventData fireData)
        {
            SpawnMuzzleFlash(fireData.MuzzlePosition);
            SpawnTracer(fireData.MuzzlePosition, fireData.HitPoint);

            if (fireData.DidHit)
            {
                SpawnImpactSparks(fireData.HitPoint, fireData.HitNormal);
            }
        }

        void SpawnTracer(Vector3 start, Vector3 end)
        {
            TracerItem item = null;
            if (tracerPool.Count > 0)
            {
                item = tracerPool.Dequeue();
            }
            else if (activeTracers.Count > 0)
            {
                // Steal oldest active
                item = activeTracers[0];
                activeTracers.RemoveAt(0);
            }

            if (item != null)
            {
                item.go.SetActive(true);
                item.line.SetPosition(0, start);
                item.line.SetPosition(1, end);
                item.timer = tracerDuration;
                activeTracers.Add(item);
            }
        }

        void SpawnImpactSparks(Vector3 hitPoint, Vector3 hitNormal)
        {
            SparkItem item = null;
            if (sparkPool.Count > 0)
            {
                item = sparkPool.Dequeue();
            }
            else if (activeSparks.Count > 0)
            {
                item = activeSparks[0];
                activeSparks.RemoveAt(0);
            }

            if (item != null)
            {
                item.go.transform.position = hitPoint + hitNormal * 0.02f;
                Vector3 upVec = Mathf.Abs(hitNormal.y) > 0.99f ? Vector3.forward : Vector3.up;
                item.go.transform.rotation = Quaternion.LookRotation(hitNormal, upVec);
                item.go.SetActive(true);
                item.particles.Clear();
                item.particles.Play();
                item.timer = sparkDuration;
                activeSparks.Add(item);
            }
        }

        void SpawnMuzzleFlash(Vector3 muzzlePos)
        {
            FlashItem item = null;
            if (flashPool.Count > 0)
            {
                item = flashPool.Dequeue();
            }
            else if (activeFlashes.Count > 0)
            {
                item = activeFlashes[0];
                activeFlashes.RemoveAt(0);
            }

            if (item != null)
            {
                item.go.transform.position = muzzlePos;
                item.go.SetActive(true);
                item.timer = flashDuration;
                activeFlashes.Add(item);
            }
        }

        void InitializeMaterials()
        {
            Shader unlit = Shader.Find("Universal Render Pipeline/Unlit");
            if (unlit == null) unlit = Shader.Find("Sprites/Default");

            sharedTracerMat = new Material(unlit);
            sharedTracerMat.SetColor("_BaseColor", tracerColor);
            sharedTracerMat.SetColor("_Color", tracerColor);

            sharedSparkMat = new Material(unlit);
            sharedSparkMat.SetColor("_BaseColor", sparkColor);
            sharedSparkMat.SetColor("_Color", sparkColor);
        }

        void CreatePoolHierarchy()
        {
            GameObject root = new GameObject("_GunVFX_PoolRoot");
            poolRoot = root.transform;
            poolRoot.SetParent(transform, false);
        }

        void PrewarmPools()
        {
            // Tracers
            for (int i = 0; i < tracerPoolSize; i++)
            {
                GameObject go = new GameObject($"Tracer_{i}");
                go.transform.SetParent(poolRoot, false);
                LineRenderer lr = go.AddComponent<LineRenderer>();
                lr.sharedMaterial = sharedTracerMat;
                lr.startWidth = tracerStartWidth;
                lr.endWidth = tracerEndWidth;
                lr.positionCount = 2;
                lr.useWorldSpace = true;
                lr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                lr.receiveShadows = false;
                lr.startColor = tracerColor;
                lr.endColor = tracerColor;
                go.SetActive(false);

                tracerPool.Enqueue(new TracerItem { go = go, line = lr });
            }

            // Sparks
            for (int i = 0; i < sparkPoolSize; i++)
            {
                GameObject go = new GameObject($"Spark_{i}");
                go.transform.SetParent(poolRoot, false);
                ParticleSystem ps = go.AddComponent<ParticleSystem>();
                var main = ps.main;
                main.playOnAwake = false;
                main.duration = 0.25f;
                main.startLifetime = 0.2f;
                main.startSpeed = 8f;
                main.startSize = 0.06f;
                main.startColor = sparkColor;
                main.loop = false;
                main.stopAction = ParticleSystemStopAction.None;

                var emission = ps.emission;
                emission.rateOverTime = 0;
                emission.burstCount = 1;
                emission.SetBurst(0, new ParticleSystem.Burst(0f, 14));

                var shape = ps.shape;
                shape.shapeType = ParticleSystemShapeType.Cone;
                shape.angle = 35f;
                shape.radius = 0.05f;

                var rend = go.GetComponent<ParticleSystemRenderer>();
                rend.sharedMaterial = sharedSparkMat;
                rend.renderMode = ParticleSystemRenderMode.Billboard;

                go.SetActive(false);
                sparkPool.Enqueue(new SparkItem { go = go, particles = ps });
            }

            // Muzzle Lights
            for (int i = 0; i < muzzleFlashPoolSize; i++)
            {
                GameObject go = new GameObject($"Flash_{i}");
                go.transform.SetParent(poolRoot, false);
                Light lt = go.AddComponent<Light>();
                lt.type = LightType.Point;
                lt.range = lightRange;
                lt.intensity = lightIntensity;
                lt.color = muzzleColor;
                lt.shadows = LightShadows.None;
                go.SetActive(false);

                flashPool.Enqueue(new FlashItem { go = go, light = lt });
            }
        }
    }
}
