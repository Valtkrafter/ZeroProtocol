using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEngine;
using ZeroProtocol.Player;

namespace ZeroProtocol.Dev
{
    /// <summary>
    /// Play Mode check of the sprint (Shift held + W): ground speed and its wobble, cadence, foot slide of the planted toe joint and of the shoe sole,
    /// pelvis height and sway, head on the centre line, tail, bust / hair / ears, next to the numbers Blender measured on the same run
    /// (Blender/Yoru_Run_gait.json, Yoru_Run_reference.json). Everything is sampled at the end of the frame.
    /// The planted foot of the run is the TOE JOINT (Blender: 54.4 mm above the floor, 0.0 mm error per frame).
    /// </summary>
    public class RunVerifyTest : MonoBehaviour
    {
        public string outputDir = "";
        public string blenderGaitJson = "";
        public string blenderReferenceJson = "";
        public bool finished;
        readonly StringBuilder log = new StringBuilder();
        YoruController player;
        GameInput input;
        Animator anim;
        Camera shotCam;

        void Log(string s) { log.AppendLine(s); }

        void Shot(string name, Vector3 offset, float lookHeight, float orthoSize)
        {
            var root = player.transform;
            Vector3 o = root.right * offset.x + Vector3.up * offset.y + root.forward * offset.z;
            shotCam.transform.position = root.position + o;
            shotCam.transform.LookAt(root.position + Vector3.up * lookHeight);
            shotCam.orthographicSize = orthoSize;
            var rt = new RenderTexture(540, 720, 24, RenderTextureFormat.ARGB32);
            shotCam.targetTexture = rt;
            shotCam.Render();
            RenderTexture.active = rt;
            var tex = new Texture2D(rt.width, rt.height, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, rt.width, rt.height), 0, 0);
            tex.Apply();
            File.WriteAllBytes(Path.Combine(outputDir, name + ".png"), tex.EncodeToPNG());
            RenderTexture.active = null;
            shotCam.targetTexture = null;
            Destroy(tex); rt.Release(); Destroy(rt);
        }

        static Transform FindDeep(Transform root, string name)
        {
            if (root.name == name) return root;
            for (int i = 0; i < root.childCount; i++)
            {
                var r = FindDeep(root.GetChild(i), name);
                if (r != null) return r;
            }
            return null;
        }

        static float Percentile(List<float> v, float p)
        {
            if (v.Count == 0) return 0f;
            var s = v.OrderBy(x => x).ToList();
            return s[Mathf.Clamp(Mathf.RoundToInt(p * (s.Count - 1)), 0, s.Count - 1)];
        }

        class Joints
        {
            public readonly List<Transform> t = new List<Transform>();
            public readonly List<Quaternion> rest = new List<Quaternion>();
            public float max, sum; public long n;
            public Joints(IEnumerable<Transform> ts) { foreach (var x in ts) { t.Add(x); rest.Add(x.localRotation); } }
            public void Sample()
            {
                for (int i = 0; i < t.Count; i++)
                {
                    float a = Quaternion.Angle(t[i].localRotation, rest[i]);
                    max = Mathf.Max(max, a); sum += a; n++;
                }
            }
            public string Text { get { return "max " + max.ToString("F1") + " mean " + (n > 0 ? sum / n : 0f).ToString("F1") + " (" + t.Count + " joints)"; } }
        }

        /// <summary>One foot: the toe joint is planted while it stays within 3 mm of its planted height; slide while planted, drift over a whole stance.</summary>
        class Foot
        {
            public Transform toe;
            public bool planted, prevPlanted;
            public Vector3 start, prev;
            public int frames, touchdowns;
            public float startTime;
            public readonly List<float> slide = new List<float>();
            public readonly List<float> drift = new List<float>();
            public readonly List<float> stanceMs = new List<float>();
            public void Step(float floorY, float plantedHeight, float dt, float now)
            {
                prevPlanted = planted;
                planted = toe.position.y - floorY < plantedHeight + 0.003f;
                Vector3 p = toe.position;
                if (planted && prevPlanted)
                {
                    Vector3 v = (p - prev) / dt; v.y = 0f;
                    slide.Add(v.magnitude);
                    frames++;
                }
                if (planted && !prevPlanted) { touchdowns++; start = p; frames = 0; startTime = now; }
                if (!planted && prevPlanted && frames >= 3)
                {
                    drift.Add(Vector2.Distance(new Vector2(start.x, start.z), new Vector2(prev.x, prev.z)) * 1000f);
                    stanceMs.Add((now - startTime) * 1000f);
                }
                prev = p;
            }
        }

