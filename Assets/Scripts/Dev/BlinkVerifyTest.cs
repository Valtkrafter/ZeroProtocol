using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEngine;
using VRM;
using ZeroProtocol.Player;

namespace ZeroProtocol.Dev
{
    /// <summary>
    /// Checks the blink of Yoru number by number against Blender (Blender/Yoru_Blink.json, made by Blender/scripts/build_blink.py):
    ///   1. the C# blink model gives the same blinks as the Python model for the same seed (start, strength, close / hold / open times, lid per frame)
    ///   2. in Play Mode the YoruBlink component, started with that seed, sends the same lid value to the face as the model says at its own clock,
    ///      and the blend shape weight on the face mesh is really that value (the whole chain proxy -> renderer)
    ///   3. pictures of the face with the lid open, half, and shut, and the blink graph over time
    /// </summary>
    public class BlinkVerifyTest : MonoBehaviour
    {
        public string outputDir = "";
        public string blinkJson = "";
        public bool finished;
        readonly StringBuilder log = new StringBuilder();

        void Log(string s) { log.AppendLine(s); }

        [System.Serializable]
        class JBlink { public double start, amp, close, hold, open, end; }
        [System.Serializable]
        class JData
        {
            public int seed, frames, fps;
            public double seconds;
            public List<JBlink> blinks;
            public double[] weights_per_frame;
            public Dictionary<string, double> @params;
        }

