using System;
using System.Text;
using UnityEngine;

namespace ZeroProtocol.Combat
{
    /// <summary>
    /// Proximity floating holographic cyber-terminal on each firing stall counter.
    /// Detects player presence in stall trigger volume. Displays live target status,
    /// distance, hit count, score, grouping spread in cm, and target mini-schematic.
    /// Handles hotkeys [1-4] Distance, [T] Recall, [F] Fresh Paper, [R] Reset Steel Targets.
    /// Zero runtime GC allocations.
    /// </summary>
    public class RangeTerminal : MonoBehaviour
    {
        [Header("Lane & Components")]
        public string laneName = "LANE 01";
        public TargetTrolley trolley;
        public PaperTarget paperTarget;
        public PopperTarget[] steelPoppers;
        public ShootingTarget[] laneTargets;

        [Header("Display Visuals")]
        public TextMesh terminalTextMesh;
        public Renderer screenRenderer;
        public Light terminalLight;
        public Color activeTextColor = new Color(0.0f, 0.941f, 1.0f); // #00F0FF
        public Color standbyTextColor = new Color(0.25f, 0.35f, 0.45f);

        [Header("Proximity State")]
        public bool isPlayerInside;

        // Pre-allocated buffers for Zero GC display and target plotting
        readonly StringBuilder displayBuilder = new StringBuilder(1024);
        readonly char[,] schematicGrid = new char[5, 5];

        void Awake()
        {
            if (trolley == null) trolley = GetComponentInParent<TargetTrolley>();
            if (paperTarget == null && trolley != null) paperTarget = trolley.paperTarget;

            UpdateDisplay();
        }

        void OnEnable()
        {
            SubscribeEvents();
        }

        void OnDisable()
        {
            UnsubscribeEvents();
        }

        void OnDestroy()
        {
            UnsubscribeEvents();
        }

        void SubscribeEvents()
        {
            if (paperTarget != null)
            {
                paperTarget.OnTargetHit -= HandlePaperTargetHit;
                paperTarget.OnTargetHit += HandlePaperTargetHit;
                paperTarget.OnPaperRefreshed -= HandlePaperRefreshed;
                paperTarget.OnPaperRefreshed += HandlePaperRefreshed;
            }

            if (trolley != null)
            {
                trolley.OnDistanceChanged -= HandleDistanceChanged;
                trolley.OnDistanceChanged += HandleDistanceChanged;
                trolley.OnArrived -= HandleTrolleyArrived;
                trolley.OnArrived += HandleTrolleyArrived;
            }
        }

        void UnsubscribeEvents()
        {
            if (paperTarget != null)
            {
                paperTarget.OnTargetHit -= HandlePaperTargetHit;
                paperTarget.OnPaperRefreshed -= HandlePaperRefreshed;
            }

            if (trolley != null)
            {
                trolley.OnDistanceChanged -= HandleDistanceChanged;
                trolley.OnArrived -= HandleTrolleyArrived;
            }
        }

        void OnTriggerEnter(Collider other)
        {
            if (other.CompareTag("Player") || other.GetComponent<ZeroProtocol.Player.YoruController>() != null || other.GetComponent<CharacterController>() != null)
            {
                SetPlayerInside(true);
            }
        }

        void OnTriggerExit(Collider other)
        {
            if (other.CompareTag("Player") || other.GetComponent<ZeroProtocol.Player.YoruController>() != null || other.GetComponent<CharacterController>() != null)
            {
                SetPlayerInside(false);
            }
        }

        void Update()
        {
            if (!isPlayerInside) return;

            // Direct keyboard hotkeys while player stands in stall
            if (Input.GetKeyDown(KeyCode.Alpha1) || Input.GetKeyDown(KeyCode.Keypad1))
            {
                SendTo5M();
            }
            else if (Input.GetKeyDown(KeyCode.Alpha2) || Input.GetKeyDown(KeyCode.Keypad2))
            {
                SendTo10M();
            }
            else if (Input.GetKeyDown(KeyCode.Alpha3) || Input.GetKeyDown(KeyCode.Keypad3))
            {
                SendTo15M();
            }
            else if (Input.GetKeyDown(KeyCode.Alpha4) || Input.GetKeyDown(KeyCode.Keypad4))
            {
                SendTo25M();
            }
            else if (Input.GetKeyDown(KeyCode.T))
            {
                RecallTarget();
            }
            else if (Input.GetKeyDown(KeyCode.F))
            {
                FreshPaper();
            }
            else if (Input.GetKeyDown(KeyCode.R))
            {
                ResetSteelTargets();
            }
        }

        public void SetPlayerInside(bool inside)
        {
            isPlayerInside = inside;

            if (terminalLight != null)
            {
                terminalLight.enabled = inside;
            }

            if (terminalTextMesh != null)
            {
                terminalTextMesh.color = inside ? activeTextColor : standbyTextColor;
            }

            UpdateDisplay();
        }

        public void SendTo5M()
        {
            if (trolley != null) trolley.SendTo5M();
            UpdateDisplay();
        }

        public void SendTo10M()
        {
            if (trolley != null) trolley.SendTo10M();
            UpdateDisplay();
        }

        public void SendTo15M()
        {
            if (trolley != null) trolley.SendTo15M();
            UpdateDisplay();
        }

        public void SendTo25M()
        {
            if (trolley != null) trolley.SendTo25M();
            UpdateDisplay();
        }

        public void RecallTarget()
        {
            if (trolley != null) trolley.Recall();
            UpdateDisplay();
        }