        IEnumerator Start()
        {
            player = FindFirstObjectByType<YoruController>();
            input = player.GetComponent<GameInput>();
            anim = player.animator;
            Directory.CreateDirectory(outputDir);
            var root = player.transform;
            var blink = anim.GetComponent<YoruBlink>();
            var motion = anim.GetComponent<YoruSecondaryMotion>();
            Log("controller " + (anim.runtimeAnimatorController == null ? "NONE" : anim.runtimeAnimatorController.name) + ", walkSpeed " + player.walkSpeed + ", runSpeed " + player.runSpeed + ", clipRunSpeed " + player.clipRunSpeed
                + ", runGaitSpeedVariation " + player.runGaitSpeedVariation + ", frame rate of this run " + (1f / Mathf.Max(0.0001f, Time.smoothDeltaTime)).ToString("F0") + " fps, spring steps per second " + (motion != null ? motion.springStepsPerSecond.ToString("F0") : "?"));

            string bSpeed = "?", bSteps = "?", bStepLen = "?", bPelvis = "?", bSway = "?", bTail = "?", bBust = "?", bEar = "?", bHair = "?";
            float bMin = 4.713f, bMax = 5.113f;
            try
            {
                var gj = Newtonsoft.Json.Linq.JObject.Parse(File.ReadAllText(blenderGaitJson));
                var rj = Newtonsoft.Json.Linq.JObject.Parse(File.ReadAllText(blenderReferenceJson));
                bSpeed = ((float)gj["speed"]).ToString("F3");
                bSteps = ((float)gj["steps_per_minute"]).ToString("F1");
                bStepLen = ((float)gj["step_length"]).ToString("F3");
                bPelvis = ((float)gj["run_report"]["pelvis_z_mm"][2]).ToString("F1") + " mm";
                bSway = ((float)gj["pelvis_sway"] * 1000f).ToString("F1");
                var sp = gj["speed_variation"]["speed_per_frame"].Select(x => (float)x).ToList();
                bMin = sp.Min(); bMax = sp.Max();
                var tt = rj["tail_tip_vs_hips"];
                bTail = "side " + ((float)tt["side_mm"]).ToString("F0") + " mm, height " + ((float)tt["height_mm"]).ToString("F0") + " mm";
                bBust = "max " + ((float)rj["bust_first"][0]).ToString("F1") + " mean " + ((float)rj["bust_first"][1]).ToString("F1");
                bEar = "max " + ((float)rj["ear_tip"][0]).ToString("F1") + " mean " + ((float)rj["ear_tip"][1]).ToString("F1");
                bHair = "max " + ((float)rj["hair_first"][0]).ToString("F1") + " mean " + ((float)rj["hair_first"][1]).ToString("F1");
            }
            catch (System.Exception e) { Log("Blender numbers not read: " + e.Message); }

            var camGo = new GameObject("RunShotCam");
            shotCam = camGo.AddComponent<Camera>();
            shotCam.enabled = false;
            shotCam.clearFlags = CameraClearFlags.SolidColor;
            shotCam.backgroundColor = new Color(0.20f, 0.23f, 0.30f);
            shotCam.orthographic = true;

            Transform hips = anim.GetBoneTransform(HumanBodyBones.Hips), head = anim.GetBoneTransform(HumanBodyBones.Head);
            Transform tailTip = FindDeep(anim.transform, "J_Opt_C_CatTail8_01");
            var all = anim.GetComponentsInChildren<Transform>(true);
            var feet = new[] { new Foot { toe = anim.GetBoneTransform(HumanBodyBones.LeftToes) }, new Foot { toe = anim.GetBoneTransform(HumanBodyBones.RightToes) } };

            yield return new WaitForSeconds(1.2f);

            // ---- what the inputs do
            Log("--- what each input does ---");
            foreach (var c in new[] { ("W only", new Vector2(0f, 1f), false, player.walkSpeed), ("W + Shift held", new Vector2(0f, 1f), true, player.runSpeed), ("tilt 0.25 + Shift held", new Vector2(0f, 0.25f), true, player.runSpeed * 0.25f / player.walkTilt) })
            {
                input.MoveOverride = c.Item2; input.SprintOverride = c.Item3;
                yield return new WaitForSeconds(2.2f);
                Log(string.Format("input {0,-24} -> ground speed {1:F2} m/s (wanted {2:F2}), IsSprinting {3}, animator Speed {4:F2}, LocoMult {5:F2}", c.Item1, player.HorizontalSpeed, c.Item4, player.IsSprinting, anim.GetFloat("Speed"), anim.GetFloat("LocoMult")));
                input.MoveOverride = Vector2.zero; input.SprintOverride = false;
                yield return new WaitForSeconds(0.8f);
            }

            // ---- the sprint itself
            Log("--- sprint at " + player.runSpeed.ToString("F2") + " m/s ---");
            var cc = player.GetComponent<CharacterController>();
            cc.enabled = false; root.position = new Vector3(2f, 0.05f, -36f); root.rotation = Quaternion.identity; cc.enabled = true;
            yield return new WaitForSeconds(1.5f);
            float floorY = root.position.y;
            var bust = new Joints(all.Where(x => x.name.StartsWith("J_Sec_L_Bust") || x.name.StartsWith("J_Sec_R_Bust")));
            var ears = new Joints(all.Where(x => x.name.StartsWith("J_Opt_L_CatEar") || x.name.StartsWith("J_Opt_R_CatEar")));
            var hair = new Joints(all.Where(x => x.name.StartsWith("J_Sec_Hair")));
            var hairFirst = new Joints(all.Where(x => x.name.StartsWith("J_Sec_Hair") && x.name.EndsWith("_01")));
            var bustFirst = new Joints(all.Where(x => x.name == "J_Sec_L_Bust1" || x.name == "J_Sec_R_Bust1"));
            float plantedHeight = 0.0544f;                                            // Blender: the toe joint stays 54.4 mm above the floor while planted

            input.MoveOverride = new Vector2(0f, 1f); input.SprintOverride = true;
            yield return new WaitForSeconds(2.2f);                                    // reach the speed, the spring bones find their rhythm
            float t0 = Time.time, tEnd = t0 + 4.2f;
            int n = 0, offBoth = 0;
            float hipsYmin = 9f, hipsYmax = -9f, hipsXmin = 9f, hipsXmax = -9f, headXmin = 9f, headXmax = -9f, headYmin = 9f, headYmax = -9f;
            var rootSpeed = new List<float>(); var hipsSeries = new List<float>(); var factorSeries = new List<float>();
            var tailSide = new List<float>(); var tailHigh = new List<float>();
            Vector3 prevRoot = root.position;
            Vector3 tailMin = Vector3.one * 9f, tailMax = Vector3.one * -9f;
            float blinkMax = 0f;
            float[] shotAt = { 0.4f, 0.55f, 0.7f, 0.85f };
            int shot = 0;
            while (Time.time < tEnd)
            {
                yield return new WaitForEndOfFrame();
                float dt = Time.deltaTime;
                if (dt <= 0f) continue;
                n++;
                var dRoot = root.position - prevRoot; dRoot.y = 0f; prevRoot = root.position;
                rootSpeed.Add(dRoot.magnitude / dt);
                hipsSeries.Add(hips.position.y - floorY);
                factorSeries.Add(player.GaitSpeedFactor);
                Vector3 hl = root.InverseTransformPoint(hips.position);
                hipsYmin = Mathf.Min(hipsYmin, hips.position.y - floorY); hipsYmax = Mathf.Max(hipsYmax, hips.position.y - floorY);
                hipsXmin = Mathf.Min(hipsXmin, hl.x); hipsXmax = Mathf.Max(hipsXmax, hl.x);
                Vector3 hd = root.InverseTransformPoint(head.position);
                headXmin = Mathf.Min(headXmin, hd.x); headXmax = Mathf.Max(headXmax, hd.x);
                headYmin = Mathf.Min(headYmin, hd.y); headYmax = Mathf.Max(headYmax, hd.y);
                foreach (var f in feet) f.Step(floorY, plantedHeight, dt, Time.time);
                if (!feet[0].planted && !feet[1].planted) offBoth++;
                if (tailTip != null)
                {
                    var rp = root.InverseTransformPoint(tailTip.position);
                    var tp = rp - root.InverseTransformPoint(hips.position);
                    tailMin = Vector3.Min(tailMin, tp); tailMax = Vector3.Max(tailMax, tp);
                    tailSide.Add(tp.x); tailHigh.Add(tp.y);
                }
                bust.Sample(); bustFirst.Sample(); ears.Sample(); hair.Sample(); hairFirst.Sample();
                if (blink != null) blinkMax = Mathf.Max(blinkMax, blink.Lid);
                float tt = Time.time - t0;
                if (shot < shotAt.Length && tt >= shotAt[shot])
                {
                    Shot("side_" + shot, new Vector3(3.2f, 0.95f, 0f), 0.8f, 0.95f);
                    Shot("back_" + shot, new Vector3(0f, 1.0f, -3.2f), 0.8f, 0.95f);
                    Shot("front_" + shot, new Vector3(1.6f, 1.1f, 3.0f), 0.8f, 0.95f);
                    Shot("tail_" + shot, new Vector3(0.9f, 1.2f, -2.2f), 0.95f, 0.55f);
                    shot++;
                }
            }
            float dur = Time.time - t0;
            input.MoveOverride = Vector2.zero; input.SprintOverride = false;

            double mS = rootSpeed.Average(), mH = hipsSeries.Average(), cov = 0, vS = 0, vH = 0;
            for (int i = 0; i < rootSpeed.Count; i++) { double a = rootSpeed[i] - mS, b = hipsSeries[i] - mH; cov += a * b; vS += a * a; vH += b * b; }
            double corr = cov / System.Math.Sqrt(vS * vH + 1e-12);
            Log(string.Format("ground speed of the character per frame: 2 % {0:F3}, 98 % {1:F3}, mean {2:F3} m/s (Blender model {3:F3} .. {4:F3}, mean {5}); factor {6:F3} .. {7:F3}; correlation with the pelvis height {8:F2} (the model dips while a foot is on the ground = the pelvis is low: negative)",
                Percentile(rootSpeed, 0.02f), Percentile(rootSpeed, 0.98f), mS, bMin, bMax, bSpeed, factorSeries.Min(), factorSeries.Max(), corr));
            int td = feet[0].touchdowns + feet[1].touchdowns;
            float stepsPerSecond = td / dur;
            Log(string.Format("samples {0} over {1:F1} s ({2:F0} fps); toe joint touchdowns L {3} R {4} = {5:F0} steps/min (Blender {6}), step length {7:F3} m (Blender {8}; the count is +-1 of the window)",
                n, dur, n / dur, feet[0].touchdowns, feet[1].touchdowns, stepsPerSecond * 60f, bSteps, mS / Mathf.Max(0.01f, stepsPerSecond), bStepLen));
            var slide = feet[0].slide.Concat(feet[1].slide).ToList();
            var drift = feet[0].drift.Concat(feet[1].drift).ToList();
            var stance = feet[0].stanceMs.Concat(feet[1].stanceMs).ToList();
            Log(string.Format("planted toe joint: horizontal speed while planted (m/s, {0} frames): median {1:F3}, 90 % below {2:F3}, 99 % below {3:F3}, largest {4:F3}   (planted = 0)",
                slide.Count, Percentile(slide, 0.5f), Percentile(slide, 0.9f), Percentile(slide, 0.99f), slide.Count > 0 ? slide.Max() : 0f));
            Log(string.Format("drift of the planted toe joint over one whole stance (mm, {0} stances of {1:F0} ms, Blender stance 133 ms): median {2:F1}, largest {3:F1}", drift.Count, Percentile(stance, 0.5f), Percentile(drift, 0.5f), drift.Count > 0 ? drift.Max() : 0f));
            Log(string.Format("both toe joints off the ground {0:F0} % of the time (Blender: both feet off the ground for 50 % of the cycle)", 100f * offBoth / Mathf.Max(1, n)));
            Log(string.Format("pelvis height range {0:F4} .. {1:F4} m = {2:F1} mm (Blender {3})", hipsYmin, hipsYmax, (hipsYmax - hipsYmin) * 1000f, bPelvis));
            Log(string.Format("pelvis side shift {0:F1} .. {1:F1} mm = +-{2:F1} mm (Blender +-{3} mm)", hipsXmin * 1000f, hipsXmax * 1000f, (hipsXmax - hipsXmin) * 500f, bSway));
            Log(string.Format("head side position {0:F1} .. {1:F1} mm (spec: within +-5 mm of the centre line), head height range {2:F1} mm", headXmin * 1000f, headXmax * 1000f, (headYmax - headYmin) * 1000f));
            Log(string.Format("tail tip relative to the hips (character frame): side {0:F0} mm, height {1:F0} mm (2 %..98 %: side {2:F0}, height {3:F0}); Blender: {4}; tail rest blend {5:F2}, sprint arch {6}",
                (tailMax.x - tailMin.x) * 1000f, (tailMax.y - tailMin.y) * 1000f, (Percentile(tailSide, 0.98f) - Percentile(tailSide, 0.02f)) * 1000f, (Percentile(tailHigh, 0.98f) - Percentile(tailHigh, 0.02f)) * 1000f, bTail,
                motion != null ? motion.TailRestBlend : 0f, motion != null ? "on" : "?"));
            Log("spring bones, swing away from the rest direction (deg), Blender simulation in brackets:");
            Log("   bust, first joints  " + bustFirst.Text + "   (Blender: " + bBust + ")");
            Log("   ear joints          " + ears.Text + "   (Blender tip: " + bEar + ")");
            Log("   hair, first joints  " + hairFirst.Text + "   (Blender: " + bHair + ")");
            Log("   hair, all joints    " + hair.Text);
            Log("blink while sprinting: max lid " + blinkMax.ToString("F2"));

            yield return new WaitForSeconds(1.2f);
            Log("after stop: ground speed " + player.HorizontalSpeed.ToString("F2") + ", animator Speed " + anim.GetFloat("Speed").ToString("F2"));
            File.WriteAllText(Path.Combine(outputDir, "run_verify.txt"), log.ToString());
            Destroy(camGo);
            finished = true;
        }
    }
}
