using System;
using UnityEngine;

namespace ZeroProtocol.Combat
{
    /// <summary>
    /// Per-lane motorized overhead trolley target carrier system.
    /// Traverses overhead steel track beam spanning from the firing line to 25m.
    /// Every distance is measured from the shooter's standing position (FiringLineZ), so the HUD distance,
    /// the MOA maths and the floor stop markers all agree with where the player actually stands.
    /// Moves with smooth critically damped travel to preset stop distances:
    /// Recall (0.8m -> Z = -1.7m), 5m (Z = 2.5m), 10m (Z = 7.5m), 15m (Z = 12.5m), 25m (Z = 22.5m).
    /// </summary>
    public class TargetTrolley : MonoBehaviour
    {
        /// <summary>Shooter standing Z, behind the bench. Zero point of every range distance. ArenaBuilder spawns the player here.</summary>
        public const float FiringLineZ = -2.5f;

        public const float DistanceRecall = 0.8f;
        public const float Distance5M = 5.0f;
        public const float Distance10M = 10.0f;
        public const float Distance15M = 15.0f;
        public const float Distance25M = 25.0f;

        public const float ZRecall = FiringLineZ + DistanceRecall;
        public const float Z5M = FiringLineZ + Distance5M;
        public const float Z10M = FiringLineZ + Distance10M;
        public const float Z15M = FiringLineZ + Distance15M;
        public const float Z25M = FiringLineZ + Distance25M;

        [Header("Trolley Configuration")]
        [Tooltip("Firing line Z coordinate: the shooter's standing position (Reference: Z = -2.5m, behind the bench)")]
        public float boothOriginZ = FiringLineZ;

        [Tooltip("Smooth time for critically damped movement (seconds)")]
        public float smoothTime = 0.65f;

        [Tooltip("Maximum travel speed in meters per second")]
        public float maxSpeed = 8.0f;

        [Header("Attached Target")]
        public PaperTarget paperTarget;

        [Header("Visual Cables & Carriage")]
        public Transform carriageTransform;
        public Transform suspensionFrame;

        // Events
        public event Action<TargetTrolley, float> OnDistanceChanged;
        public event Action<TargetTrolley> OnArrived;

        float targetZ = Z10M;
        float currentVelocity;
        bool isMoving;

        public float CurrentZ => transform.position.z;
        public float TargetZ => targetZ;
        public float CurrentDistance => transform.position.z - boothOriginZ;
        public float TargetDistance => targetZ - boothOriginZ;
        public bool IsMoving => isMoving;
        public float Velocity => currentVelocity;

        void Awake()
        {
            if (carriageTransform == null) carriageTransform = transform;
            if (paperTarget == null) paperTarget = GetComponentInChildren<PaperTarget>();
            targetZ = transform.position.z;
        }

        void Start()
        {
            OnDistanceChanged?.Invoke(this, CurrentDistance);
        }

        void Update()
        {
            float dt = Time.deltaTime;
            if (dt <= 0f && Application.isPlaying) return;
            if (dt <= 0f) dt = 0.016f;

            Vector3 pos = transform.position;
            float diff = targetZ - pos.z;

            if (Mathf.Abs(diff) > 0.005f || Mathf.Abs(currentVelocity) > 0.01f)
            {
                isMoving = true;
                pos.z = Mathf.SmoothDamp(pos.z, targetZ, ref currentVelocity, smoothTime, maxSpeed, dt);
                transform.position = pos;
                OnDistanceChanged?.Invoke(this, CurrentDistance);
            }
            else if (isMoving)
            {
                pos.z = targetZ;
                transform.position = pos;
                currentVelocity = 0f;
                isMoving = false;
                OnDistanceChanged?.Invoke(this, CurrentDistance);
                OnArrived?.Invoke(this);
            }
        }

        public void MoveToDistance(float distanceInMeters)
        {
            targetZ = boothOriginZ + distanceInMeters;
            isMoving = true;
        }

        public void MoveToZ(float z)
        {
            targetZ = z;
            isMoving = true;
        }

        public void SetPreset(int presetIndex)
        {
            switch (presetIndex)
            {
                case 0:
                    MoveToDistance(DistanceRecall);
                    break;
                case 1:
                    MoveToDistance(Distance5M);
                    break;
                case 2:
                    MoveToDistance(Distance10M);
                    break;
                case 3:
                    MoveToDistance(Distance15M);
                    break;
                case 4:
                    MoveToDistance(Distance25M);
                    break;
                default:
                    MoveToDistance(Distance10M);
                    break;
            }
        }

        public void Recall()
        {
            MoveToDistance(DistanceRecall);
        }

        public void SendTo5M() => MoveToDistance(Distance5M);
        public void SendTo10M() => MoveToDistance(Distance10M);
        public void SendTo15M() => MoveToDistance(Distance15M);
        public void SendTo25M() => MoveToDistance(Distance25M);
    }
}
