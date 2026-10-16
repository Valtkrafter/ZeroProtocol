using UnityEngine;
using UnityEngine.InputSystem;

namespace ZeroProtocol.Player
{
    /// <summary>
    /// Owns every gameplay input action. Other scripts only read from here, so a menu or a cutscene
    /// can switch the whole player input off in one place (InputEnabled).
    /// Keyboard + mouse like Wuthering Waves (WASD, mouse camera, Space jump, Shift = dodge when tapped and sprint when held,
    /// wheel click lock-on) plus a gamepad fallback.
    /// </summary>
    [DefaultExecutionOrder(-100)]
    public class GameInput : MonoBehaviour
    {
        [Header("Camera look")]
        public float mouseDegreesPerPixel = 0.09f;
        public float stickDegreesPerSecond = 170f;

        public bool InputEnabled = true;

        /// <summary>Move stick: x = right, y = forward (length 0..1).</summary>
        public Vector2 Move { get; private set; }
        /// <summary>Camera look in degrees for THIS frame (x = yaw, y = pitch up).</summary>
        public Vector2 Look { get; private set; }
        /// <summary>Mouse wheel / trigger zoom, positive = zoom out.</summary>
        public float Zoom { get; private set; }
        public bool JumpPressed { get; private set; }
        /// <summary>The frame in which Shift (pad: east button) went down: the dodge starts at once, a short press never waits for a hold.</summary>
        public bool DashPressed { get; private set; }
        /// <summary>Shift (pad: east button) is held down: after the dodge is over it goes on into the sprint (see YoruController.sprintHoldDelay).</summary>
        public bool SprintHeld { get; private set; }
        public bool LockOnPressed { get; private set; }
        /// <summary>Held: Ctrl. Reserved, it does nothing yet: Ctrl will get its own animation later (W already plays the walk).</summary>
        public bool CtrlHeld { get; private set; }

        /// <summary>Test hooks: when set, they replace the real devices (used by automated checks).</summary>
        public Vector2? MoveOverride;
        public bool JumpOverride, DashOverride, LockOnOverride;
        /// <summary>Stay on until they are set back (a held Ctrl key, a held Shift key).</summary>
        public bool CtrlOverride, SprintOverride;

        InputAction move, look, zoom, jump, dash, lockOn, ctrl;

        void Awake()
        {
            move = new InputAction("Move", InputActionType.Value);
            move.AddCompositeBinding("2DVector")
                .With("Up", "<Keyboard>/w").With("Down", "<Keyboard>/s")
                .With("Left", "<Keyboard>/a").With("Right", "<Keyboard>/d");
            move.AddBinding("<Gamepad>/leftStick");

            look = new InputAction("Look", InputActionType.Value);
            look.AddBinding("<Mouse>/delta");
            look.AddBinding("<Gamepad>/rightStick");

            zoom = new InputAction("Zoom", InputActionType.Value);
            zoom.AddBinding("<Mouse>/scroll/y");

            jump = new InputAction("Jump", InputActionType.Button);
            jump.AddBinding("<Keyboard>/space");
            jump.AddBinding("<Gamepad>/buttonSouth");

            dash = new InputAction("Dash", InputActionType.Button);
            dash.AddBinding("<Keyboard>/leftShift");
            dash.AddBinding("<Gamepad>/buttonEast");

            lockOn = new InputAction("LockOn", InputActionType.Button);
            lockOn.AddBinding("<Mouse>/middleButton");
            lockOn.AddBinding("<Gamepad>/rightStickPress");

            ctrl = new InputAction("Ctrl", InputActionType.Button);
            ctrl.AddBinding("<Keyboard>/leftCtrl");
            ctrl.AddBinding("<Keyboard>/rightCtrl");
        }

        void OnEnable()
        {
            move.Enable(); look.Enable(); zoom.Enable(); jump.Enable(); dash.Enable(); lockOn.Enable(); ctrl.Enable();
        }

        void OnDisable()
        {
            move.Disable(); look.Disable(); zoom.Disable(); jump.Disable(); dash.Disable(); lockOn.Disable(); ctrl.Disable();
        }

        void Update()
        {
            if (!InputEnabled)
            {
                Move = Vector2.zero; Look = Vector2.zero; Zoom = 0f;
                JumpPressed = DashPressed = LockOnPressed = CtrlHeld = SprintHeld = false;
                return;
            }

            Move = Vector2.ClampMagnitude(MoveOverride ?? move.ReadValue<Vector2>(), 1f);
            CtrlHeld = ctrl.IsPressed() || CtrlOverride;
            JumpPressed = jump.WasPressedThisFrame() || JumpOverride;
            DashPressed = dash.WasPressedThisFrame() || DashOverride;
            SprintHeld = dash.IsPressed() || SprintOverride;
            LockOnPressed = lockOn.WasPressedThisFrame() || LockOnOverride;
            JumpOverride = DashOverride = LockOnOverride = false;

            // Mouse delta only counts while the cursor is captured; the stick is time based.
            Vector2 raw = look.ReadValue<Vector2>();
            bool usingMouse = Mouse.current != null && Mouse.current.delta.ReadValue().sqrMagnitude > 0f;
            if (usingMouse)
                Look = Cursor.lockState == CursorLockMode.Locked ? raw * mouseDegreesPerPixel : Vector2.zero;
            else
                Look = raw * stickDegreesPerSecond * Time.deltaTime;

            Zoom = -zoom.ReadValue<float>() * 0.01f;
        }
    }
}
