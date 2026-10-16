using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace ZeroProtocol.Settings
{
    /// <summary>
    /// Post-processing settings the player can change in the game. For now: the strength of the motion blur (a slider from 0 = off to 100 %),
    /// saved between sessions. The slider is shown in the top right corner while the cursor is free (Esc in the game, or F10 in the editor too).
    /// The blur itself is the URP "Motion Blur" override of a global Volume (built by Zero Protocol / Add Post Processing); "Camera and objects"
    /// also blurs the moving character against the still background, the clamp keeps the blur from smearing at the sprint.
    /// </summary>
    public class PostFxSettings : MonoBehaviour
    {
        public const string PrefKeyMotionBlur = "ZeroProtocol.MotionBlur";

        [Tooltip("The global Volume that holds the Motion Blur override.")]
        public Volume volume;
        [Tooltip("Strength of the motion blur, 0 = off, 1 = full. The saved value of the player wins at the start.")]
        [Range(0f, 1f)] public float motionBlur = 0.4f;
        public MotionBlurMode blurMode = MotionBlurMode.CameraAndObjects;
        public MotionBlurQuality blurQuality = MotionBlurQuality.High;                      // High = more samples, less of the dithered noise in the streaks
        [Tooltip("Largest blur length as a share of the screen: keeps a fast turn of the camera from smearing the picture.")]
        [Range(0f, 0.2f)] public float blurClamp = 0.06f;
        [Tooltip("Show the slider panel while the cursor is free (Esc in the game).")]
        public bool showPanelWhenCursorFree = true;
        [Tooltip("Show the slider panel in any case (F10 toggles it).")]
        public bool panelPinned;

        public static PostFxSettings Instance { get; private set; }

        void Awake()
        {
            Instance = this;
            motionBlur = PlayerPrefs.GetFloat(PrefKeyMotionBlur, motionBlur);
            var cam = Camera.main;
            if (cam != null) cam.GetUniversalAdditionalCameraData().renderPostProcessing = true;
            Apply();
        }

        /// <summary>Sets the motion blur strength (0..1), applies it and remembers it.</summary>
        public void SetMotionBlur(float value)
        {
            motionBlur = Mathf.Clamp01(value);
            PlayerPrefs.SetFloat(PrefKeyMotionBlur, motionBlur);
            Apply();
        }

        /// <summary>Writes the settings into the Motion Blur override of the volume (the profile is this scene's own copy, the asset stays as built).</summary>
        public void Apply()
        {
            if (volume == null || volume.profile == null) return;
            if (!volume.profile.TryGet(out MotionBlur blur)) blur = volume.profile.Add<MotionBlur>(true);      // looked up every time: the runtime profile is a copy that is recreated with the scene
            blur.active = motionBlur > 0.001f;
            blur.mode.Override(blurMode);
            blur.quality.Override(blurQuality);
            blur.clamp.Override(blurClamp);
            blur.intensity.Override(motionBlur);
        }

        void OnValidate()
        {
            if (Application.isPlaying && volume != null) Apply();
        }

        void Update()
        {
            if (UnityEngine.InputSystem.Keyboard.current != null && UnityEngine.InputSystem.Keyboard.current.f10Key.wasPressedThisFrame) panelPinned = !panelPinned;
        }

        void OnGUI()
        {
            if (!panelPinned && !(showPanelWhenCursorFree && Cursor.lockState != CursorLockMode.Locked)) return;
            float s = Mathf.Max(1f, Screen.height / 1080f);
            var old = GUI.matrix;
            GUI.matrix = Matrix4x4.Scale(new Vector3(s, s, 1f));
            float w = 330f, x = Screen.width / s - w - 16f, y = 44f;
            GUI.Box(new Rect(x, y, w, 118f), "Einstellungen");
            GUI.Label(new Rect(x + 14f, y + 28f, w - 28f, 22f), "Motion Blur: " + (motionBlur < 0.001f ? "aus" : Mathf.RoundToInt(motionBlur * 100f) + " %"));
            float v = GUI.HorizontalSlider(new Rect(x + 14f, y + 56f, w - 28f, 22f), motionBlur, 0f, 1f);
            if (!Mathf.Approximately(v, motionBlur)) SetMotionBlur(v);
            GUI.Label(new Rect(x + 14f, y + 80f, w - 28f, 34f), "Esc: Menü auf/zu (Klick ins Spiel schließt), F10: festhalten");
            GUI.matrix = old;
        }
    }
}