        public void FreshPaper()
        {
            if (paperTarget != null) paperTarget.FreshPaper();
            UpdateDisplay();
        }

        public void ResetSteelTargets()
        {
            if (steelPoppers != null)
            {
                for (int i = 0; i < steelPoppers.Length; i++)
                {
                    if (steelPoppers[i] != null)
                    {
                        steelPoppers[i].ResetTarget();
                    }
                }
            }

            if (laneTargets != null)
            {
                for (int i = 0; i < laneTargets.Length; i++)
                {
                    if (laneTargets[i] != null)
                    {
                        laneTargets[i].ResetTarget();
                    }
                }
            }

            UpdateDisplay();
        }

        void HandlePaperTargetHit(PaperTarget target, Vector2 coord, int score)
        {
            UpdateDisplay();
        }

        void HandlePaperRefreshed(PaperTarget target)
        {
            UpdateDisplay();
        }

        void HandleDistanceChanged(TargetTrolley t, float dist)
        {
            UpdateDisplay();
        }

        void HandleTrolleyArrived(TargetTrolley t)
        {
            UpdateDisplay();
        }

        public void UpdateDisplay()
        {
            if (terminalTextMesh == null) return;

            displayBuilder.Clear();
            displayBuilder.Append(laneName).Append(" // CYBER-RANGE\n");

            if (!isPlayerInside)
            {
                displayBuilder.Append("[STANDBY] ENTER BOOTH TO ENGAGE\n");
                terminalTextMesh.text = displayBuilder.ToString();
                return;
            }

            float currentDist = trolley != null ? trolley.CurrentDistance : 0f;
            float targetDist = trolley != null ? trolley.TargetDistance : 0f;
            bool isMoving = trolley != null && trolley.IsMoving;

            displayBuilder.Append("DIST: ").Append(currentDist.ToString("F1")).Append("m ");
            if (isMoving)
            {
                displayBuilder.Append("[TRANSIT -> ").Append(targetDist.ToString("F1")).Append("m]\n");
            }
            else
            {
                displayBuilder.Append("[STATIONARY]\n");
            }

            int shots = paperTarget != null ? paperTarget.ShotCount : 0;
            int score = paperTarget != null ? paperTarget.TotalScore : 0;
            displayBuilder.Append("HITS: ").Append(shots).Append("  |  SCORE: ").Append(score).Append("\n");

            float spread = paperTarget != null ? paperTarget.ExtremeSpreadCm : 0f;
            float mean = paperTarget != null ? paperTarget.MeanRadiusCm : 0f;
            // 1 MOA at distance D (meters) = D * 0.02908882 cm
            float moa = (currentDist > 0.1f && spread > 0f) ? spread / (currentDist * 0.02908882f) : 0f;
            displayBuilder.Append("SPREAD: ").Append(spread.ToString("F1")).Append("cm (").Append(moa.ToString("F2")).Append(" MOA)  |  MEAN: ").Append(mean.ToString("F1")).Append("cm\n");

            // Render 5x5 ASCII mini-target schematic showing plotted bullet holes
            BuildTargetSchematic();

            displayBuilder.Append("[1-4] DIST  [T] RECALL  [F] FRESH  [R] RESET");

            terminalTextMesh.text = displayBuilder.ToString();
        }

        void BuildTargetSchematic()
        {
            // Initialize default schematic grid: bullseye rings and center crosshair (+)
            schematicGrid[0, 0] = '.'; schematicGrid[0, 1] = '.'; schematicGrid[0, 2] = '|'; schematicGrid[0, 3] = '.'; schematicGrid[0, 4] = '.';
            schematicGrid[1, 0] = '.'; schematicGrid[1, 1] = '('; schematicGrid[1, 2] = '.'; schematicGrid[1, 3] = ')'; schematicGrid[1, 4] = '.';
            schematicGrid[2, 0] = '-'; schematicGrid[2, 1] = '-'; schematicGrid[2, 2] = '+'; schematicGrid[2, 3] = '-'; schematicGrid[2, 4] = '-';
            schematicGrid[3, 0] = '.'; schematicGrid[3, 1] = '('; schematicGrid[3, 2] = '.'; schematicGrid[3, 3] = ')'; schematicGrid[3, 4] = '.';
            schematicGrid[4, 0] = '.'; schematicGrid[4, 1] = '.'; schematicGrid[4, 2] = '|'; schematicGrid[4, 3] = '.'; schematicGrid[4, 4] = '.';

            if (paperTarget != null)
            {
                int count = paperTarget.RecordedShotCount;
                for (int i = 0; i < count; i++)
                {
                    Vector2 hit = paperTarget.GetHitCoordinate(i);
                    // Map hit coordinates from target sheet dimensions (0.55m x 0.85m) to 5x5 cells
                    int gx = Mathf.Clamp(Mathf.RoundToInt((hit.x / 0.55f + 0.5f) * 4f), 0, 4);
                    int gy = Mathf.Clamp(Mathf.RoundToInt((0.5f - hit.y / 0.85f) * 4f), 0, 4);
                    schematicGrid[gy, gx] = (i == count - 1) ? 'X' : '*';
                }
            }

            displayBuilder.Append("TARGET PLOT:\n");
            for (int r = 0; r < 5; r++)
            {
                displayBuilder.Append("  [ ");
                for (int c = 0; c < 5; c++)
                {
                    displayBuilder.Append(schematicGrid[r, c]).Append(' ');
                }
                displayBuilder.Append("]\n");
            }
        }
    }
}
