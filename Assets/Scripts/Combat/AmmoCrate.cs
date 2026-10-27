using UnityEngine;

namespace ZeroProtocol.Combat
{
    /// <summary>
    /// Resupply ammo station placed in the firing range booth.
    /// Replenishes player's pistols to full capacity when approached.
    /// Non-allocating physics and zero garbage collection overhead.
    /// </summary>
    public class AmmoCrate : MonoBehaviour
    {
        [Header("Resupply Configuration")]
        [Tooltip("Trigger interaction radius in meters")]
        public float resupplyRadius = 2.5f;

        [Tooltip("Cooldown in seconds between resupply pulses")]
        public float cooldown = 1.0f;

        float lastResupplyTime = -10f;
        readonly Collider[] overlapBuffer = new Collider[8];

        void Update()
        {
            float dt = Time.deltaTime;
            if (dt <= 0f && Application.isPlaying) return;

            if (Time.time < lastResupplyTime + cooldown) return;

            // Non-allocating overlap sphere check
            int count = Physics.OverlapSphereNonAlloc(transform.position, resupplyRadius, overlapBuffer, ~0, QueryTriggerInteraction.Collide);
            for (int i = 0; i < count; i++)
            {
                Collider col = overlapBuffer[i];
                if (col == null) continue;

                DualPistolCombat combat = col.GetComponentInParent<DualPistolCombat>();
                if (combat != null)
                {
                    if (combat.AmmoLeft < combat.maxAmmoPerMag || combat.AmmoRight < combat.maxAmmoPerMag || combat.IsReloading)
                    {
                        combat.ResupplyAmmo();
                        lastResupplyTime = Time.time;
                        break;
                    }
                }
            }
        }

        public void ForceResupply(DualPistolCombat combat)
        {
            if (combat != null)
            {
                combat.ResupplyAmmo();
                lastResupplyTime = Time.time;
            }
        }

        void OnDrawGizmosSelected()
        {
            Gizmos.color = new Color(0f, 0.94f, 1f, 0.4f);
            Gizmos.DrawWireSphere(transform.position, resupplyRadius);
        }
    }
}
