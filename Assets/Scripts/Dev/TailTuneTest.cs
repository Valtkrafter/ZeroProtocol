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
    /// Walks at walking speed and measures how far the tip of the tail swings (sideways, up and down, reach) for a list of settings of the
    /// tail physics and of the swing of the tail base, so the numbers can be matched to the Blender walk (side 146 mm, height 116 mm).
    /// Settings: walkYaw, walkPitch, stiffness, drag, gravity (the tail spring bone is changed while the game runs).
    /// </summary>
    public class TailTuneTest : MonoBehaviour
    {
        public string outputDir = "";
        public List<Vector4> settings = new List<Vector4>();          // x walkYaw, y stiffness, z drag, w walkPitch
        public float gravityOverride = -1f;
        [Tooltip("Tune the sprint (Shift held): x sprintYaw, y sprintStiffness, z sprintDrag, w sprintPitch")]
        public bool sprint;
        public string blenderSide = "?", blenderHeight = "?";
        public bool finished;

        IEnumerator Start()
        {
            Directory.CreateDirectory(outputDir);
            var player = FindFirstObjectByType<YoruController>();
            var input = player.GetComponent<GameInput>();
            var anim = player.animator;
            var motion = anim.GetComponent<YoruSecondaryMotion>();
            VRMSpringBone tail = null;
            foreach (var sb in anim.GetComponentsInChildren<VRMSpringBone>(true)) if (sb.m_comment == "CatTail") tail = sb;
            Transform tip = null, hips = anim.GetBoneTransform(HumanBodyBones.Hips);
            foreach (var t in anim.GetComponentsInChildren<Transform>(true)) if (t.name == "J_Opt_C_CatTail8_01") tip = t;
            var root = player.transform;
            var cc = player.GetComponent<CharacterController>();
            var log = new StringBuilder();
            log.AppendLine("Blender walk (Blender/Yoru_Walk_reference.json): tail tip side " + blenderSide + " mm, height " + blenderHeight + " mm, reach -0.430 .. -0.425");
            log.AppendLine("walkYaw stiff  drag  walkPitch | side mm (x range)         | height mm (y range)     | reach (z range)");
            foreach (var st in settings)
            {
                if (sprint) { motion.sprintYaw = st.x; motion.sprintStiffness = st.y; motion.sprintDrag = st.z; motion.sprintPitch = st.w; }
                else { motion.walkYaw = st.x; motion.walkStiffness = st.y; tail.m_dragForce = st.z; motion.walkPitch = st.w; }
                if (gravityOverride >= 0f) tail.m_gravityPower = gravityOverride;
                cc.enabled = false; root.position = new Vector3(2f, 0.05f, sprint ? -37f : -8f); root.rotation = Quaternion.identity; cc.enabled = true;
                input.MoveOverride = new Vector2(0f, 1f);
                input.SprintOverride = sprint;
                yield return new WaitForSeconds(sprint ? 2.2f : 2.5f);
                Vector3 mn = Vector3.one * 9f, mx = Vector3.one * -9f;
                float t0 = Time.time;
                while (Time.time - t0 < (sprint ? 4.0f : 8.0f))
                {
                    yield return new WaitForEndOfFrame();
                    var p = root.InverseTransformPoint(tip.position) - root.InverseTransformPoint(hips.position);
                    mn = Vector3.Min(mn, p); mx = Vector3.Max(mx, p);
                }
                input.MoveOverride = Vector2.zero; input.SprintOverride = false;
                log.AppendLine(string.Format("{0,6:F1} {1,6:F2} {2,6:F2} {3,7:F1}   | {4,4:F0} ({5,6:F3} .. {6,6:F3})   | {7,4:F0} ({8,6:F3} .. {9,6:F3}) | ({10,6:F3} .. {11,6:F3})",
                    st.x, st.y, st.z, st.w, (mx.x - mn.x) * 1000f, mn.x, mx.x, (mx.y - mn.y) * 1000f, mn.y, mx.y, mn.z, mx.z));
                yield return new WaitForSeconds(sprint ? 1.2f : 0.8f);
            }
            File.WriteAllText(Path.Combine(outputDir, "tail_tune.txt"), log.ToString());
            finished = true;
        }
    }
}