        IEnumerator Start()
        {
            Directory.CreateDirectory(outputDir);
            var d = Newtonsoft.Json.JsonConvert.DeserializeObject<JData>(File.ReadAllText(blinkJson));
            Log("Blender data: seed " + d.seed + ", " + d.frames + " frames @ " + d.fps + " fps = " + d.seconds.ToString("F2") + " s, " + d.blinks.Count + " blinks");

            // ---- 1. the model itself (no Unity involved)
            var groups = BlinkModel.Groups((uint)d.seed, d.seconds);
            var blinks = new List<Blink>();
            foreach (var g in groups) blinks.AddRange(g);
            double worst = 0.0;
            string worstWhat = "-";
            bool sameCount = blinks.Count == d.blinks.Count;
            for (int i = 0; i < Mathf.Min(blinks.Count, d.blinks.Count); i++)
            {
                var a = blinks[i]; var b = d.blinks[i];
                double[] diffs = { a.Start - b.start, a.Amp - b.amp, a.Close - b.close, a.Hold - b.hold, a.Open - b.open, a.End - b.end };
                string[] names = { "start", "amp", "close", "hold", "open", "end" };
                for (int k = 0; k < diffs.Length; k++)
                    if (System.Math.Abs(diffs[k]) > worst) { worst = System.Math.Abs(diffs[k]); worstWhat = "blink " + i + " " + names[k]; }
            }
            Log("model parity: C# " + blinks.Count + " blinks, Python " + d.blinks.Count + " blinks (same count: " + sameCount + "); largest difference of any start / strength / close / hold / open / end: "
                + worst.ToString("E2") + " s (" + worstWhat + ")");
            double worstW = 0.0;
            for (int f = 0; f < d.frames; f++)
            {
                double w = BlinkModel.Weight(blinks, f / (double)d.fps);
                worstW = System.Math.Max(worstW, System.Math.Abs(w - d.weights_per_frame[f]));
            }
            Log("lid value on all " + d.frames + " frames of the Blender timeline: largest difference to Blender " + worstW.ToString("E2"));
            // the numbers inside the model against the numbers Blender used
            var sb = new StringBuilder();
            var pr = d.@params;
            string[] keys = { "median_interval", "sigma", "min_interval", "max_interval", "first_min", "first_max", "p_partial", "partial_lo", "partial_hi", "t_close", "close_spread", "open_ratio_lo", "open_ratio_hi", "hold_lo", "hold_hi", "p_double", "overlap_lo", "overlap_hi", "double_min_onset", "amp2_lo", "amp2_hi", "close_warp", "open_warp" };
            double[] mine = { BlinkModel.MedianInterval, BlinkModel.Sigma, BlinkModel.MinInterval, BlinkModel.MaxInterval, BlinkModel.FirstMin, BlinkModel.FirstMax, BlinkModel.PPartial, BlinkModel.PartialLo, BlinkModel.PartialHi, BlinkModel.TClose, BlinkModel.CloseSpread, BlinkModel.OpenRatioLo, BlinkModel.OpenRatioHi, BlinkModel.HoldLo, BlinkModel.HoldHi, BlinkModel.PDouble, BlinkModel.OverlapLo, BlinkModel.OverlapHi, BlinkModel.DoubleMinOnset, BlinkModel.Amp2Lo, BlinkModel.Amp2Hi, BlinkModel.CloseWarp, BlinkModel.OpenWarp };
            int bad = 0;
            for (int i = 0; i < keys.Length; i++)
            {
                double theirs;
                if (pr == null || !pr.TryGetValue(keys[i], out theirs)) { sb.Append(keys[i] + " missing; "); bad++; continue; }
                if (System.Math.Abs(theirs - mine[i]) > 1e-12) { sb.Append(keys[i] + " " + theirs + " vs " + mine[i] + "; "); bad++; }
            }
            Log("model constants: " + keys.Length + " compared with the numbers Blender used, " + (bad == 0 ? "all equal" : bad + " DIFFER: " + sb));
            // a long run of the model: rate and shape
            var hour = BlinkModel.Groups(7u, 3600.0);
            int nb = 0, nd = 0, np = 0; double ivSum = 0.0; int ivN = 0; double ivMin = 1e9, ivMax = 0.0;
            for (int i = 0; i < hour.Count; i++)
            {
                nb += hour[i].Length; if (hour[i].Length == 2) nd++; if (hour[i][0].Amp < 0.999) np++;
                if (i > 0) { double iv = hour[i][0].Start - hour[i - 1][0].Start; ivSum += iv; ivN++; ivMin = System.Math.Min(ivMin, iv); ivMax = System.Math.Max(ivMax, iv); }
            }
            Log(string.Format("one hour of blinks (seed 7): {0} blinks in {1} groups = {2:F1} per minute, start to start of the groups mean {3:F2} s (min {4:F2}, max {5:F2}), double {6:F0} %, weaker {7:F0} %",
                nb, hour.Count, nb / 60.0, ivSum / ivN, ivMin, ivMax, 100.0 * nd / hour.Count, 100.0 * np / hour.Count));

            // ---- 2. Play Mode: the component, the proxy and the mesh
            var player = FindFirstObjectByType<YoruController>();
            var anim = player.animator;
            var comp = anim.GetComponent<YoruBlink>();
            var proxy = anim.GetComponent<VRMBlendShapeProxy>();
            var key = BlendShapeKey.CreateFromPreset(BlendShapePreset.Blink);
            SkinnedMeshRenderer faceSmr = null;
            int closeIndex = -1;
            foreach (var smr in anim.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                if (smr.sharedMesh == null) continue;
                int idx = smr.sharedMesh.GetBlendShapeIndex("Fcl_EYE_Close");
                if (idx >= 0) { faceSmr = smr; closeIndex = idx; break; }
            }
            Log("face mesh with Fcl_EYE_Close: " + (faceSmr != null ? faceSmr.name + " (blend shape " + closeIndex + " of " + faceSmr.sharedMesh.blendShapeCount + ")" : "NOT FOUND"));

            var camGo = new GameObject("BlinkShotCam");
            var cam = camGo.AddComponent<Camera>();
            cam.enabled = false;
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.20f, 0.23f, 0.30f);
            cam.fieldOfView = 12f;
            cam.nearClipPlane = 0.05f;
            var head = anim.GetBoneTransform(HumanBodyBones.Head);
            var lEye = anim.GetBoneTransform(HumanBodyBones.LeftEye);
            var rEye = anim.GetBoneTransform(HumanBodyBones.RightEye);

