using System.Collections;
using System.IO;
using UnityEngine;
using ZeroProtocol.Player;

namespace ZeroProtocol.Dev
{
    /// <summary>
    /// Films the walk in the game: the game is run at exactly 30 frames per second of game time (Time.captureFramerate) and three pictures
    /// are saved every frame: front three quarters (A), side (B) and a close-up of the face (C), all following her. The floor grid shows
    /// whether the feet slide. The blink of the film is the Blender blink (seed 312, see YoruBlink.Restart).
    /// </summary>
    public class WalkFilmTest : MonoBehaviour
    {
        public string outputDir = "";
        public int frames = 120;
        public int blinkSeed = 312;
        public bool finished;

        Camera MakeCam(string name, bool ortho, float size)
        {
            var go = new GameObject(name);
            var c = go.AddComponent<Camera>();
            c.enabled = false;
            c.clearFlags = CameraClearFlags.SolidColor;
            c.backgroundColor = new Color(0.20f, 0.23f, 0.30f);
            c.orthographic = ortho;
            if (ortho) c.orthographicSize = size; else { c.fieldOfView = size; c.nearClipPlane = 0.05f; }
            return c;
        }

        void Snap(Camera cam, int w, int h, string file)
        {
            var rt = new RenderTexture(w, h, 24, RenderTextureFormat.ARGB32);
            cam.targetTexture = rt;
            cam.Render();
            RenderTexture.active = rt;
            var tex = new Texture2D(w, h, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, w, h), 0, 0);
            tex.Apply();
            File.WriteAllBytes(file, tex.EncodeToPNG());
            RenderTexture.active = null;
            cam.targetTexture = null;
            Destroy(tex); rt.Release(); Destroy(rt);
        }

        IEnumerator Start()
        {
            Directory.CreateDirectory(outputDir);
            var player = FindFirstObjectByType<YoruController>();
            var input = player.GetComponent<GameInput>();
            var anim = player.animator;
            var blink = anim.GetComponent<YoruBlink>();
            var root = player.transform;
            var cc = player.GetComponent<CharacterController>();
            var lEye = anim.GetBoneTransform(HumanBodyBones.LeftEye);
            var rEye = anim.GetBoneTransform(HumanBodyBones.RightEye);
            var camA = MakeCam("FilmA", true, 0.95f);
            var camB = MakeCam("FilmB", true, 0.95f);
            var camC = MakeCam("FilmC", false, 13f);

            cc.enabled = false; root.position = new Vector3(0f, 0.05f, -8f); root.rotation = Quaternion.identity; cc.enabled = true;
            yield return new WaitForSeconds(1.0f);
            Time.captureFramerate = 30;
            input.MoveOverride = new Vector2(0f, 1f);
           
            for (int i = 0; i < 45; i++) yield return null;                 // 1.5 s: she reaches the walking speed, the spring bones find their rhythm
            blink.Restart(blinkSeed);                                        // the blink of the film starts now (first blink after 1.9 s, then 5.5 s)
            for (int f = 0; f < frames; f++)
            {
                yield return new WaitForEndOfFrame();
                Vector3 look = root.position + Vector3.up * 0.8f;
                camA.transform.position = root.position + root.right * 1.6f + Vector3.up * 1.1f + root.forward * 3.0f;
                camA.transform.LookAt(look);
                camB.transform.position = root.position + root.right * 3.2f + Vector3.up * 0.95f;
                camB.transform.LookAt(look);
                Vector3 c = (lEye.position + rEye.position) * 0.5f;
                camC.transform.position = c + root.forward * 0.9f;
                camC.transform.LookAt(c + Vector3.down * 0.012f);
                Snap(camA, 540, 720, Path.Combine(outputDir, "A_" + f.ToString("D3") + ".png"));
                Snap(camB, 540, 720, Path.Combine(outputDir, "B_" + f.ToString("D3") + ".png"));
                Snap(camC, 540, 720, Path.Combine(outputDir, "C_" + f.ToString("D3") + ".png"));
                File.AppendAllText(Path.Combine(outputDir, "film_log.txt"), f + " blinkClock " + blink.Clock.ToString("F3") + " lid " + blink.Lid.ToString("F3") + " speed " + player.HorizontalSpeed.ToString("F3") + "\n");
            }
            Time.captureFramerate = 0;
            input.MoveOverride = Vector2.zero;
            File.WriteAllText(Path.Combine(outputDir, "done.txt"), "ok");
            finished = true;
        }
    }
}
