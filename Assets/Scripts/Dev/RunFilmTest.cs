using System.Collections;
using System.IO;
using UnityEngine;
using ZeroProtocol.Player;

namespace ZeroProtocol.Dev
{
    /// <summary>
    /// Films the sprint in the game: the game is run at exactly 60 frames per second of game time (Time.captureFramerate) and three pictures are saved
    /// every frame: front three quarters (A), side (B) and the real game camera with its post processing and speed feel (C), following her.
    /// The floor grid shows whether the feet slide. Shift is held (sprint) from the 2nd second on, so the walk -> sprint change is in the film too.
    /// </summary>
    public class RunFilmTest : MonoBehaviour
    {
        public string outputDir = "";
        public int frames = 240;
        public bool finished;

        Camera MakeCam(string name, float size)
        {
            var go = new GameObject(name);
            var c = go.AddComponent<Camera>();
            c.enabled = false;
            c.clearFlags = CameraClearFlags.SolidColor;
            c.backgroundColor = new Color(0.20f, 0.23f, 0.30f);
            c.orthographic = true; c.orthographicSize = size;
            return c;
        }

        void Snap(Camera cam, int w, int h, string file)
        {
            var rt = new RenderTexture(w, h, 24, RenderTextureFormat.ARGB32);
            var old = cam.targetTexture;
            cam.targetTexture = rt;
            cam.Render();
            RenderTexture.active = rt;
            var tex = new Texture2D(w, h, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, w, h), 0, 0);
            tex.Apply();
            File.WriteAllBytes(file, tex.EncodeToPNG());
            RenderTexture.active = null;
            cam.targetTexture = old;
            Destroy(tex); rt.Release(); Destroy(rt);
        }

        IEnumerator Start()
        {
            Directory.CreateDirectory(outputDir);
            var player = FindFirstObjectByType<YoruController>();
            var input = player.GetComponent<GameInput>();
            var root = player.transform;
            var cc = player.GetComponent<CharacterController>();
            var camA = MakeCam("FilmA", 0.95f);
            var camB = MakeCam("FilmB", 0.95f);
            var game = Camera.main;

            cc.enabled = false; root.position = new Vector3(2f, 0.05f, -37f); root.rotation = Quaternion.identity; cc.enabled = true;
            yield return new WaitForSeconds(1.0f);
            Time.captureFramerate = 60;
            input.MoveOverride = new Vector2(0f, 1f);
            for (int i = 0; i < 60; i++) yield return null;                  // 1 s of walking at 60 fps
            input.SprintOverride = true;
            for (int i = 0; i < 90; i++) yield return null;                  // the sprint takes over, the spring bones find their rhythm
            for (int f = 0; f < frames; f++)
            {
                yield return new WaitForEndOfFrame();
                Vector3 look = root.position + Vector3.up * 0.8f;
                camA.transform.position = root.position + root.right * 1.6f + Vector3.up * 1.1f + root.forward * 3.0f;
                camA.transform.LookAt(look);
                camB.transform.position = root.position + root.right * 3.2f + Vector3.up * 0.95f;
                camB.transform.LookAt(look);
                Snap(camA, 540, 720, Path.Combine(outputDir, "A_" + f.ToString("D3") + ".png"));
                Snap(camB, 540, 720, Path.Combine(outputDir, "B_" + f.ToString("D3") + ".png"));
                if (game != null) Snap(game, 540, 720, Path.Combine(outputDir, "C_" + f.ToString("D3") + ".png"));
                File.AppendAllText(Path.Combine(outputDir, "film_log.txt"), f + " speed " + player.HorizontalSpeed.ToString("F3") + " fov " + (game != null ? game.fieldOfView.ToString("F1") : "?") + "\n");
            }
            Time.captureFramerate = 0;
            input.MoveOverride = Vector2.zero; input.SprintOverride = false;
            File.WriteAllText(Path.Combine(outputDir, "done.txt"), "ok");
            finished = true;
        }
    }
}
