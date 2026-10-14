using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEngine;
using ZeroProtocol.Player;

namespace ZeroProtocol.Dev
{
    /// <summary>
    /// Scripted Play Mode check of the animation state machine. Drives the player through idle, run, standing jump,
    /// running jump, dash and a staircase descent, logs the Animator state every few frames and saves side-view pictures.
    /// </summary>
    public class AnimationSmokeTest : MonoBehaviour
    {
        public string outputDir = "";
        public bool finished;
        readonly StringBuilder log = new StringBuilder();
        YoruController player;
        GameInput input;
        Animator anim;
        Camera shotCam;
        static readonly string[] StateNames = { "Locomotion", "JumpAir", "JumpRunAir", "Land", "LandRun", "Dash" };

        void Start() { StartCoroutine(Run()); }

        string State()
        {
            var info = anim.GetCurrentAnimatorStateInfo(0);
            string s = "?";
            foreach (var n in StateNames) if (info.IsName(n)) { s = n; break; }
            if (anim.IsInTransition(0))
            {
                var next = anim.GetNextAnimatorStateInfo(0);
                string t = "?";
                foreach (var n in StateNames) if (next.IsName(n)) { t = n; break; }
                s += ">" + t;
            }
            return s;
        }

        IEnumerator Run()
        {
            player = FindFirstObjectByType<YoruController>();
            input = player.GetComponent<GameInput>();
            anim = player.animator;
            Directory.CreateDirectory(outputDir);
            var camGo = new GameObject("PoseShotCam");
            shotCam = camGo.AddComponent<Camera>();
            shotCam.enabled = false;
            shotCam.clearFlags = CameraClearFlags.SolidColor;
            shotCam.backgroundColor = new Color(0.78f, 0.82f, 0.88f);
            shotCam.fieldOfView = 28f;
            Log("controller " + (anim.runtimeAnimatorController == null ? "NONE" : anim.runtimeAnimatorController.name) + ", params " + anim.parameterCount);

            yield return new WaitForSeconds(1.0f);
            Log("idle: state " + State() + " speed param " + anim.GetFloat("Speed").ToString("F2"));
            Pose("idle_a"); yield return new WaitForSeconds(0.95f); Pose("idle_b");
            for (int i = 0; i < 6; i++) { PoseBack("tail_idle_" + i); yield return new WaitForSeconds(0.55f); }
            var motion = player.GetComponentInChildren<YoruSecondaryMotion>();
            if (motion != null) { motion.TriggerFlick(); }
            for (int i = 0; i < 4; i++) { PoseBack("tail_flick_" + i); yield return new WaitForSeconds(0.12f); }
            yield return new WaitForSeconds(0.6f);

            // run
            input.MoveOverride = new Vector2(0f, 1f);
            yield return new WaitForSeconds(0.6f);
            for (int i = 0; i < 4; i++) { Pose("run_" + i); yield return new WaitForSeconds(0.1f); }
            Log("run: state " + State() + ", Speed " + anim.GetFloat("Speed").ToString("F2") + " m/s, LocoMult " + anim.GetFloat("LocoMult").ToString("F2"));
            input.MoveOverride = Vector2.zero;
            yield return new WaitForSeconds(0.8f);
            Log("after stop: state " + State() + " speed " + anim.GetFloat("Speed").ToString("F2"));

            // standing jump
            yield return Jump("jump", false);
            yield return new WaitForSeconds(0.8f);

            // running jump
            input.MoveOverride = new Vector2(0f, 1f);
            yield return new WaitForSeconds(0.5f);
            yield return Jump("rjump", true);
            input.MoveOverride = Vector2.zero;
            yield return new WaitForSeconds(0.8f);

            // dash
            input.MoveOverride = new Vector2(0f, 0f);
            input.DashOverride = true;
            var seen = new List<string>();
            for (int i = 0; i < 8; i++)
            {
                yield return new WaitForSeconds(0.05f);
                string s = State(); if (seen.Count == 0 || seen[seen.Count - 1] != s) seen.Add(s);
                if (i == 1 || i == 3) Pose("dash_" + i);
            }
            Log("dash: states " + string.Join(" , ", seen.ToArray()));
            yield return new WaitForSeconds(0.8f);

            // staircase descent: the top of the stairs is at the end of the stairs (z about 11, y 1.2)
            yield return Stairs();

            File.WriteAllText(Path.Combine(outputDir, "anim_log.txt"), log.ToString());
            finished = true;
        }

