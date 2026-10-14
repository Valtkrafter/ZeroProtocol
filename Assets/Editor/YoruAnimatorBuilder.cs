using System.IO;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

namespace ZeroProtocol.EditorTools
{
    /// <summary>
    /// Builds Yoru's Animator Controller from the clips baked from Blender (Assets/Animations/Yoru/Yoru_*.anim).
    /// It uses whatever clips exist, so it can be run again after every new animation:
    ///   Locomotion   Yoru_Idle alone, or a 1D blend tree on the ground speed (m/s) once Yoru_Walk / Yoru_Run exist
    ///   (jump / landing / dash states are added later together with their clips)
    /// The parameters are declared up front so the controller script (YoruController) can already feed them.
    /// </summary>
    public static class YoruAnimatorBuilder
    {
        public const string ControllerPath = "Assets/Animations/Yoru/YoruLocomotion.controller";
        const string Dir = "Assets/Animations/Yoru/";

        [MenuItem("Zero Protocol/Build Yoru Animator")]
        public static void Build()
        {
            Directory.CreateDirectory("Assets/Animations/Yoru");
            var idle = Load("Yoru_Idle");
            var walk = Load("Yoru_Walk");
            var run = Load("Yoru_Run");

            var ctrl = AnimatorController.CreateAnimatorControllerAtPath(ControllerPath);
            ctrl.AddParameter("Speed", AnimatorControllerParameterType.Float);          // ground speed m/s
            ctrl.AddParameter("LocoMult", AnimatorControllerParameterType.Float);       // run clip speed factor
            ctrl.AddParameter("Grounded", AnimatorControllerParameterType.Bool);
            ctrl.AddParameter("VerticalVelocity", AnimatorControllerParameterType.Float);
            ctrl.AddParameter("AirPhase", AnimatorControllerParameterType.Float);
            ctrl.AddParameter("RunJump", AnimatorControllerParameterType.Bool);
            ctrl.AddParameter("Dashing", AnimatorControllerParameterType.Bool);
            var ps = ctrl.parameters;
            for (int i = 0; i < ps.Length; i++)
            {
                if (ps[i].name == "LocoMult") ps[i].defaultFloat = 1f;
                if (ps[i].name == "Grounded") ps[i].defaultBool = true;
            }
            ctrl.parameters = ps;

            var sm = ctrl.layers[0].stateMachine;
            AnimatorState loco;
            if (walk == null && run == null)
            {
                loco = sm.AddState("Locomotion");
                loco.motion = idle;
            }
            else
            {
                BlendTree tree;
                loco = ctrl.CreateBlendTreeInController("Locomotion", out tree);
                tree.blendType = BlendTreeType.Simple1D;
                tree.blendParameter = "Speed";
                tree.useAutomaticThresholds = false;
                tree.AddChild(idle, 0f);
                if (walk != null) tree.AddChild(walk, WalkSpeed);
                if (run != null) tree.AddChild(run, RunSpeed);
                loco.speedParameterActive = true;
                loco.speedParameter = "LocoMult";
            }
            sm.defaultState = loco;

            EditorUtility.SetDirty(ctrl);
            AssetDatabase.SaveAssets();
            Debug.Log("[YoruAnimatorBuilder] built " + ControllerPath + ": idle=" + (idle != null) + " walk=" + (walk != null) + " run=" + (run != null));
        }

        // ground speeds (m/s) the walk and run cycles were authored for; set when the clips are made
        // (walk: Blender/Yoru_Walk_gait.json speed 1.15, stride 0.997 m; the same number is YoruController.walkSpeed)
        const float WalkSpeed = 1.15f;
        const float RunSpeed = 4.4f;

        static AnimationClip Load(string name)
        {
            return AssetDatabase.LoadAssetAtPath<AnimationClip>(Dir + name + ".anim");
        }
    }
}