            comp.enabled = true;
            comp.Restart(d.seed);
            yield return null;
            double maxErrLid = 0.0, maxErrMesh = 0.0, maxErrProxy = 0.0;
            float maxLid = 0f; int frames = 0;
            var starts = new List<double>();
            float prevLid = 0f;
            var shots = new Dictionary<string, bool>();
            var series = new StringBuilder();
            double runFor = System.Math.Min(d.seconds, 26.0);
            while (comp.Clock < runFor)
            {
                yield return new WaitForEndOfFrame();                       // the frame is finished: the lid value, the blend shape and the picture belong together
                frames++;
                double clock = comp.Clock;
                double expected = BlinkModel.Weight(blinks, clock);
                maxErrLid = System.Math.Max(maxErrLid, System.Math.Abs(comp.Lid - expected));
                if (proxy != null) maxErrProxy = System.Math.Max(maxErrProxy, System.Math.Abs(proxy.GetValue(key) - comp.Lid));
                if (faceSmr != null) maxErrMesh = System.Math.Max(maxErrMesh, System.Math.Abs(faceSmr.GetBlendShapeWeight(closeIndex) / 100.0 - comp.Lid));
                maxLid = Mathf.Max(maxLid, comp.Lid);
                if (prevLid < 0.02f && comp.Lid >= 0.02f) starts.Add(clock);
                prevLid = comp.Lid;
                if (comp.Lid > 0.97f && !shots.ContainsKey("shut")) { Shot(cam, head, lEye, rEye, "face_shut"); shots["shut"] = true; }
                if (comp.Lid > 0.45f && comp.Lid < 0.6f && prevLid > 0.1f && !shots.ContainsKey("half")) { Shot(cam, head, lEye, rEye, "face_half"); shots["half"] = true; }
                if (comp.Lid == 0f && clock > 0.4 && !shots.ContainsKey("open")) { Shot(cam, head, lEye, rEye, "face_open"); shots["open"] = true; }
                if (series.Length < 3000 && frames % 12 == 0) series.Append(clock.ToString("F2") + ":" + comp.Lid.ToString("F2") + " ");
            }
            Log(string.Format("Play Mode: {0} frames over {1:F1} s of the blink clock; blinks started {2} (Blender {3} in 26 s)", frames, comp.Clock, comp.BlinksStarted, d.blinks.Count));
            Log(string.Format("component lid vs model at its own clock: largest difference {0:E2}; proxy value vs component {1:E2}; blend shape weight on the face mesh / 100 vs component {2:E2}  (all must be about 0)", maxErrLid, maxErrProxy, maxErrMesh));
            Log("lid reached " + maxLid.ToString("F3") + " (must be 1); blink starts seen in Play Mode (clock s): " + string.Join(", ", starts.ConvertAll(s => s.ToString("F2")).ToArray()));
            var bs = new List<string>();
            foreach (var b in blinks) if (b.End < runFor) bs.Add(b.Start.ToString("F2"));
            Log("blink starts of the model / Blender (s):                          " + string.Join(", ", bs.ToArray()));

            // the lid really goes to 0 afterwards
            yield return new WaitForSeconds(0.8f);
            comp.fixedSeed = -1;
            Log("lid samples (clock:lid) every 12th frame: " + series);
            File.WriteAllText(Path.Combine(outputDir, "blink_verify.txt"), log.ToString());
            Destroy(camGo);
            finished = true;
        }

        void Shot(Camera cam, Transform head, Transform lEye, Transform rEye, string name)
        {
            Vector3 c = (lEye != null && rEye != null) ? (lEye.position + rEye.position) * 0.5f : head.position + Vector3.up * 0.07f;
            Vector3 fwd = head.root.forward;
            cam.transform.position = c + fwd * 0.9f + Vector3.up * 0.0f;
            cam.transform.LookAt(c + Vector3.down * 0.01f);
            var rt = new RenderTexture(720, 480, 24, RenderTextureFormat.ARGB32);
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