        IEnumerator Jump(string tag, bool running)
        {
            var seen = new List<string>();
            string lastState = "";
            float yStart = player.transform.position.y, yMax = yStart;
            input.JumpOverride = true;
            int shot = 0;
            float t = 0f, nextShot = 0f;
            while (t < 1.6f)
            {
                yield return null;
                t += Time.deltaTime;
                yMax = Mathf.Max(yMax, player.transform.position.y);
                string s = State(); if (s != lastState) { seen.Add(s + "@" + t.ToString("F2")); lastState = s; }
                if (t >= nextShot && shot < 14)
                {
                    Pose(tag + "_" + shot.ToString("D2") + "_" + s.Replace(">", "-to-"));
                    shot++; nextShot += 0.1f;
                }
            }
            Log(tag + ": rose " + (yMax - yStart).ToString("F2") + " m; states " + string.Join(" , ", seen.ToArray()) + "; AirPhase end " + anim.GetFloat("AirPhase").ToString("F2"));
        }

        IEnumerator Stairs()
        {
            // put the player on the top step (stairs are at x -14, z 8 .. 11.2) and walk down (-z) with a fixed camera direction
            var cc = player.GetComponent<CharacterController>();
            cc.enabled = false; player.transform.position = new Vector3(-14f, 1.3f, 10.5f); cc.enabled = true;
            player.transform.rotation = Quaternion.LookRotation(Vector3.back);
            var dummy = new GameObject("StairCam").transform;
            dummy.rotation = Quaternion.LookRotation(Vector3.back);
            var oldCam = player.cameraTransform;
            player.cameraTransform = dummy;
            yield return new WaitForSeconds(0.3f);
            var seen = new List<string>();
            string lastState = "";
            int airFrames = 0, frames = 0;
            input.MoveOverride = new Vector2(0f, 1f);
            float t = 0f;
            float yTop = player.transform.position.y;
            while (t < 1.4f)
            {
                yield return null; t += Time.deltaTime; frames++;
                string s = State();
                if (s.StartsWith("JumpAir") || s.StartsWith("JumpRunAir")) airFrames++;
                if (s != lastState) { seen.Add(s + "@" + t.ToString("F2")); lastState = s; }
                if (frames == 20) Pose("stairs_down");
            }
            input.MoveOverride = Vector2.zero;
            Log("stairs down: from y " + yTop.ToString("F2") + " to " + player.transform.position.y.ToString("F2") + ", frames in air-state " + airFrames + "/" + frames + ", states " + string.Join(" , ", seen.ToArray()));
            player.cameraTransform = oldCam;
        }

        void PoseBack(string name) { Shot(name, -player.transform.forward * 2.6f + Vector3.up * 1.15f, 0.85f); }
        void Pose(string name) { Shot(name, player.transform.right * 3.4f + Vector3.up * 0.95f, 0.8f); }

        void Shot(string name, Vector3 offset, float lookHeight)
        {
            var p = player.transform;
            shotCam.transform.position = p.position + offset;
            shotCam.transform.LookAt(p.position + Vector3.up * lookHeight);
            var rt = new RenderTexture(420, 520, 24, RenderTextureFormat.ARGB32);
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

        void Log(string s) { log.AppendLine(s); Debug.Log("[AnimTest] " + s); }
    }
}
