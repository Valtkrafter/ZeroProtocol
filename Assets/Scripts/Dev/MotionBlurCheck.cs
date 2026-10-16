using System.Collections;
using System.IO;
using UnityEngine;
using UnityEngine.Rendering.Universal;
using ZeroProtocol.CameraSystem;
using ZeroProtocol.Settings;

namespace ZeroProtocol.Dev
{
    /// <summary>
    /// Does the motion blur slider do something in the real Game view? The game camera is turned by a few degrees every frame (the same turn for every
    /// setting, so the pictures show the same scene), the Game view is captured at the end of the last frame with the slider at 0, 0.25, 0.5, 0.75 and 1,
    /// and the sharpness of the picture (mean absolute difference of neighbouring pixels) is compared. Blur lowers it. The pictures are saved.
    /// </summary>
    public class MotionBlurCheck : MonoBehaviour
    {
        public string outputDir = "";
        public float degreesPerFrame = 4f;
        public int turnFrames = 8;
        public bool finished;

        static double Sharpness(Texture2D t)
        {
            var p = t.GetPixels32();
            int w = t.width, h = t.height;
            double s = 0; long n = 0;
            for (int y = h / 4; y < 3 * h / 4; y += 2)
                for (int x = 1; x < w - 1; x++)
                {
                    int i = y * w + x;
                    s += Mathf.Abs((p[i + 1].r + p[i + 1].g + p[i + 1].b) - (p[i].r + p[i].g + p[i].b)) / 3.0;
                    n++;
                }
            return s / n;
        }

        /// <summary>Difference between the view-projection matrix of this frame and of the last frame that URP keeps for the camera motion blur (reflection: the data is internal).</summary>
        static string MotionHistory(UniversalAdditionalCameraData data)
        {
            try
            {
                var flags = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Public;
                object mv = typeof(UniversalAdditionalCameraData).GetProperty("motionVectorsPersistentData", flags).GetValue(data);
                var cur = (Matrix4x4[])mv.GetType().GetProperty("viewProjectionStereo", flags).GetValue(mv);
                var prev = (Matrix4x4[])mv.GetType().GetProperty("previousViewProjectionStereo", flags).GetValue(mv);
                float d = 0f; for (int k = 0; k < 16; k++) d += Mathf.Abs(cur[0][k] - prev[0][k]);
                return "sum |viewProj - previousViewProj| = " + d.ToString("F4");
            }
            catch (System.Exception e) { return "not readable: " + e.Message; }
        }

        IEnumerator Start()
        {
            Directory.CreateDirectory(outputDir);
            var cam = Camera.main;
            var rig = cam.GetComponent<ThirdPersonCamera>();
            var fx = PostFxSettings.Instance;
            var sb = new System.Text.StringBuilder();
            var data = cam.GetUniversalAdditionalCameraData();
            sb.AppendLine("settings component " + (fx != null) + ", volume " + (fx != null && fx.volume != null) + ", camera post processing " + data.renderPostProcessing + ", camera fov " + cam.fieldOfView.ToString("F1")
                          + ", game view " + Screen.width + " x " + Screen.height + ", turn " + degreesPerFrame + " deg per frame");
            if (rig != null) rig.enabled = false;                                       // the camera is held by this test
            yield return new WaitForSeconds(0.5f);
            Quaternion q0 = cam.transform.rotation;
            {
                yield return new WaitForEndOfFrame();
                var t0 = ScreenCapture.CaptureScreenshotAsTexture();
                var vg = fx.volume.profile.Add<UnityEngine.Rendering.Universal.Vignette>(true);
                vg.intensity.Override(0.8f);
                yield return null; yield return new WaitForEndOfFrame();
                var t1 = ScreenCapture.CaptureScreenshotAsTexture();
                var pa = t0.GetPixels32(); var pb = t1.GetPixels32(); double ds = 0;
                for (int i = 0; i < pa.Length; i++) ds += (Mathf.Abs(pa[i].r - pb[i].r) + Mathf.Abs(pa[i].g - pb[i].g) + Mathf.Abs(pa[i].b - pb[i].b)) / 3.0;
                sb.AppendLine("game view vignette sanity check: mean difference " + (ds / pa.Length).ToString("F2") + " of 255 (post processing reaches the game view if clearly above 0.5)");
                fx.volume.profile.Remove<UnityEngine.Rendering.Universal.Vignette>();
                Destroy(t0); Destroy(t1);
            }
            double sharp0 = 0;
            foreach (var mm in new[] { UnityEngine.Rendering.Universal.MotionBlurMode.CameraOnly, UnityEngine.Rendering.Universal.MotionBlurMode.CameraAndObjects })
            foreach (float v in new[] { 0f, 0.5f, 1f })
            {
                fx.blurMode = mm;
                fx.SetMotionBlur(v);
                cam.transform.rotation = q0;
                yield return null;
                for (int i = 0; i < turnFrames; i++)
                {
                    cam.transform.Rotate(0f, degreesPerFrame, 0f, Space.World);           // the last turn is made in the frame that is captured, so this frame moves against the last one
                    if (i < turnFrames - 1) yield return null;
                }
                yield return new WaitForEndOfFrame();
                var tex = ScreenCapture.CaptureScreenshotAsTexture();
                File.WriteAllBytes(Path.Combine(outputDir, "turn_blur_" + mm + "_" + Mathf.RoundToInt(v * 100f).ToString("D3") + ".png"), tex.EncodeToPNG());
                double sh = Sharpness(tex);
                if (v == 0f) sharp0 = sh;                                                   // the picture without blur of this mode
                sb.AppendLine(string.Format("{3} blur {0:F2}: sharpness {1:F3} ({2:F0} % of the sharpness without blur)", v, sh, 100.0 * sh / System.Math.Max(1e-9, sharp0), mm));
                Destroy(tex);
            }
            cam.transform.rotation = q0;
            fx.SetMotionBlur(0.4f);
            if (rig != null) rig.enabled = true;
            File.WriteAllText(Path.Combine(outputDir, "motion_blur.txt"), sb.ToString());
            finished = true;
        }
    }
}
