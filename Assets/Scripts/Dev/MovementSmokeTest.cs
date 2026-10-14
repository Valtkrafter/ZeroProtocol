using System.Collections;
using System.IO;
using System.Text;
using UnityEngine;
using ZeroProtocol.CameraSystem;
using ZeroProtocol.Player;

namespace ZeroProtocol.Dev
{
    /// <summary>
    /// Scripted Play Mode check: runs, stops, jumps, dashes, locks on, and writes numbers plus game-camera
    /// pictures into outputDir. Used instead of a human pressing keys, so a stage can be verified automatically.
    /// </summary>
    public class MovementSmokeTest : MonoBehaviour
    {
        public string outputDir = "";
        public bool finished;
        readonly StringBuilder log = new StringBuilder();

        void Start() { StartCoroutine(Run()); }

        IEnumerator Run()
        {
            var player = FindFirstObjectByType<YoruController>();
            var input = player.GetComponent<GameInput>();
            var lockSys = player.GetComponent<LockOnSystem>();
            var camRig = Camera.main.GetComponent<ThirdPersonCamera>();
            Directory.CreateDirectory(outputDir);
            input.InputEnabled = false;                  // real devices off; overrides are applied below
            input.InputEnabled = true;
            yield return new WaitForSeconds(0.6f);
            Log("start pos " + P(player.transform.position) + " grounded " + player.IsGrounded + " frame " + Time.frameCount);
            Shot("01_start");

            // run forward 1.5 s
            Vector3 p0 = player.transform.position;
            input.MoveOverride = new Vector2(0f, 1f);
            yield return new WaitForSeconds(1.5f);
            float peakSpeed = new Vector2(player.Velocity.x, player.Velocity.z).magnitude;
            Log("run 1.5 s: moved " + (player.transform.position - p0).magnitude.ToString("F2") + " m, speed " + peakSpeed.ToString("F2") + " m/s");
            Shot("02_run");
            input.MoveOverride = Vector2.zero;
            yield return new WaitForSeconds(0.5f);
            Log("after stop: horizontal speed " + new Vector2(player.Velocity.x, player.Velocity.z).magnitude.ToString("F2") + " (expect ~0)");

            // jump
            float y0 = player.transform.position.y, maxY = y0;
            input.JumpOverride = true;
            float t = 0f;
            while (t < 1.2f) { t += Time.deltaTime; maxY = Mathf.Max(maxY, player.transform.position.y); yield return null; }
            Log("jump: rose " + (maxY - y0).ToString("F2") + " m (expect ~1.5), grounded again " + player.IsGrounded);

            // dash forward
            Vector3 d0 = player.transform.position;
            input.DashOverride = true;
            yield return new WaitForSeconds(0.5f);
            Log("dash: covered " + (player.transform.position - d0).magnitude.ToString("F2") + " m");
            Shot("03_after_dash");
            yield return new WaitForSeconds(0.5f);

            // lock-on
            input.LockOnOverride = true;
            yield return new WaitForSeconds(1.2f);
            Log("lock-on: target " + (lockSys.Current == null ? "NONE" : lockSys.Current.name) + ", camera yaw " + camRig.Yaw.ToString("F1"));
            Shot("04_locked");
            input.MoveOverride = new Vector2(1f, 0f);       // strafe right while locked
            yield return new WaitForSeconds(1.0f);
            input.MoveOverride = Vector2.zero;
            Shot("05_locked_after_strafe");
            input.LockOnOverride = true;
            yield return new WaitForSeconds(0.4f);
            Log("lock released: " + (lockSys.Current == null));

            File.WriteAllText(Path.Combine(outputDir, "smoke_log.txt"), log.ToString());
            finished = true;
        }

        void Shot(string name)
        {
            var cam = Camera.main;
            var rt = new RenderTexture(960, 540, 24, RenderTextureFormat.ARGB32);
            var old = cam.targetTexture;
            cam.targetTexture = rt;
            cam.Render();
            RenderTexture.active = rt;
            var tex = new Texture2D(rt.width, rt.height, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, rt.width, rt.height), 0, 0);
            tex.Apply();
            File.WriteAllBytes(Path.Combine(outputDir, name + ".png"), tex.EncodeToPNG());
            RenderTexture.active = null;
            cam.targetTexture = old;
            Destroy(tex);
            rt.Release();
            Destroy(rt);
        }

        void Log(string s) { log.AppendLine(s); Debug.Log("[SmokeTest] " + s); }
        static string P(Vector3 v) { return v.ToString("F2"); }
    }
}
