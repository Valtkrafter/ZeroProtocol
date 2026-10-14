using System.Collections;
using System.IO;
using UnityEngine;
using ZeroProtocol.Player;

namespace ZeroProtocol.Dev
{
    /// <summary>
    /// Play Mode check of the hair cap: Yoru runs, the wind lifts the hair (strong wind on purpose), and the nape is photographed
    /// from the side, from behind and from three quarters. No brown cap may show through.
    /// </summary>
    public class HairLiftTest : MonoBehaviour
    {
        public string outputDir = "";
        public float testWind = 0.05f;
        public bool finished;

        IEnumerator Start()
        {
            Directory.CreateDirectory(outputDir);
            var player = FindFirstObjectByType<YoruController>();
            var input = player.GetComponent<GameInput>();
            var motion = player.GetComponentInChildren<YoruSecondaryMotion>();
            float oldWind = motion.windHair;
            motion.windHair = testWind;
            var camGo = new GameObject("HairLiftCam");
            var cam = camGo.AddComponent<Camera>();
            cam.enabled = false;
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.30f, 0.34f, 0.42f);
            cam.fieldOfView = 26f; cam.nearClipPlane = 0.05f;
            var animator = player.animator;
            var head = animator.GetBoneTransform(HumanBodyBones.Head);

            input.MoveOverride = new Vector2(0f, 1f);
            yield return new WaitForSeconds(1.2f);
            for (int i = 0; i < 3; i++)
            {
                Shot(cam, head, player.transform, "side_" + i, player.transform.right * 1.7f);
                Shot(cam, head, player.transform, "back_" + i, -player.transform.forward * 1.7f);
                Shot(cam, head, player.transform, "threeq_" + i, (player.transform.right - player.transform.forward) * 1.2f);
                yield return new WaitForSeconds(0.35f);
            }
            input.MoveOverride = Vector2.zero;
            motion.windHair = oldWind;
            Destroy(camGo);
            finished = true;
            File.WriteAllText(Path.Combine(outputDir, "done.txt"), "ok");
        }

        void Shot(Camera cam, Transform head, Transform root, string name, Vector3 offset)
        {
            Vector3 center = head.position + Vector3.down * 0.06f;
            cam.transform.position = center + offset + Vector3.up * 0.1f;
            cam.transform.LookAt(center);
            var rt = new RenderTexture(560, 560, 24, RenderTextureFormat.ARGB32);
            cam.targetTexture = rt;
            cam.Render();
            RenderTexture.active = rt;
            var tex = new Texture2D(rt.width, rt.height, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, rt.width, rt.height), 0, 0);
            tex.Apply();
            File.WriteAllBytes(Path.Combine(outputDir, name + ".png"), tex.EncodeToPNG());
            RenderTexture.active = null;
            cam.targetTexture = null;
            Destroy(tex); rt.Release(); Destroy(rt);
        }
    }
}
