using System.Collections.Generic;
using UnityEngine;
using VRM;

namespace ZeroProtocol.Player
{
    /// <summary>
    /// Natural blinking through the VRM blend shape "Blink" (Fcl_EYE_Close, both eyes together). The idle / walk clips do not contain the face.
    /// The blinks come from BlinkModel, the same model as in Blender (Blender/scripts/blink_model.py, preview Blender/Yoru_Walk.blend):
    /// the lid closes in about 60 ms, stays shut for 15 to 40 ms and opens in about 125 ms; the gap to the next blink is irregular
    /// (about 6 s on average, never under 1.6 s), now and then a weaker blink and a double blink.
    /// With the same fixedSeed the blinks are the ones in Blender/Yoru_Blink.json (seed 312).
    /// </summary>
    public class YoruBlink : MonoBehaviour
    {
        [Tooltip("Multiplies the gap between blinks: 1 = about every 6 s, 0.5 = twice as often, 2 = rarely.")]
        public float intervalScale = 1f;
        [Tooltip("-1 = a new random sequence at every start, 0 or more = always the same blinks (tests, Blender comparison).")]
        public int fixedSeed = -1;

        /// <summary>Lid closure that was sent to the face last frame, 0 = open, 1 = shut.</summary>
        public float Lid { get; private set; }
        /// <summary>Seconds since this component started (the clock of the blink model).</summary>
        public double Clock { get; private set; }
        public uint Seed { get; private set; }
        /// <summary>Number of blinks (a double blink counts twice) that have started so far.</summary>
        public int BlinksStarted { get; private set; }

        VRMBlendShapeProxy proxy;
        BlendShapeKey blink;
        BlinkGenerator generator;
        readonly List<Blink> pending = new List<Blink>();
        readonly Queue<double> startTimes = new Queue<double>();
        double queuedUntil;
        float sent = -1f;

        void Awake()
        {
            proxy = GetComponent<VRMBlendShapeProxy>();
            blink = BlendShapeKey.CreateFromPreset(BlendShapePreset.Blink);
            Restart(fixedSeed);
        }

        /// <summary>Starts the blink sequence of a seed from the beginning (clock 0); a negative seed picks a random one.</summary>
        public void Restart(int seed)
        {
            fixedSeed = seed;
            Seed = seed >= 0 ? (uint)seed : (uint)(System.Environment.TickCount ^ (GetInstanceID() * 7919));
            generator = new BlinkGenerator(Seed);
            pending.Clear();
            startTimes.Clear();
            queuedUntil = 0.0;
            Clock = 0.0;
            BlinksStarted = 0;
            Lid = 0f;
            sent = -1f;
        }

        void Update()
        {
            if (proxy == null) return;
            Clock += Time.deltaTime;

            // keep about two seconds of blinks queued ahead of the clock
            while (queuedUntil < Clock + 2.0)
            {
                foreach (var b in generator.NextGroup(intervalScale)) { pending.Add(b); startTimes.Enqueue(b.Start); }
                queuedUntil = generator.LastEnd;
            }
            while (startTimes.Count > 0 && startTimes.Peek() <= Clock) { startTimes.Dequeue(); BlinksStarted++; }

            double lid = 0.0;
            for (int i = pending.Count - 1; i >= 0; i--)
            {
                var b = pending[i];
                if (b.End < Clock - 0.05) { pending.RemoveAt(i); continue; }
                if (b.Start <= Clock) lid = System.Math.Max(lid, b.Lid(Clock));
            }
            Lid = (float)lid;
            if (Mathf.Abs(Lid - sent) > 0.0005f || (Lid == 0f && sent != 0f))
            {
                proxy.ImmediatelySetValue(blink, Lid);
                sent = Lid;
            }
        }
    }
}
