using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using ZeroProtocol.CameraSystem;
using ZeroProtocol.Player;

namespace ZeroProtocol.EditorTools
{
    /// <summary>Builds the flat test arena scene (grid floor, crates, stairs, ramp, dummies, Yoru, camera).</summary>
    public static class ArenaBuilder
    {
        const string ScenePath = "Assets/Scenes/Arena.unity";
        const string YoruPrefabPath = "Assets/Characters/Yoru/ShiroganeYoru.prefab";
        // The first model (V1) had a bare scalp that YoruScalpShell covered with a shell of hair; Yoru V2 has the hair base fixed in the model.
        // Switch on again only if bare skin shows under the hair (check with HairLiftTest).
        static readonly bool UseScalpShell = false;
        const string MatDir = "Assets/Materials/Arena";

        [MenuItem("Zero Protocol/Build Test Arena")]
        public static void Build()
        {
            PlayerSettings.runInBackground = true;
            EditorSceneManager.SaveOpenScenes();

            Directory.CreateDirectory(MatDir);
            var floorMat = MakeMat("ArenaGrid", new Color(1f, 1f, 1f), GridTexture(), 80f);
            var crateMat = MakeMat("ArenaCrate", new Color(0.86f, 0.52f, 0.20f), null, 1f);
            var blockMat = MakeMat("ArenaBlock", new Color(0.62f, 0.66f, 0.72f), null, 1f);
            var dummyMat = MakeMat("ArenaDummy", new Color(0.80f, 0.25f, 0.25f), null, 1f);

            Scene scene = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);
            Directory.CreateDirectory("Assets/Scenes");

            var root = new GameObject("Arena").transform;

            // floor 80 x 80 m, the top surface sits at y = 0
            var floor = GameObject.CreatePrimitive(PrimitiveType.Cube);
            floor.name = "Floor";
            floor.transform.SetParent(root);
            floor.transform.position = new Vector3(0f, -0.5f, 0f);
            floor.transform.localScale = new Vector3(80f, 1f, 80f);
            floor.GetComponent<Renderer>().sharedMaterial = floorMat;

            // crates (size, position)
            Box(root, "Crate_S", new Vector3(1f, 1f, 1f), new Vector3(5f, 0.5f, 4f), crateMat);
            Box(root, "Crate_M", new Vector3(1.5f, 1.5f, 1.5f), new Vector3(7f, 0.75f, 6f), crateMat);
            Box(root, "Crate_L", new Vector3(2f, 2f, 2f), new Vector3(-6f, 1f, 5f), crateMat);
            Box(root, "Crate_Stack", new Vector3(1f, 1f, 1f), new Vector3(-6f, 2.5f, 5f), crateMat);
            Box(root, "Pillar_A", new Vector3(1.2f, 5f, 1.2f), new Vector3(-12f, 2.5f, -4f), blockMat);
            Box(root, "Pillar_B", new Vector3(1.2f, 5f, 1.2f), new Vector3(12f, 2.5f, -4f), blockMat);
            Box(root, "Wall_North", new Vector3(24f, 3f, 0.6f), new Vector3(0f, 1.5f, 30f), blockMat);

            // stairs (4 steps of 0.3 m) and a platform with a ramp
            for (int i = 0; i < 4; i++)
                Box(root, "Stair_" + i, new Vector3(3f, 0.3f * (i + 1), 0.8f),
                    new Vector3(-14f, 0.15f * (i + 1), 8f + 0.8f * i), blockMat);
            Box(root, "Platform", new Vector3(6f, 1.2f, 6f), new Vector3(14f, 0.6f, 12f), blockMat);
            var ramp = Box(root, "Ramp", new Vector3(3f, 0.3f, 6.5f), new Vector3(14f, 0.55f, 6.1f), blockMat);
            ramp.transform.rotation = Quaternion.Euler(-10.6f, 0f, 0f);

            // training dummies you can lock on to
            Dummy(root, "Dummy_1", new Vector3(0f, 1f, 12f), dummyMat);
            Dummy(root, "Dummy_2", new Vector3(-9f, 1f, 10f), dummyMat);
            Dummy(root, "Dummy_3", new Vector3(10f, 1f, 18f), dummyMat);

