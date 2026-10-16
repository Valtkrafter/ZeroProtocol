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
    /// Play Mode check of the walk and the walk mode of the controller. It writes numbers (speed per input, cadence, foot slide on the ground,
    /// pelvis height and sway, head on the centre line, tail, bust / hair / ears, blink) next to the numbers Blender measured on the same walk
    /// (Blender/Yoru_Walk_gait.json and the tail / spring numbers of the Blender file) and saves pictures from the side, the back and the front.
    /// Everything is sampled at the end of the frame, when the animation and the controller have both finished that frame.
    /// </summary>
    public class WalkVerifyTest : MonoBehaviour
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

        IEnumerator SpeedCheck(string label, Vector2 stick, bool ctrl, float expected)
        {
            input.MoveOverride = stick;
            input.CtrlOverride = ctrl;
            yield return new WaitForSeconds(1.4f);
            float sp = player.HorizontalSpeed;
            Log(string.Format("input {0,-34} -> ground speed {1:F2} m/s (wanted {2:F2}), IsWalking {3}, animator Speed {4:F2}, LocoMult {5:F2}",
                label, sp, expected, player.IsWalking, anim.GetFloat("Speed"), anim.GetFloat("LocoMult")));
            input.MoveOverride = Vector2.zero;
            input.CtrlOverride = false;
            yield return new WaitForSeconds(0.7f);
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
                + ", frame rate of this run " + (1f / Mathf.Max(0.0001f, Time.smoothDeltaTime)).ToString("F0") + " fps, spring steps per second " + (motion != null ? motion.springStepsPerSecond.ToString("F0") : "?"));

            // the numbers of the Blender walk to compare with (Yoru_Walk_gait.json, Yoru_Walk_reference.json made by Blender/scripts/dump_reference.py)
            string bSpeed = "?", bSteps = "?", bStepLen = "?", bPelvis = "?", bSway = "?", bTail = "?", bBust = "?", bEar = "?", bHair = "?";
            try
            {
                var gj = Newtonsoft.Json.Linq.JObject.Parse(File.ReadAllText(blenderGaitJson));
                var rj = Newtonsoft.Json.Linq.JObject.Parse(File.ReadAllText(blenderReferenceJson));
                bSpeed = ((float)gj["speed"]).ToString("F3");
                bSteps = ((float)gj["steps_per_minute"]).ToString("F1");
                bStepLen = ((float)gj["step_length"]).ToString("F3");
                bPelvis = ((float)gj["spec_report"]["pelvis_z_mm"][2]).ToString("F1") + " mm, " + ((float)gj["pelvis_height_min"]).ToString("F4") + " .. " + ((float)gj["pelvis_height_max"]).ToString("F4");
                bSway = ((float)gj["pelvis_sway"] * 1000f).ToString("F1");
                var tt = rj["tail_tip_vs_hips"];
                bTail = "side " + ((float)tt["side_mm"]).ToString("F0") + " mm (x " + ((float)tt["x"][0]).ToString("F3") + " .. " + ((float)tt["x"][1]).ToString("F3") + "), height " + ((float)tt["height_mm"]).ToString("F0")
                        + " mm (" + ((float)tt["z_height"][0]).ToString("F3") + " .. " + ((float)tt["z_height"][1]).ToString("F3") + "), reach " + ((float)tt["y_reach"][0]).ToString("F3") + " .. " + ((float)tt["y_reach"][1]).ToString("F3");
                bBust = "max " + ((float)rj["bust_first"][0]).ToString("F1") + " mean " + ((float)rj["bust_first"][1]).ToString("F1");
                bEar = "max " + ((float)rj["ear_tip"][0]).ToString("F1") + " mean " + ((float)rj["ear_tip"][1]).ToString("F1");
                bHair = "max " + ((float)rj["hair_first"][0]).ToString("F1") + " mean " + ((float)rj["hair_first"][1]).ToString("F1");
            }
            catch (System.Exception e) { Log("Blender numbers not read: " + e.Message); }

            var camGo = new GameObject("WalkShotCam");
            shotCam = camGo.AddComponent<Camera>();
            shotCam.enabled = false;
            shotCam.clearFlags = CameraClearFlags.SolidColor;
            shotCam.backgroundColor = new Color(0.20f, 0.23f, 0.30f);
            shotCam.orthographic = true;

            Transform hips = anim.GetBoneTransform(HumanBodyBones.Hips), head = anim.GetBoneTransform(HumanBodyBones.Head);
            Transform lf = anim.GetBoneTransform(HumanBodyBones.LeftFoot), rf = anim.GetBoneTransform(HumanBodyBones.RightFoot);
            Transform tailTip = FindDeep(anim.transform, "J_Opt_C_CatTail8_01");
            Transform tailRoot = FindDeep(anim.transform, "J_Opt_C_CatTail1_01");
            var all = anim.GetComponentsInChildren<Transform>(true);

            yield return new WaitForSeconds(1.2f);                                   // settle on the floor, idle

            // ---- the controller and its walk mode
            Log("--- what each input does (W is the walk, Ctrl is reserved and must change nothing) ---");
            yield return SpeedCheck("W (keyboard)", new Vector2(0f, 1f), false, player.walkSpeed);
            yield return SpeedCheck("Ctrl + W (Ctrl does nothing yet)", new Vector2(0f, 1f), true, player.walkSpeed);
            yield return SpeedCheck("stick tilt 0.30", new Vector2(0f, 0.30f), false, player.walkSpeed * 0.30f / player.walkTilt);
            yield return SpeedCheck("stick tilt 0.50", new Vector2(0f, 0.50f), false, player.walkSpeed);
            yield return SpeedCheck("stick tilt 0.75", new Vector2(0f, 0.75f), false, player.walkSpeed);
            yield return SpeedCheck("Ctrl + stick tilt 0.25", new Vector2(0f, 0.25f), true, player.walkSpeed * 0.25f / player.walkTilt);

            // ---- the walk itself
            Log("--- walk at " + player.walkSpeed.ToString("F2") + " m/s ---");
            var cc = player.GetComponent<CharacterController>();
            cc.enabled = false; root.position = new Vector3(0f, 0.05f, -8f); root.rotation = Quaternion.identity; cc.enabled = true;
            yield return new WaitForSeconds(2.0f);                                   // settle (the spring bones find their rest)
            float floorY = root.position.y;
            float ankleRestL = lf.position.y - floorY, ankleRestR = rf.position.y - floorY;
            Log(string.Format("standing: root y {0:F4}, ankle height L {1:F4} R {2:F4} (Blender ankle rest 0.1146), hips height {3:F4}", floorY, ankleRestL, ankleRestR, hips.position.y - floorY));
            var bust = new Joints(all.Where(x => x.name.StartsWith("J_Sec_L_Bust") || x.name.StartsWith("J_Sec_R_Bust")));
            var ears = new Joints(all.Where(x => x.name.StartsWith("J_Opt_L_CatEar") || x.name.StartsWith("J_Opt_R_CatEar")));
            var hair = new Joints(all.Where(x => x.name.StartsWith("J_Sec_Hair")));
            var hairFirst = new Joints(all.Where(x => x.name.StartsWith("J_Sec_Hair") && x.name.EndsWith("_01")));
            var bustFirst = new Joints(all.Where(x => x.name == "J_Sec_L_Bust1" || x.name == "J_Sec_R_Bust1"));

            input.MoveOverride = new Vector2(0f, 1f);
            yield return new WaitForSeconds(1.5f);                                   // reach speed, the spring bones find their rhythm
            float t0 = Time.time, tEnd = t0 + 10f;
            int n = 0;
            float speedSum = 0f;
            float hipsYmin = 9f, hipsYmax = -9f, hipsXmin = 9f, hipsXmax = -9f, headXmin = 9f, headXmax = -9f, headYmin = 9f, headYmax = -9f;
            float ankleMinL = 9f, ankleMinR = 9f;
            var slide = new List<float>();
            var contactSlide = new List<float>();
            var drift = new List<float>();
            var runFrames = new List<float>();
            var rootSpeed = new List<float>();
            var tailSide = new List<float>();
            var tailHigh = new List<float>();
            var hipsSeries = new List<float>();
            var factorSeries = new List<float>();
            Vector3 prevRoot = root.position;
            // contact points: the vertices of the shoe mesh that are on the floor (the same idea as the planted points in Blender)
            SkinnedMeshRenderer bodySmr = null; int[] shoeVerts = new int[0];
            foreach (var smr in anim.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                if (smr.name == "Body") bodySmr = smr;
            if (bodySmr != null)
            {
                var mats = bodySmr.sharedMaterials;
                for (int m = 0; m < mats.Length; m++)
                    if (mats[m] != null && mats[m].name.Contains("Shoes")) shoeVerts = bodySmr.sharedMesh.GetIndices(m).Distinct().ToArray();
            }
            var baked = new Mesh();
            var bakedVerts = new List<Vector3>();
            var prevShoe = new Vector3[shoeVerts.Length];
            var prevContact = new bool[shoeVerts.Length];
            int contactFrames = 0;
            Vector3 prevL = lf.position, prevR = rf.position;
            bool prevFlatL = false, prevFlatR = false;
            Vector3 runStartL = Vector3.zero, runStartR = Vector3.zero;
            int runLenL = 0, runLenR = 0;
            int stepsL = 0, stepsR = 0;
            Vector3 tailMin = Vector3.one * 9f, tailMax = Vector3.one * -9f, tailRootMin = Vector3.one * 9f, tailRootMax = Vector3.one * -9f;
            float blinkMax = 0f; int blinkStart0 = blink != null ? blink.BlinksStarted : 0;
            float restBlendMax = 0f;
            float[] shotAt = { 2.0f, 2.45f, 2.9f, 3.35f };
            int shot = 0;
            var series = new StringBuilder();
            float nextSeries = 0f;
            while (Time.time < tEnd)
            {
                yield return new WaitForEndOfFrame();
                float dt = Time.deltaTime;
                if (dt <= 0f) continue;
                n++;
                speedSum += player.HorizontalSpeed;
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

                float hL = lf.position.y - floorY, hR = rf.position.y - floorY;
                ankleMinL = Mathf.Min(ankleMinL, hL); ankleMinR = Mathf.Min(ankleMinR, hR);
                bool flatL = hL < ankleRestL + 0.0007f, flatR = hR < ankleRestR + 0.0007f;     // flat = the foot is really on its sole (within 0.7 mm of the standing ankle height)
                Vector3 vL = (lf.position - prevL) / dt, vR = (rf.position - prevR) / dt;
                vL.y = 0f; vR.y = 0f;
                if (flatL && prevFlatL) { slide.Add(vL.magnitude); runLenL++; if (runLenL == 1) runStartL = lf.position; }
                if (flatR && prevFlatR) { slide.Add(vR.magnitude); runLenR++; if (runLenR == 1) runStartR = rf.position; }
                if (flatL && !prevFlatL) stepsL++;
                if (flatR && !prevFlatR) stepsR++;
                if (!flatL && prevFlatL) { if (runLenL >= 10) { runFrames.Add(runLenL); drift.Add(Vector2.Distance(new Vector2(runStartL.x, runStartL.z), new Vector2(prevL.x, prevL.z)) * 1000f); } runLenL = 0; }
                if (!flatR && prevFlatR) { if (runLenR >= 10) { runFrames.Add(runLenR); drift.Add(Vector2.Distance(new Vector2(runStartR.x, runStartR.z), new Vector2(prevR.x, prevR.z)) * 1000f); } runLenR = 0; }
                prevFlatL = flatL; prevFlatR = flatR; prevL = lf.position; prevR = rf.position;
                if (bodySmr != null && shoeVerts.Length > 0)
                {
                    bodySmr.BakeMesh(baked);
                    baked.GetVertices(bakedVerts);
                    bool any = false;
                    for (int k = 0; k < shoeVerts.Length; k++)
                    {
                        Vector3 w = bodySmr.transform.TransformPoint(bakedVerts[shoeVerts[k]]);
                        bool contact = w.y - floorY < 0.0007f;
                        if (contact && prevContact[k])
                        {
                            var dv = w - prevShoe[k]; dv.y = 0f;
                            contactSlide.Add(dv.magnitude / dt);
                            any = true;
                        }
                        prevContact[k] = contact; prevShoe[k] = w;
                    }
                    if (any) contactFrames++;
                }

                if (tailTip != null)
                {
                    // character frame (not turned with the pelvis), relative to the hips: the same numbers as the Blender file
                    var rp = root.InverseTransformPoint(tailTip.position);
                    var tp = rp - root.InverseTransformPoint(hips.position);
                    tailMin = Vector3.Min(tailMin, tp); tailMax = Vector3.Max(tailMax, tp);
                    tailSide.Add(tp.x); tailHigh.Add(tp.y);
                    tailRootMin = Vector3.Min(tailRootMin, rp); tailRootMax = Vector3.Max(tailRootMax, rp);
                }
                bust.Sample(); bustFirst.Sample(); ears.Sample(); hair.Sample(); hairFirst.Sample();
                if (blink != null) blinkMax = Mathf.Max(blinkMax, blink.Lid);
                if (motion != null) restBlendMax = Mathf.Max(restBlendMax, motion.TailRestBlend);

                float tt = Time.time - t0;
                if (tt >= nextSeries && tailTip != null)
                {
                    nextSeries += 0.3f;
                    var th = root.InverseTransformPoint(tailTip.position) - root.InverseTransformPoint(hips.position);
                    series.Append(tt.ToString("F1") + "s:(" + th.x.ToString("F2") + "," + th.y.ToString("F2") + "," + th.z.ToString("F2") + ") ");
                }
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
            input.MoveOverride = Vector2.zero;

            float avgSpeed = speedSum / Mathf.Max(1, n);
            // the ground speed within the steps (actual displacement of the character per frame) against the height of the pelvis
            double mS = rootSpeed.Average(), mH = hipsSeries.Average(), cov = 0, vS = 0, vH = 0;
            for (int i = 0; i < rootSpeed.Count; i++) { double a = rootSpeed[i] - mS, b = hipsSeries[i] - mH; cov += a * b; vS += a * a; vH += b * b; }
            double corr = cov / System.Math.Sqrt(vS * vH + 1e-12);
            float expMin = player.walkSpeed * (1f - player.gaitSpeedVariation), expMax = player.walkSpeed * (1f + player.gaitSpeedVariation);
            Log(string.Format("ground speed of the character per frame: min {0:F3}, max {1:F3}, mean {2:F3} m/s (the model says {3:F3} .. {4:F3}, mean {5:F3}); the wobble is {6:F1} % of the mean; factor {7:F3} .. {8:F3}; correlation with the pelvis height {9:F2} (a faster walker is lower: must be clearly negative)",
                Percentile(rootSpeed, 0.02f), Percentile(rootSpeed, 0.98f), mS, expMin, expMax, player.walkSpeed, 100f * (Percentile(rootSpeed, 0.98f) - Percentile(rootSpeed, 0.02f)) / (2f * (float)mS), factorSeries.Min(), factorSeries.Max(), corr));
            Log("samples " + n + " over " + dur.ToString("F1") + " s (" + (n / dur).ToString("F0") + " fps), average ground speed " + avgSpeed.ToString("F3") + " m/s (Blender walk speed " + bSpeed + ")");
            float stepsPerSecond = (stepsL + stepsR) / dur;
            Log(string.Format("foot touchdowns L {0} R {1} in {2:F1} s = {3:F2} steps/s = {4:F0} steps/min (Blender {6} steps/min at {8} m/s; the count is +-1 of the window), step length {5:F3} m (Blender {7})", stepsL, stepsR, dur, stepsPerSecond, stepsPerSecond * 60f, avgSpeed / Mathf.Max(0.01f, stepsPerSecond), bSteps, bStepLen, bSpeed));
            Log(string.Format("foot slide while flat on the floor (horizontal speed of the ankle within 0.7 mm of its flat height, m/s, {0} frames): median {1:F3}, 90 % of the frames below {2:F3}, 99 % below {3:F3}, largest {4:F3}   (planted = near 0)",
                slide.Count, Percentile(slide, 0.5f), Percentile(slide, 0.9f), Percentile(slide, 0.99f), slide.Count > 0 ? slide.Max() : 0f));
            Log(string.Format("foot slide of the shoe SOLE (every shoe vertex within 0.7 mm of the floor, horizontal speed in m/s, {0} samples in {1} frames): median {2:F3}, 90 % below {3:F3}, 99 % below {4:F3}, largest {5:F3}   (Blender planted points: heel 0.4 .. 0.7 mm, ball 2.2 mm)",
                contactSlide.Count, contactFrames, Percentile(contactSlide, 0.5f), Percentile(contactSlide, 0.9f), Percentile(contactSlide, 0.99f), contactSlide.Count > 0 ? contactSlide.Max() : 0f));
            Log(string.Format("drift of a planted foot (ankle) over one whole flat phase (mm, {0} phases of about {1:F0} ms): median {2:F1}, largest {3:F1}   (Blender: the foot is flat from phase 0.08 to 0.30 = 190 ms)", drift.Count, Percentile(runFrames, 0.5f) / (n / dur) * 1000f, Percentile(drift, 0.5f), drift.Count > 0 ? drift.Max() : 0f));
            Log(string.Format("lowest ankle height above the floor: left {0:F4} right {1:F4} (flat foot {2:F4} / {3:F4}; below = sunk in, far above = floating)", ankleMinL, ankleMinR, ankleRestL, ankleRestR));
            Log(string.Format("pelvis height range {0:F4} .. {1:F4} m = {2:F1} mm (Blender {3})", hipsYmin, hipsYmax, (hipsYmax - hipsYmin) * 1000f, bPelvis));
            Log(string.Format("pelvis side shift {0:F1} .. {1:F1} mm = +-{2:F1} mm (Blender +-{3} mm)", hipsXmin * 1000f, hipsXmax * 1000f, (hipsXmax - hipsXmin) * 500f, bSway));
            Log(string.Format("head side position {0:F1} .. {1:F1} mm (spec: within +-5 mm of the centre line), head height range {2:F1} mm", headXmin * 1000f, headXmax * 1000f, (headYmax - headYmin) * 1000f));
            Log(string.Format("tail tip relative to the hips (character frame): side x {0:F3} .. {1:F3} = {2:F0} mm, height y {3:F3} .. {4:F3} = {5:F0} mm, reach z {6:F3} .. {7:F3}; behind the root: z {8:F2} .. {9:F2}, height above the floor {10:F2} .. {11:F2}; Blender: {12}",
                tailMin.x, tailMax.x, (tailMax.x - tailMin.x) * 1000f, tailMin.y, tailMax.y, (tailMax.y - tailMin.y) * 1000f, tailMin.z, tailMax.z, tailRootMin.z, tailRootMax.z, tailRootMin.y, tailRootMax.y, bTail));
            Log(string.Format("tail tip, the usual swing (2 % .. 98 % of the 10 s, without the rare big excursions): side {0:F0} mm, height {1:F0} mm", (Percentile(tailSide, 0.98f) - Percentile(tailSide, 0.02f)) * 1000f, (Percentile(tailHigh, 0.98f) - Percentile(tailHigh, 0.02f)) * 1000f));
            Log("tail rest curve blend reached " + restBlendMax.ToString("F2") + " (1 = walking J), tail root scale " + (tailRoot != null ? tailRoot.localScale.x.ToString("F2") : "?"));
            Log("spring bones, swing away from the rest direction (deg), Blender simulation in brackets:");
            Log("   bust, first joints  " + bustFirst.Text + "   (Blender: " + bBust + ")");
            Log("   bust, all joints    " + bust.Text);
            Log("   ear joints          " + ears.Text + "   (Blender tip: " + bEar + ")");
            Log("   hair, first joints  " + hairFirst.Text + "   (Blender: " + bHair + ")");
            Log("   hair, all joints    " + hair.Text);
            Log("blink while walking: max lid " + blinkMax.ToString("F2") + ", blinks started in the run " + (blink != null ? (blink.BlinksStarted - blinkStart0).ToString() : "?"));
            Log("tail tip in hips space every 0.3 s: " + series);

            // stop and look at the idle again
            yield return new WaitForSeconds(1.2f);
            Log("after stop: ground speed " + player.HorizontalSpeed.ToString("F2") + ", animator Speed " + anim.GetFloat("Speed").ToString("F2") + ", tail rest blend " + (motion != null ? motion.TailRestBlend.ToString("F2") : "?"));
            yield return new WaitForEndOfFrame();
            Shot("idle_after", new Vector3(3.2f, 0.95f, 0f), 0.8f, 0.95f);

            File.WriteAllText(Path.Combine(outputDir, "walk_verify.txt"), log.ToString());
            Destroy(camGo);
            finished = true;
        }
    }
}
