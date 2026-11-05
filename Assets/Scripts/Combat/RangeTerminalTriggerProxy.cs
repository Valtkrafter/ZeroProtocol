using UnityEngine;
using ZeroProtocol.Player;

namespace ZeroProtocol.Combat
{
    /// <summary>
    /// Routes the stall proximity trigger volume to its RangeTerminal. Lives in the runtime assembly on purpose:
    /// an Editor-only script loads as Missing Script in a standalone build, and the booth would never wake up.
    /// </summary>
    public class RangeTerminalTriggerProxy : MonoBehaviour
    {
        public RangeTerminal terminal;

        void Start()
        {
            var col = GetComponent<BoxCollider>();
            if (col != null && terminal != null)
            {
                // Check if the player spawned inside the trigger volume at startup
                var hits = Physics.OverlapBox(transform.position + col.center, col.size * 0.5f, transform.rotation);
                for (int i = 0; i < hits.Length; i++)
                {
                    if (IsPlayer(hits[i]))
                    {
                        terminal.SetPlayerInside(true);
                        break;
                    }
                }
            }
        }

        void OnTriggerEnter(Collider other)
        {
            if (terminal != null && IsPlayer(other))
            {
                terminal.SetPlayerInside(true);
            }
        }

        void OnTriggerExit(Collider other)
        {
            if (terminal != null && IsPlayer(other))
            {
                terminal.SetPlayerInside(false);
            }
        }

        static bool IsPlayer(Collider other)
        {
            return other.CompareTag("Player") || other.GetComponent<YoruController>() != null || other.GetComponent<CharacterController>() != null;
        }
    }
}
