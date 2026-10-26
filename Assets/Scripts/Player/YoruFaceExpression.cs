using UnityEngine;

namespace ZeroProtocol.Player
{
    /// <summary>
    /// Yoru's base face: expression "B, cool and watchful" of the Blender idle v2 (Docs/Charakter_Yoru.md): focused eyes (upper lid down at the
    /// inner corner, lower lid up a little), a straight closed mouth, brows a little down. The humanoid clips do not contain the face, so the shape
    /// keys are set here, and they stay for walking and running.
    ///
    /// The values and the slow variation are the ones of the Blender idle (Blender/scripts/build_idle_v2_face.py EXPRESSIONS['B'],
    /// build_idle_v2_face_loop.py face_values(): lids +-10 %, mouth +-8 %, brows +-5 % over 12 s). While a blink closes the lid (YoruBlink.Lid)
    /// the mood lids are taken back with it, so they do not pile up on the closing lid (Blender: value * (1 - blink)).
    /// These shape keys are not bound to a VRM expression, so the VRMBlendShapeProxy leaves them alone; "Blink" (Fcl_EYE_Close) stays with YoruBlink.
    /// </summary>
    [DefaultExecutionOrder(100)]
    public class YoruFaceExpression : MonoBehaviour
    {
        [Tooltip("0 = neutral face, 1 = expression B as in Blender.")]
        [Range(0f, 1f)] public float strength = 1f;

        [Header("Expression B (shape key values 0..1)")]
        public float eyeAngry = 0.40f;
        public float eyeFun = 0.16f;
        public float mouthNeutral = 0.55f;
        public float mouthClose = 0.20f;
        public float browAngry = 0.50f;

        [Header("Slow variation (the Blender idle loop is 12 s)")]
        public float period = 12f;
        public float lidVariation = 0.10f;
        public float mouthVariation = 0.08f;
        public float browVariation = 0.05f;

        SkinnedMeshRenderer face;
        int iEyeAngry = -1, iEyeFun = -1, iMouthNeutral = -1, iMouthClose = -1, iBrowAngry = -1;
        YoruBlink blink;
        float clockOffset;

        void Awake()
        {
            foreach (var smr in GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                var mesh = smr.sharedMesh;
                if (mesh == null || mesh.GetBlendShapeIndex("Fcl_EYE_Close") < 0) continue;
                face = smr;
                iEyeAngry = mesh.GetBlendShapeIndex("Fcl_EYE_Angry");
                iEyeFun = mesh.GetBlendShapeIndex("Fcl_EYE_Fun");
                iMouthNeutral = mesh.GetBlendShapeIndex("Fcl_MTH_Neutral");
                iMouthClose = mesh.GetBlendShapeIndex("Fcl_MTH_Close");
                iBrowAngry = mesh.GetBlendShapeIndex("Fcl_BRW_Angry");
                break;
            }
            blink = GetComponent<YoruBlink>();
            clockOffset = Random.value * period;
        }

        void LateUpdate()
        {
            if (face == null) return;
            float w = 6.2832f / Mathf.Max(1f, period);
            float t = Time.time + clockOffset;
            float lid1 = 1f + lidVariation * (Mathf.Sin(w * t + 0.7f) + 0.35f * Mathf.Sin(3f * w * t + 2.2f)) / 1.35f;
            float lid2 = 1f + lidVariation * (Mathf.Sin(w * t + 2.4f) + 0.30f * Mathf.Sin(2f * w * t + 0.9f)) / 1.30f;
            float mouth = 1f + mouthVariation * (Mathf.Sin(w * t + 1.3f) + 0.30f * Mathf.Sin(3f * w * t + 0.4f)) / 1.30f;
            float brow = 1f + browVariation * Mathf.Sin(w * t + 2.1f);
            float open = 1f - (blink != null ? Mathf.Clamp01(blink.Lid) : 0f);
            Set(iEyeAngry, eyeAngry * lid1 * open);
            Set(iEyeFun, eyeFun * lid2 * open);
            Set(iMouthNeutral, mouthNeutral * mouth);
            Set(iMouthClose, mouthClose * mouth);
            Set(iBrowAngry, browAngry * brow);
        }

        void Set(int index, float value)
        {
            if (index >= 0) face.SetBlendShapeWeight(index, Mathf.Clamp01(value * strength) * 100f);
        }
    }
}
