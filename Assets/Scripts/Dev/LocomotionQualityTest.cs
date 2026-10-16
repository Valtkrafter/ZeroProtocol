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
    /// How good does the movement look at every speed and at every change of speed?
    ///  A  speed sweep: steady ground speeds from the walk to the sprint (the blend tree mixes the walk and the run clip in between):
    ///     cadence, step length, drift of the planted toe joint (sliding), flight share
    ///  B  transitions (idle -> walk -> sprint -> walk -> stop, sprint -> stop, jump out of the sprint, dodge into the sprint): the largest
    ///     world rotation of any humanoid bone from one frame to the next (normalised to degrees per 1/60 s) and the largest change of the ground speed,
    ///     next to the steady walk and sprint.
    /// Written to outputDir/locomotion_quality.txt.
    /// </summary>
    public class LocomotionQualityTest : MonoBehaviour
    {
        public string outputDir = "";
        public bool finished;
        readonly StringBuilder log = new StringBuilder();
        YoruController player;
        GameInput input;
        Animator anim;
        Transform[] toes;
        Transform[] bones;
        string[] boneNames;
        Quaternion[] prevRot;

        void Log(string s) { log.AppendLine(s); }

        static float Percentile(List<float> v, float p)
        {
            if (v.Count == 0) return 0f;
            var s = v.OrderBy(x => x).ToList();
            return s[Mathf.Clamp(Mathf.RoundToInt(p * (s.Count - 1)), 0, s.Count - 1)];
        }

        /// <summary>Per-frame rotation step of every humanoid bone, normalised to 1/60 s: the largest and its bone. Call at the end of every frame.</summary>
        void SampleBones(float dt, ref float worst, ref string worstBone, List<float> frameMax)
        {
            float k = (1f / 60f) / dt;
            float fm = 0f;
            for (int i = 0; i < bones.Length; i++)
            {
                var r = bones[i].rotation;
                float a = Quaternion.Angle(prevRot[i], r) * k;
                prevRot[i] = r;
                if (a > fm) fm = a;
                if (a > worst) { worst = a; worstBone = boneNames[i]; }
            }
            if (frameMax != null) frameMax.Add(fm);
        }

        void ResetBones() { for (int i = 0; i < bones.Length; i++) prevRot[i] = bones[i].rotation; }

        void Place(Vector3 p)
        {
            var cc = player.GetComponent<CharacterController>();
            cc.enabled = false; player.transform.position = p; player.transform.rotation = Quaternion.identity; cc.enabled = true;
        }

        IEnumerator Steady(string label, Vector2 stick, bool sprint)
        {
            Place(new Vector3(2f, 0.05f, -36f));
            input.MoveOverride = stick; input.SprintOverride = sprint;
            yield return new WaitForSeconds(2.4f);
            float floorY = player.transform.position.y;
            var td = new[] { 0, 0 }; var planted = new[] { false, false };
            var start = new Vector3[2]; var prev = new Vector3[2]; var frames = new[] { 0, 0 };
            var drift = new List<float>(); var slide = new List<float>();
            float t0 = Time.time; int n = 0, off = 0; float spSum = 0f;
            float worst = 0f; string wb = ""; var fm = new List<float>();
            ResetBones();
            var rootPrev = player.transform.position;
            var sp = new List<float>();
            while (Time.time - t0 < 3.0f)
            {
                yield return new WaitForEndOfFrame();
                float dt = Time.deltaTime; if (dt <= 0f) continue;
                n++;
                var d = player.transform.position - rootPrev; d.y = 0f; rootPrev = player.transform.position;
                sp.Add(d.magnitude / dt); spSum += d.magnitude / dt;
                SampleBones(dt, ref worst, ref wb, fm);
                for (int f = 0; f < 2; f++)
                {
                    bool was = planted[f];
                    planted[f] = toes[f].position.y - floorY < 0.0544f + 0.003f;
                    var p = toes[f].position;
                    if (planted[f] && was) { var v = (p - prev[f]) / dt; v.y = 0f; slide.Add(v.magnitude); frames[f]++; }
                    if (planted[f] && !was) { td[f]++; start[f] = p; frames[f] = 0; }
                    if (!planted[f] && was && frames[f] >= 3) drift.Add(Vector2.Distance(new Vector2(start[f].x, start[f].z), new Vector2(prev[f].x, prev[f].z)) * 1000f);
                    prev[f] = p;
                }
                if (!planted[0] && !planted[1]) off++;
            }
            float dur = Time.time - t0;
            float mean = spSum / Mathf.Max(1, n);
            float steps = (td[0] + td[1]) / dur;
            Log(string.Format("{0,-26} speed {1,5:F2} m/s | cadence {2,4:F0} steps/min step {3,4:F2} m | planted toe: drift {4,5:F1} mm median ({5,2} stances), slide median {6:F3} m/s | both off the floor {7,3:F0} % | largest bone step {8,5:F1} deg/60th ({9})",
                label, mean, steps * 60f, mean / Mathf.Max(0.01f, steps), Percentile(drift, 0.5f), drift.Count, Percentile(slide, 0.5f), 100f * off / Mathf.Max(1, n), worst, wb));
            input.MoveOverride = Vector2.zero; input.SprintOverride = false;
            yield return new WaitForSeconds(1.2f);
        }

        /// <summary>Runs `action` (a coroutine that sets inputs over time) and measures the bone steps and ground speed changes during `seconds`.</summary>
        IEnumerator Phase(string label, float seconds)
        {
            float t0 = Time.time; float worst = 0f; string wb = ""; var fm = new List<float>();
            var accel = new List<float>(); float prevSp = player.HorizontalSpeed;
            ResetBones();
            while (Time.time - t0 < seconds)
            {
                yield return new WaitForEndOfFrame();
                float dt = Time.deltaTime; if (dt <= 0f) continue;
                SampleBones(dt, ref worst, ref wb, fm);
                accel.Add(Mathf.Abs(player.HorizontalSpeed - prevSp) / dt); prevSp = player.HorizontalSpeed;
            }
            Log(string.Format("{0,-44} largest bone step {1,5:F1} deg per 1/60 s ({2}), 99 % of the frames below {3,5:F1}; largest ground acceleration {4,5:F1} m/s2 (control setting {5:F0}); animator Speed {6:F2}",
                label, worst, wb, Percentile(fm, 0.99f), accel.Count > 0 ? accel.Max() : 0f, player.acceleration, anim.GetFloat("Speed")));
        }

        IEnumerator Start()
        {
            player = FindFirstObjectByType<YoruController>();
            input = player.GetComponent<GameInput>();
            anim = player.animator;
            Directory.CreateDirectory(outputDir);
            var list = new List<Transform>(); var names = new List<string>();
            for (int i = 0; i < (int)HumanBodyBones.LastBone; i++)
            {
                var hb = (HumanBodyBones)i;
                if (hb >= HumanBodyBones.LeftThumbProximal && hb <= HumanBodyBones.RightLittleDistal) continue;     // fingers: not part of this check
                var t = anim.GetBoneTransform(hb);
                if (t != null) { list.Add(t); names.Add(hb.ToString()); }
            }
            bones = list.ToArray(); boneNames = names.ToArray(); prevRot = new Quaternion[bones.Length];
            toes = new[] { anim.GetBoneTransform(HumanBodyBones.LeftToes), anim.GetBoneTransform(HumanBodyBones.RightToes) };
            Log("frame rate of this run " + (1f / Mathf.Max(0.0001f, Time.smoothDeltaTime)).ToString("F0") + " fps; walkSpeed " + player.walkSpeed + ", runSpeed " + player.runSpeed + ", clipRunSpeed " + player.clipRunSpeed + ", acceleration " + player.acceleration);
            yield return new WaitForSeconds(1.0f);

            Log("--- A: steady ground speeds (walk clip 1.5 m/s .. run clip 5.0 m/s, the blend tree mixes both in between) ---");
            yield return Steady("walk (W)", new Vector2(0f, 1f), false);
            foreach (float v in new[] { 2.0f, 2.5f, 3.0f, 3.5f, 4.0f, 4.5f })
                yield return Steady("sprint tilt -> " + v.ToString("F1") + " m/s", new Vector2(0f, player.walkTilt * v / player.runSpeed), true);
            yield return Steady("sprint (Shift + W)", new Vector2(0f, 1f), true);

            Log("--- B: changes of speed ---");
            Place(new Vector3(2f, 0.05f, -38f));
            yield return new WaitForSeconds(1.0f);
            yield return Phase("standing still", 1.0f);
            input.MoveOverride = new Vector2(0f, 1f);
            yield return Phase("start of the walk (idle -> walk)", 0.9f);
            yield return Phase("steady walk", 1.2f);
            input.SprintOverride = true;
            yield return Phase("walk -> sprint (Shift held, with the dodge)", 1.6f);
            yield return Phase("steady sprint", 1.5f);
            input.SprintOverride = false;
            yield return Phase("sprint -> walk (Shift released)", 1.2f);
            input.SprintOverride = true;
            yield return Phase("walk -> sprint again", 1.4f);
            input.MoveOverride = Vector2.zero; input.SprintOverride = false;
            yield return Phase("sprint -> stop (everything released)", 1.2f);
            input.MoveOverride = new Vector2(0f, 1f);
            yield return Phase("walk start, 2nd time", 0.8f);
            input.MoveOverride = Vector2.zero;
            yield return Phase("walk -> stop", 1.0f);
            Place(new Vector3(2f, 0.05f, -38f));
            input.MoveOverride = new Vector2(0f, 1f); input.SprintOverride = true;
            yield return new WaitForSeconds(2.6f);
            input.JumpOverride = true;
            yield return Phase("jump out of the sprint (the air clip is not made yet)", 1.4f);
            input.MoveOverride = Vector2.zero; input.SprintOverride = false;
            yield return new WaitForSeconds(1.0f);

            File.WriteAllText(Path.Combine(outputDir, "locomotion_quality.txt"), log.ToString());
            finished = true;
        }
    }
}
