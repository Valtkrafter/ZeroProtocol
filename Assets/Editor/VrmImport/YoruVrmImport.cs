using System.Collections.Generic;
using System.IO;
using UniGLTF;
using UnityEditor;
using UnityEngine;
using VRM;

namespace ZeroProtocol.EditorTools
{
    /// <summary>
    /// Imports Assets/Characters/Yoru/ShiroganeYoru.vrm completely and in one go: textures, materials, meshes, avatar, blend shapes, prefab.
    /// UniVRM's own AssetPostprocessor does the second half of the import inside EditorApplication.delayCall, which never runs while Unity
    /// is in the background (the MCP drives Unity from outside), so this repeats exactly that second half synchronously
    /// (the code is the body of vrmAssetPostprocessor.ImportVrmAndCreatePrefab, onCompleted).
    /// New model version: move the old ShiroganeYoru.* files and folders out of Assets/Characters/Yoru, copy the new .vrm there as
    /// ShiroganeYoru.vrm, let Unity import it (that writes ShiroganeYoru.Textures), then run the menu item.
    /// </summary>
    public static class YoruVrmImport
    {
        public const string VrmPath = "Assets/Characters/Yoru/ShiroganeYoru.vrm";
        public const string PrefabPath = "Assets/Characters/Yoru/ShiroganeYoru.prefab";
        const string TextureDir = "Assets/Characters/Yoru/ShiroganeYoru.Textures";

        [MenuItem("Zero Protocol/Import Yoru VRM")]
        public static void Import()
        {
            var sw = System.Diagnostics.Stopwatch.StartNew();
            AssetDatabase.Refresh();
            var map = new Dictionary<SubAssetKey, Object>();
            foreach (var f in Directory.GetFiles(TextureDir, "*.png"))
            {
                var tex = AssetDatabase.LoadAssetAtPath<Texture>(f.Replace('\\', '/'));
                if (tex != null) map[new SubAssetKey(tex)] = tex;
            }
            try
            {
                AssetDatabase.StartAssetEditing();
                using (var data = new GlbFileParser(Path.GetFullPath(VrmPath)).Parse())
                using (var context = new VRMImporterContext(new VRMData(data), externalObjectMap: map, settings: new ImporterContextSettings()))
                {
                    var editor = new VRMEditorImporterContext(context, UnityPath.FromUnityPath(PrefabPath));
                    foreach (var textureInfo in context.TextureDescriptorGenerator.Get().GetEnumerable())
                        TextureImporterConfigurator.Configure(textureInfo, context.TextureFactory.ExternalTextures);
                    var loaded = context.Load();
                    editor.SaveAsAsset(loaded);
                }
            }
            finally
            {
                AssetDatabase.StopAssetEditing();
            }
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log("[YoruVrmImport] " + VrmPath + " imported: " + map.Count + " textures, prefab " + PrefabPath + ", " + sw.ElapsedMilliseconds + " ms");
        }
    }
}
