using System;
using UnityEngine;

namespace ZeroProtocol.Combat
{
    /// <summary>
    /// Per-lane motorized overhead trolley target carrier system.
    /// Traverses overhead steel track beam spanning from booth to 25m.
    /// Moves with smooth critically damped travel to preset stop distances:
    /// Recall (0.8m -> Z = -0.2m), 5m (Z = 4.0m), 10m (Z = 9.0m), 15m (Z = 14.0m), 25m (Z = 24.0m).
    /// </summary>
    public class TargetTrolley : MonoBehaviour
    {
        public const float DistanceRecall = 0.8f;
        public const float Distance5M = 5.0f;
        public const float Distance10M = 10.0f;
        public const float Distance15M = 15.0f;
        public const float Distance25M = 25.0f;

        public const float ZRecall = -0.2f;
        public const float Z5M = 4.0f;
        public const float Z10M = 9.0f;
        public const float Z15M = 14.0f;
        public const float Z25M = 24.0f;

        [Header("Trolley Configuration")]
        [Tooltip("Firing line booth origin Z coordinate (Reference: Z = -1.0m)")]
        public float boothOriginZ = -1.0f;

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
