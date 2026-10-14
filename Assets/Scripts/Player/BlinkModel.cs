using System;
using System.Collections.Generic;

namespace ZeroProtocol.Player
{
    /// <summary>One blink: the lid goes down in Close seconds, stays at Amp for Hold seconds, comes up in Open seconds (times in seconds).</summary>
    public struct Blink
    {
        public double Start, Amp, Close, Hold, Open;

        public double End { get { return Start + Close + Hold + Open; } }

        /// <summary>Lid closure 0 (open) .. Amp (shut) at the absolute time t.</summary>
        public double Lid(double t)
        {
            t -= Start;
            if (t <= 0.0) return 0.0;
            if (t < Close) return Amp * BlinkModel.Smoother(Math.Pow(t / Close, BlinkModel.CloseWarp));
            t -= Close;
            if (t < Hold) return Amp;
            t -= Hold;
            if (t < Open)
            {
                double u = t / Open;
                return Amp * (1.0 - BlinkModel.Smoother(1.0 - Math.Pow(1.0 - u, BlinkModel.OpenWarp)));
            }
            return 0.0;
        }
    }

    /// <summary>mulberry32, the same 32 bit generator as Blender/scripts/blink_model.py (uniform in [0, 1)).</summary>
    public sealed class BlinkRng
    {
        uint s;

        public BlinkRng(uint seed) { s = seed; }

        public double Next()
        {
            unchecked
            {
                s += 0x6D2B79F5u;
                uint t = s;
                t = (t ^ (t >> 15)) * (t | 1u);
                t ^= t + (t ^ (t >> 7)) * (t | 61u);
                return (t ^ (t >> 14)) / 4294967296.0;
            }
        }
    }

    /// <summary>
    /// Yoru's blink model, a line-by-line port of Blender/scripts/blink_model.py (read that file for the reasoning and the references):
    /// fast closing, a short hold, an opening about twice as slow, irregular gaps (log-normal), now and then a weaker blink and a double blink.
    /// The same seed gives the same blinks in Blender (Blender/Yoru_Blink.json) and in the game; BlinkVerifyTest checks it number by number.
    /// Plain C# without UnityEngine, so the editor can run it as well. The numbers are the ones the user chose in Blender
    /// ("seltener, ca. alle 6 s" and "knackiger"); keep them equal to blink_model.PARAMS.
    /// </summary>
    public static class BlinkModel
    {
        public const double MedianInterval = 5.2, Sigma = 0.40, MinInterval = 1.6, MaxInterval = 10.0;    // gap from the END of one group to the START of the next (s)
        public const double FirstMin = 1.3, FirstMax = 2.3;                                                  // start of the very first blink (s)
        public const double PPartial = 0.12, PartialLo = 0.55, PartialHi = 0.85;                             // weaker blinks
        public const double TClose = 0.060, CloseSpread = 0.12;                                             // closing time (s), relative spread
        public const double OpenRatioLo = 1.9, OpenRatioHi = 2.3;                                            // opening time = closing time * ratio
        public const double HoldLo = 0.015, HoldHi = 0.040;                                                  // time with the lid fully down (s)
        public const double PDouble = 0.14, OverlapLo = 0.45, OverlapHi = 0.75, DoubleMinOnset = 0.18;       // double blinks
        public const double Amp2Lo = 0.80, Amp2Hi = 1.00;
        public const double CloseWarp = 0.80, OpenWarp = 1.8;                                               // shape of the lid speed
        public const int DrawsPerGroup = 10;

        public static double Smoother(double u) { return u * u * u * (u * (u * 6.0 - 15.0) + 10.0); }

        /// <summary>Lid closure at the time t for a set of blinks (the lowest lid wins when two blinks overlap).</summary>
        public static double Weight(IList<Blink> blinks, double t)
        {
            double w = 0.0;
            for (int i = 0; i < blinks.Count; i++)
            {
                var b = blinks[i];
                if (b.Start - 1e-9 <= t && t <= b.End) w = Math.Max(w, b.Lid(t));
            }
            return w;
        }

