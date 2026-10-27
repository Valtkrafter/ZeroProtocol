using UnityEngine;

namespace ZeroProtocol.Combat
{
    public enum HitType
    {
        Body,
        Headshot,
        Weakpoint
    }

    public enum HandSide
    {
        Left,
        Right
    }

    public struct DamageInfo
    {
        public float damage;
        public Vector3 hitPoint;
        public Vector3 hitNormal;
        public Vector3 hitDirection;
        public HitType hitType;
        public HandSide handSide;
        public GameObject attacker;

        public DamageInfo(float damage, Vector3 hitPoint, Vector3 hitNormal, Vector3 hitDirection,
            HitType hitType, HandSide handSide, GameObject attacker = null)
        {
            this.damage = damage;
            this.hitPoint = hitPoint;
            this.hitNormal = hitNormal;
            this.hitDirection = hitDirection;
            this.hitType = hitType;
            this.handSide = handSide;
            this.attacker = attacker;
        }
    }

    public interface IDamageable
    {
        bool IsAlive { get; }
        void TakeDamage(DamageInfo info);
    }
}
