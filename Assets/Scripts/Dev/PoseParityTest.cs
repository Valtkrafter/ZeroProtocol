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
    /// Does the clip in the game put every bone where Blender put it? The Animator is frozen at the 26 frames of the walk cycle
    /// (Locomotion state, Speed = walk speed) and the position of every humanoid bone is compared with the position the Blender walk has
    /// at that frame (Blender/Yoru_Walk_bonepos.json, made from the .blend). The differences come from the humanoid muscle limits of the avatar
    /// and from the keyframe reduction of the baker.
    /// </summary>
    public class PoseParityTest : MonoBehaviour
    {
        public string outputDir = "";
        public string bonePosJson = "";
        public string stateName = "Locomotion";
        public float speedParam = 0f;                              // 0 = the walk speed of the controller
        public bool finished;

        [System.Serializable]
        class Dump { public int frames; public string[] bones; public float[][][] pos; }

        IEnumerator Start()
        {
            Directory.CreateDirectory(outputDir);
            var log = new StringBuilder();
            var player = FindFirstObjectByType<YoruController>();
            var anim = player.animator;
            player.enabled = false;                                   // the controller must not feed the animator parameters
            var d = Newtonsoft.Json.JsonConvert.DeserializeObject<Dump>(File.ReadAllText(bonePosJson));
            var model = anim.transform;
            var bones = new List<(string name, Transform t)>();
            foreach (var n in d.bones)
            {
                if (System.Enum.TryParse(n, out HumanBodyBones hb))
                {
                    var t = anim.GetBoneTransform(hb);
                    if (t != null) bones.Add((n, t)); else bones.Add((n, null));
                }
            }
            anim.speed = 0f;
            anim.SetFloat("Speed", speedParam > 0f ? speedParam : player.walkSpeed);   // exactly the walk clip (the blend tree has idle at 0 and the walk at walkSpeed)
            anim.SetFloat("LocoMult", 1f);
            yield return null;
            int nb = d.bones.Length;
            var maxErr = new float[nb]; var sumErr = new float[nb];
            var frameMax = new float[d.frames];
            var worstFrame = new int[nb];
            for (int f = 0; f < d.frames; f++)
            {
                anim.Play(stateName, 0, f / (float)d.frames);
                anim.Update(0f);
                anim.Update(0f);
                yield return new WaitForEndOfFrame();
                anim.Update(0f);
                for (int b = 0; b < nb; b++)
                {
                    var t = bones[b].t;
                    if (t == null) continue;
                    var e = new Vector3(d.pos[f][b][0], d.pos[f][b][1], d.pos[f][b][2]);
                    float err = (model.InverseTransformPoint(t.position) - e).magnitude;
                    sumErr[b] += err;
                    if (err > maxErr[b]) { maxErr[b] = err; worstFrame[b] = f; }
                    frameMax[f] = Mathf.Max(frameMax[f], err);
                }
            }
            float all = maxErr.Max();
            log.AppendLine("pose parity of the walk clip in the game against Blender (Yoru_Walk_bonepos.json), " + d.frames + " frames x " + nb + " humanoid bones");
            log.AppendLine(string.Format("largest difference of any bone at any frame: {0:F2} mm; mean over all bones and frames {1:F2} mm", all * 1000f, sumErr.Sum() / (nb * d.frames) * 1000f));
            var order = Enumerable.Range(0, nb).OrderByDescending(i => maxErr[i]).ToList();
            log.AppendLine("bones with the largest difference (mm, worst frame, mean):");
            for (int k = 0; k < 14; k++)
            {
                int i = order[k];
                log.AppendLine(string.Format("   {0,-22} max {1,6:F2}  at frame {2,2}   mean {3,6:F2}", d.bones[i], maxErr[i] * 1000f, worstFrame[i], sumErr[i] / d.frames * 1000f));
            }
            foreach (var nm in new[] { "Hips", "Head", "LeftFoot", "RightFoot", "LeftToes", "RightToes", "LeftHand", "RightHand", "LeftLowerLeg", "RightLowerLeg" })
            {
                int i = System.Array.IndexOf(d.bones, nm);
                if (i >= 0) log.AppendLine(string.Format("   (key bone) {0,-14} max {1,6:F2} mm, mean {2,6:F2} mm", nm, maxErr[i] * 1000f, sumErr[i] / d.frames * 1000f));
            }
            log.AppendLine("largest difference per frame (mm): " + string.Join(" ", frameMax.Select(v => (v * 1000f).ToString("F1")).ToArray()));

            // loop seam: normalized time 0 against 1
            anim.Play(stateName, 0, 0f); anim.Update(0f); anim.Update(0f);
            var p0 = bones.Select(x => x.t != null ? model.InverseTransformPoint(x.t.position) : Vector3.zero).ToArray();
            anim.Play(stateName, 0, 0.9999f); anim.Update(0f); anim.Update(0f);
            var p1 = bones.Select(x => x.t != null ? model.InverseTransformPoint(x.t.position) : Vector3.zero).ToArray();
            float seam = 0f; for (int b = 0; b < nb; b++) seam = Mathf.Max(seam, (p0[b] - p1[b]).magnitude);
            log.AppendLine("loop seam: largest bone jump between the end and the start of the cycle " + (seam * 1000f).ToString("F2") + " mm (one frame of movement is much more)");
            File.WriteAllText(Path.Combine(outputDir, "pose_parity.txt"), log.ToString());
            player.enabled = true;
            anim.speed = 1f;
            finished = true;
        }
    }
}