        /// <summary>All blink groups (1 blink, or 2 for a double blink) that start and end inside [0, seconds - marginEnd].</summary>
        public static List<Blink[]> Groups(uint seed, double seconds, double marginEnd = 0.5)
        {
            var gen = new BlinkGenerator(seed);
            var list = new List<Blink[]>();
            while (true)
            {
                var g = gen.NextGroup();
                double end = 0.0;
                foreach (var b in g) end = Math.Max(end, b.End);
                if (end > seconds - marginEnd) break;
                list.Add(g);
            }
            return list;
        }
    }

    /// <summary>Endless stream of blinks for one seed; NextGroup() returns the blinks of one group.</summary>
    public sealed class BlinkGenerator
    {
        readonly BlinkRng rng;
        double tEnd;
        bool first = true;

        public BlinkGenerator(uint seed) { rng = new BlinkRng(seed); }

        /// <summary>End of the last group that was handed out (s).</summary>
        public double LastEnd { get { return tEnd; } }

        public Blink[] NextGroup(double intervalScale = 1.0)
        {
            var u = new double[BlinkModel.DrawsPerGroup];
            for (int i = 0; i < u.Length; i++) u[i] = rng.Next();
            double z = Math.Sqrt(-2.0 * Math.Log(1.0 - u[0])) * Math.Cos(2.0 * Math.PI * u[1]);               // normal(0, 1), Box-Muller
            double start;
            if (first)
            {
                start = BlinkModel.FirstMin + u[2] * (BlinkModel.FirstMax - BlinkModel.FirstMin);
                first = false;
            }
            else
            {
                double iv = Math.Exp(Math.Log(BlinkModel.MedianInterval) + BlinkModel.Sigma * z) * intervalScale;
                start = tEnd + Math.Min(Math.Max(iv, BlinkModel.MinInterval), BlinkModel.MaxInterval);
            }
            bool partial = u[3] < BlinkModel.PPartial;
            double amp = partial ? BlinkModel.PartialLo + u[4] * (BlinkModel.PartialHi - BlinkModel.PartialLo) : 1.0;
            double dur = Math.Sqrt(amp);                                                                        // weaker blinks are shorter
            double z2 = Math.Sqrt(-2.0 * Math.Log(1.0 - u[5])) * Math.Cos(2.0 * Math.PI * u[6]);
            double close = BlinkModel.TClose * (1.0 + Math.Min(Math.Max(BlinkModel.CloseSpread * z2, -0.25), 0.25)) * dur;
            double open = close * (BlinkModel.OpenRatioLo + u[7] * (BlinkModel.OpenRatioHi - BlinkModel.OpenRatioLo));
            double hold = (BlinkModel.HoldLo + u[8] * (BlinkModel.HoldHi - BlinkModel.HoldLo)) * (partial ? 0.3 : 1.0);
            var b1 = new Blink { Start = start, Amp = amp, Close = close, Hold = hold, Open = open };
            Blink[] group;
            double v0 = rng.Next(), v1 = rng.Next();                                                            // always drawn, so the sequence does not depend on the branch
            if (u[9] < BlinkModel.PDouble)
            {
                double s2 = Math.Max(start + close + hold + open * (BlinkModel.OverlapLo + v0 * (BlinkModel.OverlapHi - BlinkModel.OverlapLo)), start + BlinkModel.DoubleMinOnset);
                double a2 = amp * (BlinkModel.Amp2Lo + v1 * (BlinkModel.Amp2Hi - BlinkModel.Amp2Lo));
                var b2 = new Blink { Start = s2, Amp = a2, Close = close * 0.95, Hold = hold * 0.6, Open = open * 0.9 };
                group = new[] { b1, b2 };
            }
            else group = new[] { b1 };
            tEnd = 0.0;
            foreach (var b in group) tEnd = Math.Max(tEnd, b.End);
            return group;
        }
    }
}
