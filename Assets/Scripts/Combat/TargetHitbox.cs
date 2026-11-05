using UnityEngine;

namespace ZeroProtocol.Combat
{
    /// <summary>
    /// Hitbox proxy component placed on child colliders (Head, Body) to route damage
    /// and report distinct hit types to the parent ShootingTarget.
    /// Lives in its own file: Unity only loads a MonoBehaviour whose class name matches the file name.
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
}
