using System;
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
    /// Play Mode check of the Shift controls: a press is the DODGE (the dash starts at once), holding Shift goes into the SPRINT when the dodge is over,
    /// letting go ends it. Every case drives the input like a player would (move stick, a one-frame press, a held Shift) and writes the times and speeds
    /// it measured (position difference per frame, sampled at the end of the frame) into outputDir/sprint_input.txt.
    /// </summary>
    public class SprintInputTest : MonoBehaviour
    {
        public string outputDir = "";
        public bool finished;
        readonly StringBuilder log = new StringBuilder();
        YoruController player;
        GameInput input;

        struct Sample { public float t, speed, real; public bool dash, sprint; }
        readonly List<Sample> samples = new List<Sample>();

        Vector3 startPos;
        Quaternion startRot;

        void Log(string s) { log.AppendLine(s); }

        void Start() { StartCoroutine(Main()); }

        /// <summary>back to the starting point (a case must not end against the wall of the arena)</summary>
        IEnumerator Teleport()
        {
            var cc = player.GetComponent<CharacterController>();
            input.MoveOverride = Vector2.zero;
            input.SprintOverride = false;
            cc.enabled = false;
            player.transform.SetPositionAndRotation(startPos, startRot);
            cc.enabled = true;
            yield return new WaitForSeconds(0.7f);
        }

        /// <summary>drives the input with driver(t) before every frame and samples the character at the end of the frame</summary>
        IEnumerator Case(float seconds, Action<float> driver)
        {
            samples.Clear();
            float t0 = Time.time;
            Vector3 last = player.transform.position;
            float lastT = t0;
            while (Time.time - t0 < seconds)
            {
                driver(Time.time - t0);
                yield return new WaitForEndOfFrame();
                float dt = Time.time - lastT;
                Vector3 p = player.transform.position;
                float real = dt > 1e-4f ? new Vector2(p.x - last.x, p.z - last.z).magnitude / dt : 0f;
                last = p;
                lastT = Time.time;
                samples.Add(new Sample { t = Time.time - t0, speed = player.HorizontalSpeed, real = real, dash = player.IsDashing, sprint = player.IsSprinting });
            }
        }

        float FirstTime(Func<Sample, bool> pred) { foreach (var s in samples) if (pred(s)) return s.t; return -1f; }
        float LastTime(Func<Sample, bool> pred) { for (int i = samples.Count - 1; i >= 0; i--) if (pred(samples[i])) return samples[i].t; return -1f; }
        float MeanReal(float from, float to) { var v = samples.Where(s => s.t >= from && s.t <= to).Select(s => s.real).ToList(); return v.Count == 0 ? 0f : v.Average(); }
        float MaxReal() { return samples.Count == 0 ? 0f : samples.Max(s => s.real); }

        string Summary(string label, float releaseAt)
        {
            float fd = FirstTime(s => s.dash), ld = LastTime(s => s.dash);
            float fs = FirstTime(s => s.sprint), ls = LastTime(s => s.sprint);
            float end = samples.Count > 0 ? samples[samples.Count - 1].t : 0f;
            return string.Format("{0}: dodge {1} | sprint {2} | fastest {3:F1} m/s | speed over the last 0.4 s {4:F2} m/s | frames {5}",
                label,
                fd < 0f ? "never" : string.Format("{0:F2} s .. {1:F2} s", fd, ld),
                fs < 0f ? "never" : string.Format("from {0:F2} s to {1:F2} s", fs, ls),
                MaxReal(), MeanReal(end - 0.4f, end), samples.Count);
        }

        IEnumerator Main()
        {
            player = FindFirstObjectByType<YoruController>();
            input = player.GetComponent<GameInput>();
            Directory.CreateDirectory(outputDir);
            input.MoveOverride = Vector2.zero;
            input.SprintOverride = false;
            yield return new WaitForSeconds(0.8f);
            startPos = player.transform.position;
            startRot = player.transform.rotation;
            Log(string.Format("walkSpeed {0}, runSpeed {1}, sprintHoldDelay {2} s, dashDuration {3} s, dashCooldown {4} s, dashSpeed {5} m/s, walkTilt {6}",
                player.walkSpeed, player.runSpeed, player.sprintHoldDelay, player.dashDuration, player.dashCooldown, player.dashSpeed, player.walkTilt));

            yield return Teleport();
            // A: W only = the walk, never a sprint
            yield return Case(1.6f, t => input.MoveOverride = new Vector2(0f, 1f));
            Log(Summary("A  W only", 0f) + "   (expect: no dodge, no sprint, 1.50 m/s)");

            yield return Teleport();
            // B: walking with W, Shift pressed and HELD for 1.6 s, then let go
            yield return Case(3.2f, t =>
            {
                input.MoveOverride = new Vector2(0f, 1f);
                if (t < 0.5f) return;                                              // 0.5 s of walking first
                if (t < 0.5f + 0.06f) { input.DashOverride = true; input.SprintOverride = true; }
                else if (t < 2.2f) input.SprintOverride = true;
                else input.SprintOverride = false;
            });
            var sB = samples.ToList();
            float tPress = 0.5f;
            Log(Summary("B  W + Shift held from 0.50 s to 2.20 s", 2.2f) + string.Format("   (expect: dodge right after 0.50 s, sprint from about {0:F2} s to 2.20 s, 5.00 m/s, then back to 1.50)", tPress + player.sprintHoldDelay));
            Log(string.Format("   speed of the sprint between 1.2 s and 2.1 s: {0:F2} m/s; speed after letting go (2.7 s .. 3.2 s): {1:F2} m/s",
                MeanReal(1.2f, 2.1f), MeanReal(2.7f, 3.2f)));
            input.SprintOverride = false;
            yield return Case(1.0f, t => input.MoveOverride = new Vector2(0f, 1f));

            yield return Teleport();
            // C: walking with W, Shift only TAPPED (down for 0.10 s)
            yield return Case(3.0f, t =>
            {
                input.MoveOverride = new Vector2(0f, 1f);
                if (t < 0.5f) return;
                if (t < 0.56f) { input.DashOverride = true; input.SprintOverride = true; }
                else if (t < 0.60f) input.SprintOverride = true;
                else input.SprintOverride = false;
            });
            Log(Summary("C  W + Shift tapped (0.10 s)", 0.6f) + "   (expect: dodge, NO sprint, back to 1.50 m/s)");
            yield return Case(1.0f, t => input.MoveOverride = new Vector2(0f, 1f));

            yield return Teleport();
            // D: Shift held without a move input = the dodge in place, no sprint
            input.MoveOverride = Vector2.zero;
            yield return Case(0.8f, t => input.MoveOverride = Vector2.zero);
            yield return Case(2.0f, t =>
            {
                input.MoveOverride = Vector2.zero;
                if (t < 0.06f) { input.DashOverride = true; input.SprintOverride = true; }
                else if (t < 1.5f) input.SprintOverride = true;
                else input.SprintOverride = false;
            });
            Log(Summary("D  Shift held, no move input", 1.5f) + "   (expect: a dodge, no sprint, standing at the end)");
            yield return Case(0.8f, t => { input.MoveOverride = Vector2.zero; input.SprintOverride = false; });

            yield return Teleport();
            // E: the dodge is on cooldown when Shift is pressed again: holding still goes into the sprint after sprintHoldDelay
            yield return Case(2.4f, t =>
            {
                input.MoveOverride = new Vector2(0f, 1f);
                if (t < 0.5f) return;
                if (t < 0.56f) input.DashOverride = true;                           // a dodge (no holding)
                else if (t >= 0.80f && t < 0.86f) { input.DashOverride = true; input.SprintOverride = true; }   // pressed again while the cooldown runs: no dodge
                else if (t >= 0.86f && t < 2.0f) input.SprintOverride = true;
                else input.SprintOverride = false;
            });
            Log(Summary("E  dodge, then Shift pressed and held again 0.30 s later (cooldown 0.60 s)", 2.0f) + "   (expect: one dodge at 0.50 s, the sprint from about 1.04 s)");
            input.SprintOverride = false;
            yield return Case(1.0f, t => input.MoveOverride = new Vector2(0f, 1f));

            yield return Teleport();
            // F: a light stick tilt (0.30) with Shift held: the sprint is one speed (between the walk and the run clip the feet slide), the tilt does not slow it
            yield return Case(2.4f, t =>
            {
                input.MoveOverride = new Vector2(0f, 0.3f);
                if (t < 0.5f) return;
                input.SprintOverride = t < 2.2f;
            });
            Log(Summary("F  stick tilt 0.30 + Shift held", 2.2f) + string.Format("   (expect: the sprint speed {0} m/s whatever the tilt)", player.runSpeed));
            input.SprintOverride = false;
            input.MoveOverride = Vector2.zero;
            yield return new WaitForSeconds(0.5f);

            File.WriteAllText(Path.Combine(outputDir, "sprint_input.txt"), log.ToString());
            finished = true;
        }
    }
}
