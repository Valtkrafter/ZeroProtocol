using System.Collections;
using System.IO;
using System.Text;
using UnityEngine;
using VRM;
using ZeroProtocol.Player;

namespace ZeroProtocol.Dev
{
    /// <summary>
    /// Photographs the face with the Blink blend shape held at fixed values (0, 0.25, 0.5, 0.75, 1), once through the VRM proxy and once
    /// straight on the mesh, and compares the pictures (how much of the eye region changes). Shows whether the lid really closes in the game.
    /// </summary>
    public class EyeCloseShots : MonoBehaviour
    {
        public string outputDir = "";
        public bool finished;
        readonly StringBuilder log = new StringBuilder();

        IEnumerator Start()
        {
            Directory.CreateDirectory(outputDir);
            var player = FindFirstObjectByType<YoruController>();
            var anim = player.animator;
            var blinkComp = anim.GetComponent<YoruBlink>();
            blinkComp.enabled = false;
            var proxy = anim.GetComponent<VRMBlendShapeProxy>();
            var key = BlendShapeKey.CreateFromPreset(BlendShapePreset.Blink);
            SkinnedMeshRenderer faceSmr = null; int idx = -1;
            foreach (var smr in anim.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                if (smr.sharedMesh != null && (idx = smr.sharedMesh.GetBlendShapeIndex("Fcl_EYE_Close")) >= 0) { faceSmr = smr; break; }
            var camGo = new GameObject("EyeShotCam");
            var cam = camGo.AddComponent<Camera>();
            cam.enabled = false;
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.20f, 0.23f, 0.30f);
            cam.fieldOfView = 8f;
            cam.nearClipPlane = 0.05f;
            var lEye = anim.GetBoneTransform(HumanBodyBones.LeftEye);
            var rEye = anim.GetBoneTransform(HumanBodyBones.RightEye);
            yield return new WaitForSeconds(1.0f);
            float[] ws = { 0f, 0.25f, 0.5f, 0.75f, 1f };
            var shotsProxy = new Color[ws.Length][];
            var shotsMesh = new Color[ws.Length][];
            for (int pass = 0; pass < 2; pass++)
            {
                for (int i = 0; i < ws.Length; i++)
                {
                    if (pass == 0) proxy.ImmediatelySetValue(key, ws[i]);
                    else faceSmr.SetBlendShapeWeight(idx, ws[i] * 100f);
                    yield return null;
                    yield return null;
                    yield return new WaitForEndOfFrame();
                    var px = Shot(cam, lEye, rEye, (pass == 0 ? "proxy_" : "mesh_") + (ws[i] * 100f).ToString("F0"));
                    if (pass == 0) shotsProxy[i] = px; else shotsMesh[i] = px;
                    log.AppendLine((pass == 0 ? "via proxy " : "via mesh  ") + "weight " + ws[i].ToString("F2") + ": mesh weight now " + faceSmr.GetBlendShapeWeight(idx).ToString("F1")
                        + ", eye region changed vs open: " + Diff(shotsProxy[0] ?? shotsMesh[0], px).ToString("F4"));
                }
            }
            proxy.ImmediatelySetValue(key, 0f);
            blinkComp.enabled = true;
            File.WriteAllText(Path.Combine(outputDir, "eye_close_shots.txt"), log.ToString());
            Destroy(camGo);
            finished = true;
        }

        static float Diff(Color[] a, Color[] b)
        {
            if (a == null || b == null || a.Length != b.Length) return -1f;
            double s = 0;
            for (int i = 0; i < a.Length; i++) s += System.Math.Abs(a[i].r - b[i].r) + System.Math.Abs(a[i].g - b[i].g) + System.Math.Abs(a[i].b - b[i].b);
            return (float)(s / (3.0 * a.Length));
        }

        Color[] Shot(Camera cam, Transform lEye, Transform rEye, string name)
        {
            Vector3 c = (lEye.position + rEye.position) * 0.5f;
            Vector3 fwd = lEye.root.forward;
            cam.transform.position = c + fwd * 0.7f;
            cam.transform.LookAt(c);
            var rt = new RenderTexture(720, 360, 24, RenderTextureFormat.ARGB32);
            cam.targetTexture = rt;
            cam.Render();
            RenderTexture.active = rt;
            var tex = new Texture2D(rt.width, rt.height, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, rt.width, rt.height), 0, 0);
            tex.Apply();
            File.WriteAllBytes(Path.Combine(outputDir, name + ".png"), tex.EncodeToPNG());
            var px = tex.GetPixels();
            RenderTexture.active = null;
            cam.targetTexture = null;
            Destroy(tex); rt.Release(); Destroy(rt);
            return px;
        }
    }
}
