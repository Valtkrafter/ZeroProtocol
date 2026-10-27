using System.Collections.Generic;
using UnityEngine;

namespace ZeroProtocol.Combat
{
    /// <summary>
    /// Pre-warmed object pool of physical brass pistol cartridge casings with Rigidbody and capsule colliders.
    /// Ejected dynamically on each alternating pistol discharge from DualPistolCombat.
    /// Zero runtime GC allocations. Casings collide naturally with counters/floor and recycle after 8 seconds.
    /// </summary>
    public class ShellCasingPool : MonoBehaviour
    {
        public DualPistolCombat combat;

        [Header("Pool Configuration")]
        [Tooltip("Number of pre-warmed casing instances in the pool")]
        public int poolSize = 36;
        [Tooltip("Lifetime in seconds before casing fades and is recycled to pool (Specification: 8s)")]
        public float casingLifetime = 8.0f;

        [Header("Ejection Dynamics")]
        public Vector3 leftEjectionOffset = new Vector3(-0.15f, 0.08f, -0.05f);
        public Vector3 rightEjectionOffset = new Vector3(0.15f, 0.08f, -0.05f);
        public Vector3 leftEjectionImpulse = new Vector3(-2.4f, 1.9f, -0.4f);
        public Vector3 rightEjectionImpulse = new Vector3(2.4f, 1.9f, -0.4f);
        public float impulseRandomSpread = 0.30f;
        public float angularSpinSpeed = 28f;

        public class CasingItem
        {
            public GameObject go;
            public Transform transform;
            public Rigidbody rb;
            public CapsuleCollider col;
            public float timer;
        }

        readonly Queue<CasingItem> availablePool = new Queue<CasingItem>();
        readonly List<CasingItem> activeCasings = new List<CasingItem>();

        Transform poolRoot;
        Material sharedBrassMat;

        public int ActiveCasingCount => activeCasings.Count;
        public int AvailableCount => availablePool.Count;

        void Awake()
        {
            if (combat == null) combat = GetComponentInParent<DualPistolCombat>();
            if (combat == null) combat = FindFirstObjectByType<DualPistolCombat>();

            InitializeMaterial();
            CreatePoolHierarchy();
            PrewarmPool();
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

            if (sharedBrassMat != null)
            {
                Destroy(sharedBrassMat);
            }
        }

        void Update()
        {
            float dt = Time.deltaTime;
            if (dt <= 0f) return;

            for (int i = activeCasings.Count - 1; i >= 0; i--)
            {
                CasingItem item = activeCasings[i];
                item.timer -= dt;
                if (item.timer <= 0f)
                {
                    RecycleItem(i);
                }
            }
        }

        public void HandleWeaponFired(FireEventData fireData)
        {
            EjectCasing(fireData.Hand, fireData.MuzzlePosition, fireData.FireDirection);
        }

        public void EjectCasing(HandSide hand, Vector3 muzzlePosition, Vector3 fireDirection)
        {
            CasingItem item = null;
            if (availablePool.Count > 0)
            {
                item = availablePool.Dequeue();
            }
            else if (activeCasings.Count > 0)
            {
                // Recycle oldest active instance
                item = activeCasings[0];
                activeCasings.RemoveAt(0);
            }

            if (item == null) return;

            Transform refTransform = combat != null ? combat.transform : transform;
            Vector3 offset = (hand == HandSide.Left) ? leftEjectionOffset : rightEjectionOffset;
            Vector3 spawnPos = muzzlePosition + refTransform.TransformDirection(offset);

            item.transform.position = spawnPos;
            item.transform.rotation = Random.rotation;
            item.go.SetActive(true);

            // Reset rigidbody velocities
            item.rb.linearVelocity = Vector3.zero;
            item.rb.angularVelocity = Vector3.zero;

            // Apply realistic lateral ejection impulse and angular spin
            Vector3 baseImpulse = (hand == HandSide.Left) ? leftEjectionImpulse : rightEjectionImpulse;
            Vector3 impulseWorld = refTransform.TransformDirection(baseImpulse) + Random.insideUnitSphere * impulseRandomSpread;
            item.rb.AddForce(impulseWorld, ForceMode.Impulse);

            Vector3 torque = Random.insideUnitSphere * angularSpinSpeed;
            item.rb.AddTorque(torque, ForceMode.Impulse);

            item.timer = casingLifetime;
            activeCasings.Add(item);
        }

        public void RecycleAll()
        {
            for (int i = activeCasings.Count - 1; i >= 0; i--)
            {
                RecycleItem(i);
            }
        }

        void RecycleItem(int index)
        {
            CasingItem item = activeCasings[index];
            item.go.SetActive(false);
            item.rb.linearVelocity = Vector3.zero;
            item.rb.angularVelocity = Vector3.zero;
            activeCasings.RemoveAt(index);
            availablePool.Enqueue(item);
        }

        void InitializeMaterial()
        {
            Shader litShader = Shader.Find("Universal Render Pipeline/Lit");
            if (litShader == null) litShader = Shader.Find("Standard");

            sharedBrassMat = new Material(litShader);
            sharedBrassMat.name = "BrassCasing_SharedMat";
            Color brassColor = new Color(0.88f, 0.68f, 0.24f, 1f);
            sharedBrassMat.SetColor("_BaseColor", brassColor);
            sharedBrassMat.SetColor("_Color", brassColor);
            sharedBrassMat.SetFloat("_Metallic", 0.92f);
            sharedBrassMat.SetFloat("_Smoothness", 0.75f);
        }

        void CreatePoolHierarchy()
        {
            GameObject root = new GameObject("_ShellCasing_PoolRoot");
            poolRoot = root.transform;
            poolRoot.SetParent(transform, false);
        }

        void PrewarmPool()
        {
            PhysicsMaterial brassPhysMat = new PhysicsMaterial("BrassCasing_PhysMat")
            {
                bounciness = 0.45f,
                dynamicFriction = 0.35f,
                staticFriction = 0.45f,
                bounceCombine = PhysicsMaterialCombine.Maximum
            };

            Collider playerCol = combat != null ? combat.GetComponent<Collider>() : null;

            for (int i = 0; i < poolSize; i++)
            {
                GameObject go = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                go.name = $"Casing_{i}";
                go.transform.SetParent(poolRoot, false);
                go.transform.localScale = new Vector3(0.012f, 0.018f, 0.012f); // Handgun 9mm cartridge scale

                // Replace cylinder collider with smooth capsule collider
                Collider cylCol = go.GetComponent<Collider>();
                if (cylCol != null) DestroyImmediate(cylCol);

                CapsuleCollider capsule = go.AddComponent<CapsuleCollider>();
                capsule.radius = 0.5f;
                capsule.height = 2.0f;
                capsule.direction = 1; // Y-axis aligned
                capsule.material = brassPhysMat;

                if (playerCol != null)
                {
                    Physics.IgnoreCollision(capsule, playerCol, true);
                }

                Renderer rend = go.GetComponent<Renderer>();
                rend.sharedMaterial = sharedBrassMat;
                rend.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;

                Rigidbody rb = go.AddComponent<Rigidbody>();
                rb.mass = 0.012f;
                rb.collisionDetectionMode = CollisionDetectionMode.ContinuousDynamic;
                rb.interpolation = RigidbodyInterpolation.Interpolate;

                go.SetActive(false);

                var item = new CasingItem
                {
                    go = go,
                    transform = go.transform,
                    rb = rb,
                    col = capsule,
                    timer = 0f
                };

                availablePool.Enqueue(item);
            }
        }
    }
}
