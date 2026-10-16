using System.IO;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace ZeroProtocol.EditorTools
{
    /// <summary>
    /// The file VERSION in the project folder is the one source of the version number (SemVer, see Docs/VERSIONING.md).
    /// This copies it into the Unity player settings (Application.version in the game) when the editor loads and right before every build.
    /// </summary>
    [InitializeOnLoad]
    public class VersionSync : IPreprocessBuildWithReport
    {
        public int callbackOrder => 0;

        static VersionSync()
        {
            EditorApplication.delayCall += Sync;
        }

        [MenuItem("Zero Protocol/Sync Version from VERSION file")]
        public static void Sync()
        {
            string path = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "VERSION"));
            if (!File.Exists(path)) { Debug.LogWarning("[VersionSync] file not found: " + path); return; }
            string version = File.ReadAllText(path).Trim();
            if (string.IsNullOrEmpty(version) || PlayerSettings.bundleVersion == version) return;
            PlayerSettings.bundleVersion = version;
            Debug.Log("[VersionSync] version set to " + version);
        }

        public void OnPreprocessBuild(BuildReport report)
        {
            Sync();
        }
    }
}
