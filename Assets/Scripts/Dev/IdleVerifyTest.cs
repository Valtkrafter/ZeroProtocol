using System.Collections;
using System.IO;
using System.Text;
using UnityEngine;
using VRM;
using ZeroProtocol.Player;

namespace ZeroProtocol.Dev
{
    /// <summary>
    /// Play Mode check of the idle: samples the pose over one and a half loops and writes numbers
    /// (feet must stay planted, tail / ears / blink must move, hands must hang where the Blender idle put them).
    /// </summary>
    public class IdleVerifyTest : MonoBehaviour
    {
        public string outputDir = "";
        public bool finished;

        void Shot(Camera cam, Transform root, string name, Vector3 offset)
        {
            cam.transform.position = root.position + Vector3.up * 0.8f + offset;
            cam.transform.LookAt(root.position + Vector3.up * 0.7f);
            var rt = new RenderTexture(540, 720, 24, RenderTextureFormat.ARGB32);
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

        IEnumerator Start()
        {
            var player = FindFirstObjectByType<YoruController>();
            var anim = player.animator;
            var log = new StringBuilder();
            Directory.CreateDirectory(outputDir);
            log.AppendLine("controller: " + (anim.runtimeAnimatorController == null ? "NONE" : anim.runtimeAnimatorController.name) +
                           ", state Locomotion: " + anim.GetCurrentAnimatorStateInfo(0).IsName("Locomotion"));

            Transform lf = anim.GetBoneTransform(HumanBodyBones.LeftFoot), rf = anim.GetBoneTransform(HumanBodyBones.RightFoot);
            Transform lh = anim.GetBoneTransform(HumanBodyBones.LeftHand), rh = anim.GetBoneTransform(HumanBodyBones.RightHand);
            Transform head = anim.GetBoneTransform(HumanBodyBones.Head), hips = anim.GetBoneTransform(HumanBodyBones.Hips);
            Transform tailTip = null, earL = null;
            foreach (var t in anim.GetComponentsInChildren<Transform>(true))
            {
                if (t.name == "J_Opt_C_CatTail8_01") tailTip = t;
                if (t.name == "J_Opt_L_CatEar2_01") earL = t;
            }
            var proxy = anim.GetComponent<VRMBlendShapeProxy>();
            var blinkKey = BlendShapeKey.CreateFromPreset(BlendShapePreset.Blink);

            yield return new WaitForSeconds(0.5f);
            Transform root = player.transform;
            Vector3 lf0 = root.InverseTransformPoint(lf.position), rf0 = root.InverseTransformPoint(rf.position);
            float maxLf = 0f, maxRf = 0f, minHipsY = 9f, maxHipsY = -9f, maxBlink = 0f;
            Vector3 tailMin = Vector3.one * 9f, tailMax = Vector3.one * -9f, earMin = Vector3.one * 9f, earMax = Vector3.one * -9f;
            Vector3 lhMin = Vector3.one * 9f, lhMax = Vector3.one * -9f, rhMin = Vector3.one * 9f, rhMax = Vector3.one * -9f;
            float headYawMin = 999f, headYawMax = -999f;
            var camGo = new GameObject("IdleShotCam");
            var shotCam = camGo.AddComponent<Camera>();
            shotCam.enabled = false;
            shotCam.clearFlags = CameraClearFlags.SolidColor;
            shotCam.backgroundColor = new Color(0.20f, 0.23f, 0.30f);
            shotCam.orthographic = true;
            shotCam.orthographicSize = 0.75f;
            float[] shotTimes = { 2.0f, 5.0f, 8.0f };
            int shotIndex = 0;
            float t0 = Time.time;
            int samples = 0;
            var series = new StringBuilder();
            float nextSeries = 0f;
            while (Time.time - t0 < 14.0f)
            {
                yield return null;
                samples++;
                if (shotIndex < shotTimes.Length && Time.time - t0 >= shotTimes[shotIndex])
                {
                    Shot(shotCam, root, "side_" + shotIndex, root.right * 6f);
                    Shot(shotCam, root, "back_" + shotIndex, -root.forward * 6f);
                    shotIndex++;
                }
                if (Time.time - t0 >= nextSeries)
                {
                    nextSeries += 0.5f;
                    var th = hips.InverseTransformPoint(tailTip.position);
                    series.Append((Time.time - t0).ToString("F1") + "s:(" + th.x.ToString("F2") + "," + th.y.ToString("F2") + "," + th.z.ToString("F2") + ") ");
                }
                maxLf = Mathf.Max(maxLf, (root.InverseTransformPoint(lf.position) - lf0).magnitude);
                maxRf = Mathf.Max(maxRf, (root.InverseTransformPoint(rf.position) - rf0).magnitude);
                float hy = root.InverseTransformPoint(hips.position).y;
                minHipsY = Mathf.Min(minHipsY, hy); maxHipsY = Mathf.Max(maxHipsY, hy);
                var tp = root.InverseTransformPoint(tailTip.position);
                tailMin = Vector3.Min(tailMin, tp); tailMax = Vector3.Max(tailMax, tp);
                var ep = root.InverseTransformPoint(earL.position);
                earMin = Vector3.Min(earMin, ep); earMax = Vector3.Max(earMax, ep);
                var lp = root.InverseTransformPoint(lh.position); lhMin = Vector3.Min(lhMin, lp); lhMax = Vector3.Max(lhMax, lp);
                var rp = root.InverseTransformPoint(rh.position); rhMin = Vector3.Min(rhMin, rp); rhMax = Vector3.Max(rhMax, rp);
                float yaw = Mathf.DeltaAngle(0f, root.InverseTransformDirection(head.forward).x * 57.3f);
                headYawMin = Mathf.Min(headYawMin, yaw); headYawMax = Mathf.Max(headYawMax, yaw);
                if (proxy != null) maxBlink = Mathf.Max(maxBlink, proxy.GetValue(blinkKey));
            }
            log.AppendLine("samples " + samples + " over " + (Time.time - t0).ToString("F1") + " s");
            log.AppendLine("foot drift from its first position (mm): left " + (maxLf * 1000f).ToString("F1") + ", right " + (maxRf * 1000f).ToString("F1") + "  (planted = a few mm)");
            log.AppendLine("hips height range (m): " + minHipsY.ToString("F3") + " .. " + maxHipsY.ToString("F3"));
            log.AppendLine("left hand range (m) x " + lhMin.x.ToString("F3") + ".." + lhMax.x.ToString("F3") + " y " + lhMin.y.ToString("F3") + ".." + lhMax.y.ToString("F3") + " z " + lhMin.z.ToString("F3") + ".." + lhMax.z.ToString("F3"));
            log.AppendLine("right hand range (m) x " + rhMin.x.ToString("F3") + ".." + rhMax.x.ToString("F3") + " y " + rhMin.y.ToString("F3") + ".." + rhMax.y.ToString("F3") + " z " + rhMin.z.ToString("F3") + ".." + rhMax.z.ToString("F3"));
            log.AppendLine("tail tip travel (m): x " + (tailMax.x - tailMin.x).ToString("F3") + " y " + (tailMax.y - tailMin.y).ToString("F3") + " z " + (tailMax.z - tailMin.z).ToString("F3") + "   (must move)");
            log.AppendLine("left ear tip travel (m): x " + (earMax.x - earMin.x).ToString("F3") + " y " + (earMax.y - earMin.y).ToString("F3") + " z " + (earMax.z - earMin.z).ToString("F3"));
            log.AppendLine("blink max value seen: " + maxBlink.ToString("F2") + "   (must reach 1 within 9 s, blinks come every 2.5 to 6 s)");
            log.AppendLine("tail tip in hips space (x right, y up, z forward) every 0.5 s: " + series);
            File.WriteAllText(Path.Combine(outputDir, "idle_verify.txt"), log.ToString());
            finished = true;
        }
    }
}
