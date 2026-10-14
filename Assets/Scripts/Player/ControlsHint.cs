using UnityEngine;
using UnityEngine.InputSystem;

namespace ZeroProtocol.Player
{
    /// <summary>
    /// Development helper: captures the cursor in Play Mode (Esc frees it, a click captures it again)
    /// and shows the keys in the top left corner. Replaced by the real UI later.
    /// </summary>
    public class ControlsHint : MonoBehaviour
    {
        public bool captureCursor = true;

        void Start()
        {
            if (captureCursor) SetCursor(true);
        }

        void Update()
        {
            if (Keyboard.current != null && Keyboard.current.escapeKey.wasPressedThisFrame) SetCursor(false);
            if (captureCursor && Mouse.current != null && Mouse.current.leftButton.wasPressedThisFrame
                && Cursor.lockState != CursorLockMode.Locked) SetCursor(true);
        }

        static void SetCursor(bool locked)
        {
            Cursor.lockState = locked ? CursorLockMode.Locked : CursorLockMode.None;
            Cursor.visible = !locked;
        }

        void OnGUI()
        {
            GUI.Label(new Rect(12, 8, 640, 26),
                "WASD walk   Mouse camera   Space jump   Shift dash   Wheel click lock-on   Wheel zoom   Esc free cursor");
        }
    }
}