            // player: root with controller, Yoru as child model
            var yoruPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(YoruPrefabPath);
            var player = new GameObject("Player");
            player.tag = "Player";
            player.transform.position = new Vector3(0f, 0.05f, -4f);
            var cc = player.AddComponent<CharacterController>();
            cc.height = 1.5f; cc.radius = 0.28f; cc.center = new Vector3(0f, 0.78f, 0f);
            cc.stepOffset = 0.35f; cc.slopeLimit = 50f; cc.skinWidth = 0.03f;
            if (yoruPrefab != null)
            {
                var model = (GameObject)PrefabUtility.InstantiatePrefab(yoruPrefab);
                model.name = "Yoru";
                model.transform.SetParent(player.transform, false);
                var ctrl = AssetDatabase.LoadAssetAtPath<RuntimeAnimatorController>(YoruAnimatorBuilder.ControllerPath);
                var modelAnimator = model.GetComponent<Animator>();
                if (ctrl != null && modelAnimator != null) modelAnimator.runtimeAnimatorController = ctrl;
                model.AddComponent<YoruSecondaryMotion>();
                model.AddComponent<YoruBlink>();
                if (UseScalpShell)
                {
                    var scalp = model.AddComponent<YoruScalpShell>();
                    scalp.strandTexture = YoruHairFix.PrepareStrandTile();
                    scalp.baseMaterial = AssetDatabase.LoadAssetAtPath<Material>(YoruHairFix.MaterialPath);
                }
            }
            player.AddComponent<GameInput>();
            var controller = player.AddComponent<YoruController>();
            controller.animator = player.GetComponentInChildren<Animator>();
            player.AddComponent<LockOnSystem>();

            // camera
            var cam = Camera.main;
            cam.tag = "MainCamera";
            cam.nearClipPlane = 0.1f;
            cam.farClipPlane = 400f;
            var rig = cam.gameObject.AddComponent<ThirdPersonCamera>();
            rig.target = player.transform;
            rig.input = player.GetComponent<GameInput>();
            cam.gameObject.AddComponent<ControlsHint>();
            controller.cameraTransform = cam.transform;
            player.GetComponent<LockOnSystem>().cameraRig = rig;
            cam.transform.position = new Vector3(0f, 2.2f, -9f);

            PostFxBuilder.Add(cam);                                                      // global volume + motion blur slider

            var dirLight = Object.FindFirstObjectByType<Light>();
            if (dirLight != null) { dirLight.shadows = LightShadows.Soft; dirLight.intensity = 1.1f; }

            EditorSceneManager.SaveScene(scene, ScenePath);
            AssetDatabase.SaveAssets();
            Debug.Log("[ZeroProtocol] Arena built: " + ScenePath);
        }

        static GameObject Box(Transform parent, string name, Vector3 size, Vector3 pos, Material mat)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = name;
            go.transform.SetParent(parent);
            go.transform.position = pos;
            go.transform.localScale = size;
            go.GetComponent<Renderer>().sharedMaterial = mat;
            return go;
        }

        static void Dummy(Transform parent, string name, Vector3 pos, Material mat)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            go.name = name;
            go.transform.SetParent(parent);
            go.transform.position = pos;
            go.transform.localScale = new Vector3(0.9f, 1f, 0.9f);
            go.GetComponent<Renderer>().sharedMaterial = mat;
            var t = go.AddComponent<LockOnTarget>();
            t.aimHeight = 0.2f;
        }

        static Material MakeMat(string name, Color color, Texture2D tex, float tiling)
        {
            string path = MatDir + "/" + name + ".mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null)
            {
                mat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
                AssetDatabase.CreateAsset(mat, path);
            }
            mat.SetColor("_BaseColor", color);
            mat.SetFloat("_Smoothness", 0.15f);
            mat.SetFloat("_Metallic", 0f);
            if (tex != null)
            {
                mat.SetTexture("_BaseMap", tex);
                mat.SetTextureScale("_BaseMap", new Vector2(tiling, tiling));
            }
            EditorUtility.SetDirty(mat);
            return mat;
        }

        static Texture2D GridTexture()
        {
            string path = MatDir + "/Grid.png";
            if (!File.Exists(path))
            {
                const int n = 256;
                var tex = new Texture2D(n, n, TextureFormat.RGBA32, false);
                Color fill = new Color(0.32f, 0.35f, 0.39f), line = new Color(0.62f, 0.66f, 0.71f);
                for (int y = 0; y < n; y++)
                    for (int x = 0; x < n; x++)
                    {
                        bool edge = x < 3 || y < 3 || x >= n - 3 || y >= n - 3;
                        tex.SetPixel(x, y, edge ? line : fill);
                    }
                tex.Apply();
                File.WriteAllBytes(path, tex.EncodeToPNG());
                Object.DestroyImmediate(tex);
                AssetDatabase.ImportAsset(path);
                var imp = (TextureImporter)AssetImporter.GetAtPath(path);
                imp.wrapMode = TextureWrapMode.Repeat;
                imp.mipmapEnabled = true;
                imp.filterMode = FilterMode.Trilinear;
                imp.anisoLevel = 8;
                imp.SaveAndReimport();
            }
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }
    }
}
