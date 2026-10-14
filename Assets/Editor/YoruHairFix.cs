using UnityEditor;
using UnityEngine;

namespace ZeroProtocol.EditorTools
{
    /// <summary>
    /// VRoid exported the cap under the hair (material N00_000_00_HairBack_00_HAIR) with the default BROWN texture, only the
    /// strands carry the real hair colour, so a brown patch showed at the nape whenever the hair lifted.
    /// This puts the lilac strand texture (made by Tools/make_hair_cap_texture.py from the hair texture) on that material.
    /// Re-run it after the VRM has been re-imported (the importer rebuilds the materials).
    /// </summary>
    public static class YoruHairFix
    {
        public const string MaterialPath = "Assets/Characters/Yoru/ShiroganeYoru.Materials/N00_000_00_HairBack_00_HAIR (Instance).asset";
        public const string TexturePath = "Assets/Characters/Yoru/Textures/Yoru_HairBack_Lilac.png";

        public const string StrandTilePath = "Assets/Characters/Yoru/Textures/Yoru_HairStrands_Tile.png";

        /// <summary>Imports the seamless strand tile (repeat, no cut-out) used by the scalp shell and returns it.</summary>
        public static Texture2D PrepareStrandTile()
        {
            AssetDatabase.ImportAsset(StrandTilePath, ImportAssetOptions.ForceUpdate);
            var imp = AssetImporter.GetAtPath(StrandTilePath) as TextureImporter;
            if (imp != null)
            {
                imp.textureType = TextureImporterType.Default;
                imp.alphaIsTransparency = false;
                imp.sRGBTexture = true;
                imp.mipmapEnabled = true;
                imp.wrapMode = TextureWrapMode.Repeat;
                imp.filterMode = FilterMode.Bilinear;
                imp.SaveAndReimport();
            }
            return AssetDatabase.LoadAssetAtPath<Texture2D>(StrandTilePath);
        }

        [MenuItem("Zero Protocol/Fix Yoru Hair Cap")]
        public static void Apply()
        {
            AssetDatabase.ImportAsset(TexturePath, ImportAssetOptions.ForceUpdate);
            var imp = AssetImporter.GetAtPath(TexturePath) as TextureImporter;
            if (imp != null)
            {
                imp.textureType = TextureImporterType.Default;
                imp.alphaSource = TextureImporterAlphaSource.FromInput;
                imp.alphaIsTransparency = true;
                imp.sRGBTexture = true;
                imp.mipmapEnabled = true;
                imp.wrapMode = TextureWrapMode.Clamp;
                imp.maxTextureSize = 2048;
                imp.SaveAndReimport();
            }
            var mat = AssetDatabase.LoadAssetAtPath<Material>(MaterialPath);
            var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(TexturePath);
            if (mat == null || tex == null)
            {
                Debug.LogError("[YoruHairFix] material or texture missing: " + (mat == null) + " / " + (tex == null));
                return;
            }
            var old = mat.GetTexture("_MainTex");
            mat.SetTexture("_MainTex", tex);
            EditorUtility.SetDirty(mat);
            AssetDatabase.SaveAssets();
            Debug.Log("[YoruHairFix] hair cap texture " + (old != null ? old.name : "none") + " -> " + tex.name + " (shader " + mat.shader.name + ")");
        }
    }
}
