using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using ZeroProtocol.Settings;

namespace ZeroProtocol.EditorTools
{
    /// <summary>
    /// Adds the post-processing of the game to the open scene: a global Volume with its own profile (Motion Blur for now, more effects later: bloom,
    /// colour grading ...) and the PostFxSettings component that holds the slider of the player. Safe to run again (it reuses what exists).
    /// </summary>
    public static class PostFxBuilder
    {
        public const string ProfilePath = "Assets/Settings/ArenaPostFx.asset";

        [MenuItem("Zero Protocol/Add Post Processing (Motion Blur Slider)")]
        public static void AddToOpenScene()
        {
            var cam = Camera.main;
            if (cam == null) { Debug.LogError("[PostFxBuilder] no main camera in the open scene"); return; }
            Add(cam);
            EditorSceneManager.SaveOpenScenes();
            AssetDatabase.SaveAssets();
        }

        public static void Add(Camera cam)
        {
            Directory.CreateDirectory("Assets/Settings");
            var profile = AssetDatabase.LoadAssetAtPath<VolumeProfile>(ProfilePath);
            if (profile == null)
            {
                profile = ScriptableObject.CreateInstance<VolumeProfile>();
                AssetDatabase.CreateAsset(profile, ProfilePath);
            }
            if (!profile.TryGet(out MotionBlur mb)) mb = profile.Add<MotionBlur>(true);
            if (string.IsNullOrEmpty(AssetDatabase.GetAssetPath(mb))) { mb.name = nameof(MotionBlur); AssetDatabase.AddObjectToAsset(mb, profile); }      // a component of a profile asset is a sub asset: without this it is lost when the asset is loaded again
            mb.active = true;
            mb.mode.Override(MotionBlurMode.CameraAndObjects);
            mb.quality.Override(MotionBlurQuality.High);
            mb.clamp.Override(0.06f);
            mb.intensity.Override(0.4f);
            EditorUtility.SetDirty(profile);
            EditorUtility.SetDirty(mb);
            AssetDatabase.SaveAssets();

            var go = GameObject.Find("PostProcessing");
            if (go == null) go = new GameObject("PostProcessing");
            var volume = go.GetComponent<Volume>() ?? go.AddComponent<Volume>();
            volume.isGlobal = true;
            volume.priority = 10f;
            volume.sharedProfile = profile;
            var settings = go.GetComponent<PostFxSettings>() ?? go.AddComponent<PostFxSettings>();
            settings.volume = volume;

            cam.GetUniversalAdditionalCameraData().renderPostProcessing = true;
            Debug.Log("[PostFxBuilder] global volume 'PostProcessing' with Motion Blur (camera and objects) and the slider component added; the camera renders post processing");
        }
    }
}
