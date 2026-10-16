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

        GUIStyle versionStyle;

        void Start()
        {
            if (captureCursor) SetCursor(true);
            Debug.Log("[ZeroProtocol] version " + VersionLabel() + ", Unity " + Application.unityVersion + ", scene " + gameObject.scene.name
                      + ", " + SystemInfo.graphicsDeviceName + " (" + SystemInfo.graphicsDeviceType + "), " + Screen.width + "x" + Screen.height);
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
            GUI.Label(new Rect(12, 8, 1400, 26),
                "WASD walk   Shift tap dodge   Shift hold sprint   Mouse camera   Space jump   Wheel click lock-on   Wheel zoom   Esc free cursor + settings (motion blur slider)");
            if (versionStyle == null)
            {
                versionStyle = new GUIStyle(GUI.skin.label) { alignment = TextAnchor.LowerRight, fontSize = 11 };
                versionStyle.normal.textColor = new Color(1f, 1f, 1f, 0.55f);
            }
            GUI.Label(new Rect(Screen.width - 312, Screen.height - 28, 300, 22), "Zero Protocol " + VersionLabel(), versionStyle);
        }

        /// <summary>"0.0.2" -> "Alpha 0.0.2" (every 0.x.y is Alpha, see Docs/VERSIONING.md); a version with a channel (0.5.0-beta.1) and 1.0.0 and up stay as they are.</summary>
        static string VersionLabel()
        {
            string v = Application.version;
            return v.StartsWith("0.") && !v.Contains("-") ? "Alpha " + v : v;
        }
    }
}
