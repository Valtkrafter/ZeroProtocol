using UnityEngine;
using ZeroProtocol.Player;

namespace ZeroProtocol.CameraSystem
{
    /// <summary>
    /// Wheel click (or right stick press) locks on to the target closest to the middle of the screen,
    /// a second click releases it. The lock also breaks when the target dies or is too far away.
    /// The marker is a temporary OnGUI box until the real UI exists.
    /// </summary>
    [RequireComponent(typeof(GameInput))]
    public class LockOnSystem : MonoBehaviour
    {
        public ThirdPersonCamera cameraRig;
        public float maxLockDistance = 30f;
        public float breakDistance = 40f;
        [Range(10f, 90f)] public float maxViewAngle = 65f;

        public LockOnTarget Current { get; private set; }

        GameInput input;
        Texture2D pixel;

        void Awake()
        {
            input = GetComponent<GameInput>();
            if (cameraRig == null && Camera.main != null) cameraRig = Camera.main.GetComponent<ThirdPersonCamera>();
            pixel = new Texture2D(1, 1);
            pixel.SetPixel(0, 0, Color.white);
            pixel.Apply();
        }

        void Update()
        {
            if (Current != null && (!Current.isActiveAndEnabled ||
                (Current.transform.position - transform.position).sqrMagnitude > breakDistance * breakDistance))
                Release();

            if (input.LockOnPressed)
            {
                if (Current != null) Release();
                else Acquire();
            }
        }

        void Acquire()
        {
            if (cameraRig == null) return;
            Transform cam = cameraRig.transform;
            LockOnTarget best = null;
            float bestScore = float.MaxValue;
            foreach (var t in LockOnTarget.All)
            {
                Vector3 to = t.AimPoint - cam.position;
                float dist = to.magnitude;
                if (dist > maxLockDistance || dist < 0.5f) continue;
                float angle = Vector3.Angle(cam.forward, to);
                if (angle > maxViewAngle) continue;
                float score = angle + dist * 0.2f;      // prefer the middle of the screen, then closer ones
                if (score < bestScore) { bestScore = score; best = t; }
            }
            if (best == null) return;
            Current = best;
            cameraRig.lockTarget = best.transform;
        }

        void Release()
        {
            Current = null;
            if (cameraRig != null) cameraRig.lockTarget = null;
        }

        void OnGUI()
        {
            if (Current == null || Camera.main == null) return;
            Vector3 sp = Camera.main.WorldToScreenPoint(Current.AimPoint);
            if (sp.z <= 0f) return;
            float y = Screen.height - sp.y;
            const float s = 26f, w = 3f;
            GUI.color = new Color(1f, 0.55f, 0.15f, 0.95f);
            // four corner brackets
            for (int sx = -1; sx <= 1; sx += 2)
                for (int sy = -1; sy <= 1; sy += 2)
                {
                    float cx = sp.x + sx * s, cy = y + sy * s;
                    GUI.DrawTexture(new Rect(cx - (sx > 0 ? 10f : 0f), cy - w * 0.5f, 10f, w), pixel);
                    GUI.DrawTexture(new Rect(cx - w * 0.5f, cy - (sy > 0 ? 10f : 0f), w, 10f), pixel);
                }
            GUI.color = Color.white;
        }
    }
}
