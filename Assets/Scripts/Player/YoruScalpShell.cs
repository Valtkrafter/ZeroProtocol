using System.Collections.Generic;
using UnityEngine;

namespace ZeroProtocol.Player
{
    /// <summary>
    /// Covers the head under the hair: VRoid only gives Yoru a thin cap and bare skin elsewhere, so when the hair lifts
    /// (wind, running, jumping) skin showed at the back of the head and at the nape. This builds a thin shell of hair
    /// (lilac strand texture) over the skin of the back of the head, the crown and the nape. The shell is made from the
    /// triangles of the original skin, pushed out a few millimetres, and skinned to the same bones, so it follows head and neck.
    /// It is built when the character starts, so it also survives a re-import of the VRM.
    /// </summary>
    public class YoruScalpShell : MonoBehaviour
    {
        [Header("Look")]
        public Texture2D strandTexture;
        public Material baseMaterial;                 // any unlit hair material, only its shader / settings are copied
        public float pushOut = 0.0035f;               // metres above the skin
        public float strandsAround = 3f;              // tile repeats around the head
        public float strandsPerMetre = 6f;            // tile repeats per metre of height

        [Header("Region (model space, +Z forward, head bone at y 1.365)")]
        [Tooltip("Face skin behind this plane (z) ...")]
        public float faceBackZ = 0.03f;
        [Tooltip("... and above this height (the bottom of the head mesh is at 1.331)")]
        public float faceMinY = 1.331f;
        [Tooltip("Crown: everything above this height up to this z (towards the forehead hairline)")]
        public float crownY = 1.50f;
        public float crownMaxZ = 0.07f;
        [Tooltip("Nape (body skin): height range, behind this z, half width")]
        public float napeMinY = 1.255f;
        public float napeMaxY = 1.345f;
        public float napeBackZ = -0.012f;
        public float napeHalfWidth = 0.085f;

        public int shellTriangles { get; private set; }

        void Awake()
        {
            if (strandTexture == null || baseMaterial == null) { enabled = false; return; }
            var mat = new Material(baseMaterial) { name = "YoruScalpShell" };
            mat.SetTexture("_MainTex", strandTexture);
            mat.SetColor("_Color", Color.white);
            strandTexture.wrapMode = TextureWrapMode.Repeat;

            var animator = GetComponent<Animator>();
            Vector3 headPos = transform.InverseTransformPoint(animator.GetBoneTransform(HumanBodyBones.Head).position);
            foreach (var smr in GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                if (smr.name != "Face" && smr.name != "Body") continue;
                bool face = smr.name == "Face";
                var shell = Build(smr, face, headPos, mat);
                if (shell != null) shellTriangles += shell.sharedMesh.triangles.Length / 3;
            }
        }

        bool InRegion(Vector3 p, bool face)
        {
            if (face) return (p.z < faceBackZ && p.y > faceMinY) || (p.y > crownY && p.z < crownMaxZ);
            return p.y > napeMinY && p.y < napeMaxY && p.z < napeBackZ && Mathf.Abs(p.x) < napeHalfWidth;
        }

        SkinnedMeshRenderer Build(SkinnedMeshRenderer src, bool face, Vector3 headPos, Material mat)
        {
            var mesh = src.sharedMesh;
            if (mesh == null || !mesh.isReadable) return null;
            var verts = mesh.vertices;
            var normals = mesh.normals;
            var weights = mesh.boneWeights;
            int skinSub = -1;
            for (int i = 0; i < src.sharedMaterials.Length; i++)
                if (src.sharedMaterials[i] != null && src.sharedMaterials[i].name.Contains("SKIN")) { skinSub = i; break; }
            if (skinSub < 0) return null;

            // vertices in model space
            var sel = new bool[verts.Length];
            var model = new Vector3[verts.Length];
            for (int i = 0; i < verts.Length; i++)
            {
                model[i] = transform.InverseTransformPoint(src.transform.TransformPoint(verts[i]));
                sel[i] = InRegion(model[i], face);
            }

            var remap = new Dictionary<int, int>();
            var nv = new List<Vector3>(); var nn = new List<Vector3>(); var nuv = new List<Vector2>(); var nw = new List<BoneWeight>();
            var tris = new List<int>();
            var srcTris = mesh.GetTriangles(skinSub);
            for (int t = 0; t < srcTris.Length; t += 3)
            {
                int a = srcTris[t], b = srcTris[t + 1], c = srcTris[t + 2];
                if (!(sel[a] && sel[b] && sel[c])) continue;
                foreach (int idx in new[] { a, b, c })
                {
                    int m;
                    if (!remap.TryGetValue(idx, out m))
                    {
                        m = nv.Count;
                        remap[idx] = m;
                        Vector3 n = normals.Length > idx ? normals[idx] : Vector3.up;
                        nv.Add(verts[idx] + n.normalized * pushOut);          // mesh space, normal in mesh space
                        nn.Add(n);
                        Vector3 p = model[idx];
                        float u = Mathf.Atan2(p.x, p.z - 0.01f) / (2f * Mathf.PI) * strandsAround;
                        nuv.Add(new Vector2(u, p.y * strandsPerMetre));
                        nw.Add(weights[idx]);
                    }
                    tris.Add(m);
                }
            }
            if (tris.Count == 0) return null;

            var shellMesh = new Mesh { name = "ScalpShell_" + src.name };
            shellMesh.SetVertices(nv);
            shellMesh.SetNormals(nn);
            shellMesh.SetUVs(0, nuv);
            shellMesh.SetTriangles(tris, 0);
            shellMesh.boneWeights = nw.ToArray();
            shellMesh.bindposes = mesh.bindposes;
            shellMesh.RecalculateBounds();

            var go = new GameObject("ScalpShell_" + src.name);
            go.transform.SetParent(src.transform.parent, false);
            go.transform.localPosition = src.transform.localPosition;
            go.transform.localRotation = src.transform.localRotation;
            go.transform.localScale = src.transform.localScale;
            var r = go.AddComponent<SkinnedMeshRenderer>();
            r.sharedMesh = shellMesh;
            r.bones = src.bones;
            r.rootBone = src.rootBone;
            r.sharedMaterial = mat;
            r.updateWhenOffscreen = true;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            return r;
        }
    }
}
