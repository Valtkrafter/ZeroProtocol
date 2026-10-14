using System.Collections.Generic;
using UnityEngine;

namespace ZeroProtocol.CameraSystem
{
    /// <summary>Marks anything the player can lock on to (enemies, training dummies, bosses).</summary>
    public class LockOnTarget : MonoBehaviour
    {
        public static readonly List<LockOnTarget> All = new List<LockOnTarget>();

        /// <summary>Height of the point the camera and the marker aim at.</summary>
        public float aimHeight = 1.0f;

        public Vector3 AimPoint { get { return transform.position + Vector3.up * aimHeight; } }

        void OnEnable() { All.Add(this); }
        void OnDisable() { All.Remove(this); }
    }
}
