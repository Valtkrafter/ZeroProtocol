using UnityEngine;

namespace ZeroProtocol.Combat
{
    /// <summary>
    /// Cyberpunk combat HUD for Zero Protocol.
    /// Event-driven, decoupled from gameplay logic.
    /// Features: Dynamic bloom crosshair, 2-stage hitmarkers (Body/Headshot/Kill),
    /// dual ammo counter, and reload progress display. Zero runtime GC allocations.
    /// </summary>
    public class CombatUI : MonoBehaviour
    {
        public DualPistolCombat combat;

        [Header("Crosshair Settings")]
        public float baseReticleRadius = 14f;
        public float pixelsPerDegree = 16f;
        public float tickLength = 10f;
        public float tickThickness = 2f;
        public float centerDotSize = 3f;

        [Header("Hitmarker Settings")]
        public float hitmarkerDuration = 0.28f;
        public float hitmarkerBaseSize = 10f;
        public float hitmarkerThickness = 2.5f;

        [Header("Cyberpunk Palette")]
        public Color colorNeonCyan = new Color(0.0f, 0.941f, 1.0f, 0.85f);     // #00F0FF
        public Color colorAiming = new Color(0.0f, 1.0f, 0.85f, 0.95f);
        public Color colorIdle = new Color(0.169f, 0.176f, 0.259f, 0.85f);       // #2B2D42
        public Color colorBodyFlash = new Color(0.937f, 0.137f, 0.235f, 1.0f);   // #EF233C
        public Color colorHeadshot = new Color(1.0f, 0.745f, 0.043f, 1.0f);      // #FFBE0B
        public Color colorHover = new Color(1.0f, 0.200f, 0.400f, 1.0f);         // #FF3366
        public Color colorKillMarker = new Color(1.0f, 0.0f, 0.267f, 1.0f);      // #FF0044

        [Header("Lock-On Reticle")]
        public ZeroProtocol.CameraSystem.LockOnSystem lockOn;

        // State variables
        int leftAmmo = 15;
        int rightAmmo = 15;
        int maxAmmo = 15;
        bool isAiming;
        bool isReloading;
        float reloadProgress;
        float reloadTotalDuration = 1.25f;
        float reloadElapsed;
        float currentBloomAngle = 1.0f;
        bool isHoveringTarget;

        float hitmarkerTimer;
        HitType currentHitType;
        bool currentHitIsKill;

        Texture2D whiteTex;
        GUIStyle ammoLabelStyle;
        GUIStyle reloadLabelStyle;
        GUIStyle headerLabelStyle;

        Canvas uiCanvas;
        RectTransform lockReticleRect;
        CanvasGroup lockReticleCanvasGroup;
        Vector2 smoothedScreenPos;
        float lockAcquireTimer;
        ZeroProtocol.CameraSystem.LockOnTarget currentLockTarget;

        // Pre-allocated string lookup table for Zero GC
        static readonly string[] NumberStrings = new string[101];
        static readonly string[] SlashNumberStrings = new string[101];

        static CombatUI()
        {
            for (int i = 0; i <= 100; i++)
            {
                NumberStrings[i] = i.ToString();
                SlashNumberStrings[i] = "/" + i.ToString();
            }
        }

        string SafeSlashNumber(int val)
        {
            if (val >= 0 && val < SlashNumberStrings.Length) return SlashNumberStrings[val];
            return "/" + val.ToString();
        }

        void Awake()
        {
            if (combat == null) combat = GetComponentInParent<DualPistolCombat>();
            if (combat == null) combat = FindFirstObjectByType<DualPistolCombat>();
            if (lockOn == null) lockOn = FindFirstObjectByType<ZeroProtocol.CameraSystem.LockOnSystem>();

            whiteTex = new Texture2D(1, 1, TextureFormat.RGBA32, false);
            whiteTex.SetPixel(0, 0, Color.white);
            whiteTex.Apply();

            EnsureCanvasReticle();
        }

        void OnEnable()
        {
            if (combat == null)
            {
                combat = GetComponentInParent<DualPistolCombat>();
                if (combat == null) combat = FindFirstObjectByType<DualPistolCombat>();
            }

            if (combat != null)
            {
                combat.OnAmmoChanged -= HandleAmmoChanged;
                combat.OnAmmoChanged += HandleAmmoChanged;
                combat.OnReloadStarted -= HandleReloadStarted;
                combat.OnReloadStarted += HandleReloadStarted;
                combat.OnReloadCompleted -= HandleReloadCompleted;
                combat.OnReloadCompleted += HandleReloadCompleted;
                combat.OnAimStateChanged -= HandleAimStateChanged;
                combat.OnAimStateChanged += HandleAimStateChanged;
                combat.OnHitFeedback -= HandleHitFeedback;
                combat.OnHitFeedback += HandleHitFeedback;
                combat.OnBloomChanged -= HandleBloomChanged;
                combat.OnBloomChanged += HandleBloomChanged;
            }

            if (lockOn == null)
            {
                lockOn = FindFirstObjectByType<ZeroProtocol.CameraSystem.LockOnSystem>();
            }
            if (lockOn != null)
            {
                lockOn.OnLockTargetChanged -= HandleLockTargetChanged;
                lockOn.OnLockTargetChanged += HandleLockTargetChanged;
            }
        }

        void OnDisable()
        {
            if (combat != null)
            {
                combat.OnAmmoChanged -= HandleAmmoChanged;
                combat.OnReloadStarted -= HandleReloadStarted;
                combat.OnReloadCompleted -= HandleReloadCompleted;
                combat.OnAimStateChanged -= HandleAimStateChanged;
                combat.OnHitFeedback -= HandleHitFeedback;
                combat.OnBloomChanged -= HandleBloomChanged;
            }

            if (lockOn != null)
            {
                lockOn.OnLockTargetChanged -= HandleLockTargetChanged;
            }
        }

        void OnDestroy()
        {
            if (combat != null)
            {
                combat.OnAmmoChanged -= HandleAmmoChanged;
                combat.OnReloadStarted -= HandleReloadStarted;
                combat.OnReloadCompleted -= HandleReloadCompleted;
                combat.OnAimStateChanged -= HandleAimStateChanged;
                combat.OnHitFeedback -= HandleHitFeedback;
                combat.OnBloomChanged -= HandleBloomChanged;
            }

            if (lockOn != null)
            {
                lockOn.OnLockTargetChanged -= HandleLockTargetChanged;
            }

            if (whiteTex != null)
            {
                Destroy(whiteTex);
            }

            if (uiCanvas != null)
            {
                Destroy(uiCanvas.gameObject);
            }
        }

        void Update()
        {
            float dt = Time.deltaTime;
            if (dt <= 0f) return;

            if (hitmarkerTimer > 0f)
            {
                hitmarkerTimer -= dt;
            }

            if (lockAcquireTimer > 0f)
            {
                lockAcquireTimer -= dt;
            }

            if (isReloading)
            {
                reloadElapsed += dt;
                reloadProgress = Mathf.Clamp01(reloadElapsed / Mathf.Max(0.01f, reloadTotalDuration));
            }

            // Update modern Lock-On Canvas reticle
            UpdateLockReticle(dt);

            // Check if center screen is hovering over a target
            CheckReticleHover();
        }

        readonly RaycastHit[] hoverRayHits = new RaycastHit[8];

        void CheckReticleHover()
        {
            isHoveringTarget = false;
            Camera cam = combat != null && combat.mainCamera != null ? combat.mainCamera : Camera.main;
            if (cam == null) return;

            Ray ray = cam.ViewportPointToRay(new Vector3(0.5f, 0.5f, 0f));
            var targets = ShootingTarget.ActiveTargets;
            if (targets == null || targets.Count == 0) return;

            // Find distance to closest environmental obstacle along center ray
            int rayHitCount = Physics.RaycastNonAlloc(ray, hoverRayHits, 150f, ~0, QueryTriggerInteraction.Ignore);
            float nearestObstacleDist = float.MaxValue;
            Transform playerT = combat != null ? combat.transform : null;

            for (int i = 0; i < rayHitCount; i++)
            {
                RaycastHit h = hoverRayHits[i];
                if (h.collider == null) continue;
                if (playerT != null && h.transform.IsChildOf(playerT)) continue;
                if (h.collider.GetComponentInParent<ShootingTarget>() == null && h.distance < nearestObstacleDist)
                {
                    nearestObstacleDist = h.distance;
                }
            }

            float maxHeadAngle = isAiming ? 2.0f : 1.2f;
            float maxBodyAngle = isAiming ? 3.8f : 2.5f;

            for (int i = 0; i < targets.Count; i++)
            {
                ShootingTarget t = targets[i];
                if (t == null || !t.IsAlive) continue;

                Vector3 toHead = t.HeadPosition - ray.origin;
                float distHead = toHead.magnitude;
                if (distHead < nearestObstacleDist && Vector3.Dot(ray.direction, toHead) > 0f)
                {
                    float angle = Vector3.Angle(ray.direction, toHead / Mathf.Max(0.01f, distHead));
                    if (angle <= maxHeadAngle)
                    {
                        isHoveringTarget = true;
                        t.SetHovered(true);
                        break;
                    }
                }

                Vector3 toBody = t.BodyPosition - ray.origin;
                float distBody = toBody.magnitude;
                if (distBody < nearestObstacleDist && Vector3.Dot(ray.direction, toBody) > 0f)
                {
                    float angle = Vector3.Angle(ray.direction, toBody / Mathf.Max(0.01f, distBody));
                    if (angle <= maxBodyAngle)
                    {
                        isHoveringTarget = true;
                        t.SetHovered(true);
                        break;
                    }
                }
            }
        }

        void OnGUI()
        {
            EnsureStyles();

            float cx = Screen.width * 0.5f;
            float cy = Screen.height * 0.5f;

            // 1. Draw Bloom Crosshair
            DrawCrosshair(cx, cy);

            // 2. Draw 2-Stage Hitmarkers
            if (hitmarkerTimer > 0f)
            {
                DrawHitmarker(cx, cy);
            }

            // 3. Draw Dual Ammo Counter & Cyberpunk HUD
            DrawDualAmmoHUD();
        }

        void DrawCrosshair(float cx, float cy)
        {
            float bloomRadius = baseReticleRadius + (currentBloomAngle * pixelsPerDegree);
            Color reticleColor = isHoveringTarget ? colorHover : (isAiming ? colorAiming : colorNeonCyan);

            // Center Dot
            DrawRect(cx - centerDotSize * 0.5f, cy - centerDotSize * 0.5f, centerDotSize, centerDotSize, reticleColor);

            // 4 dynamic bloom brackets
            // Top
            DrawRect(cx - tickThickness * 0.5f, cy - bloomRadius - tickLength, tickThickness, tickLength, reticleColor);
            // Bottom
            DrawRect(cx - tickThickness * 0.5f, cy + bloomRadius, tickThickness, tickLength, reticleColor);
            // Left
            DrawRect(cx - bloomRadius - tickLength, cy - tickThickness * 0.5f, tickLength, tickThickness, reticleColor);
            // Right
            DrawRect(cx + bloomRadius, cy - tickThickness * 0.5f, tickLength, tickThickness, reticleColor);

            // ADS framing pips
            if (isAiming)
            {
                float pipDist = bloomRadius + tickLength + 4f;
                DrawRect(cx - pipDist - 4f, cy - 1f, 3f, 2f, colorAiming);
                DrawRect(cx + pipDist + 1f, cy - 1f, 3f, 2f, colorAiming);
            }
        }

        void DrawHitmarker(float cx, float cy)
        {
            float t = Mathf.Clamp01(hitmarkerTimer / hitmarkerDuration);
            // Dynamic scale pulse on impact
            float scale = Mathf.Lerp(1.4f, 1.0f, 1f - t);
            float d = (hitmarkerBaseSize * 0.7f) * scale;
            float len = (hitmarkerBaseSize * 0.9f) * scale;

            Color hitColor;
            if (currentHitIsKill)
            {
                hitColor = colorKillMarker;
            }
            else if (currentHitType == HitType.Headshot)
            {
                hitColor = colorHeadshot;
            }
            else
            {
                hitColor = colorBodyFlash;
            }

            hitColor.a = t;

            // Diagonal ticks (X shape)
            DrawLine(new Vector2(cx - d, cy - d), new Vector2(cx - d - len, cy - d - len), hitColor, hitmarkerThickness);
            DrawLine(new Vector2(cx + d, cy - d), new Vector2(cx + d + len, cy - d - len), hitColor, hitmarkerThickness);
            DrawLine(new Vector2(cx - d, cy + d), new Vector2(cx - d - len, cy + d + len), hitColor, hitmarkerThickness);
            DrawLine(new Vector2(cx + d, cy + d), new Vector2(cx + d + len, cy + d + len), hitColor, hitmarkerThickness);

            // Stage 2: Headshot / Kill extra spikes
            if (currentHitType == HitType.Headshot || currentHitIsKill)
            {
                float outerDist = d + len + 3f;
                DrawLine(new Vector2(cx - outerDist, cy), new Vector2(cx - outerDist - 5f, cy), hitColor, hitmarkerThickness + 0.5f);
                DrawLine(new Vector2(cx + outerDist, cy), new Vector2(cx + outerDist + 5f, cy), hitColor, hitmarkerThickness + 0.5f);
                DrawLine(new Vector2(cx, cy - outerDist), new Vector2(cx, cy - outerDist - 5f), hitColor, hitmarkerThickness + 0.5f);
                DrawLine(new Vector2(cx, cy + outerDist), new Vector2(cx, cy + outerDist + 5f), hitColor, hitmarkerThickness + 0.5f);
            }
        }

        void DrawDualAmmoHUD()
        {
            float panelWidth = 230f;
            float panelHeight = 84f;
            float px = Screen.width - panelWidth - 24f;
            float py = Screen.height - panelHeight - 24f;

            // Background panel
            DrawRect(px, py, panelWidth, panelHeight, new Color(0.08f, 0.10f, 0.14f, 0.75f));
            // Cyberpunk border frame
            DrawRect(px, py, panelWidth, 2f, colorNeonCyan);
            DrawRect(px, py + panelHeight - 2f, panelWidth, 2f, colorNeonCyan);
            DrawRect(px, py, 2f, panelHeight, colorNeonCyan);
            DrawRect(px + panelWidth - 2f, py, 2f, panelHeight, colorNeonCyan);

            // Header title
            GUI.Label(new Rect(px + 12f, py + 6f, 150f, 18f), "DUAL GUN-FU PROTOCOL", headerLabelStyle);

            if (isReloading)
            {
                // Reload progress bar
                GUI.Label(new Rect(px + 12f, py + 26f, 200f, 22f), "RELOADING...", reloadLabelStyle);
                float barWidth = panelWidth - 24f;
                DrawRect(px + 12f, py + 52f, barWidth, 14f, new Color(0.2f, 0.2f, 0.25f, 0.8f));
                DrawRect(px + 12f, py + 52f, barWidth * reloadProgress, 14f, colorHeadshot);
                return;
            }

            // Left Mag Bar & Number
            string leftStr = SafeNumber(leftAmmo);
            string rightStr = SafeNumber(rightAmmo);
            string maxStr = SafeNumber(maxAmmo);

            Color leftColor = leftAmmo <= 3 ? colorBodyFlash : colorNeonCyan;
            Color rightColor = rightAmmo <= 3 ? colorBodyFlash : colorNeonCyan;

            // Left
            GUI.Label(new Rect(px + 12f, py + 26f, 50f, 20f), "L-MAG", headerLabelStyle);
            DrawAmmoSegments(px + 60f, py + 30f, 75f, 12f, leftAmmo, maxAmmo, leftColor);
            ammoLabelStyle.normal.textColor = leftColor;
            GUI.Label(new Rect(px + 145f, py + 25f, 30f, 22f), leftStr, ammoLabelStyle);

            // Right
            GUI.Label(new Rect(px + 12f, py + 52f, 50f, 20f), "R-MAG", headerLabelStyle);
            DrawAmmoSegments(px + 60f, py + 56f, 75f, 12f, rightAmmo, maxAmmo, rightColor);
            ammoLabelStyle.normal.textColor = rightColor;
            GUI.Label(new Rect(px + 145f, py + 51f, 30f, 22f), rightStr, ammoLabelStyle);

            // Max Ammo Divider
            ammoLabelStyle.normal.textColor = new Color(1f, 1f, 1f, 0.45f);
            GUI.Label(new Rect(px + 175f, py + 38f, 40f, 22f), SafeSlashNumber(maxAmmo), ammoLabelStyle);
        }

        void DrawAmmoSegments(float x, float y, float width, float height, int current, int max, Color col)
        {
            DrawRect(x, y, width, height, new Color(0.15f, 0.17f, 0.22f, 0.8f));
            if (max <= 0) return;
            float segWidth = (width - (max - 1) * 1.5f) / max;
            for (int i = 0; i < current; i++)
            {
                float segX = x + i * (segWidth + 1.5f);
                DrawRect(segX, y, segWidth, height, col);
            }
        }

        void DrawRect(float x, float y, float w, float h, Color col)
        {
            Color old = GUI.color;
            GUI.color = col;
            GUI.DrawTexture(new Rect(x, y, w, h), whiteTex);
            GUI.color = old;
        }

        void DrawLine(Vector2 p1, Vector2 p2, Color col, float width)
        {
            Color oldCol = GUI.color;
            GUI.color = col;
            Vector2 d = p2 - p1;
            float angle = Mathf.Atan2(d.y, d.x) * Mathf.Rad2Deg;
            Matrix4x4 oldMat = GUI.matrix;
            GUIUtility.RotateAroundPivot(angle, p1);
            GUI.DrawTexture(new Rect(p1.x, p1.y - width * 0.5f, d.magnitude, width), whiteTex);
            GUI.matrix = oldMat;
            GUI.color = oldCol;
        }

        string SafeNumber(int val)
        {
            if (val >= 0 && val < NumberStrings.Length) return NumberStrings[val];
            return val.ToString();
        }

        void EnsureStyles()
        {
            if (ammoLabelStyle == null)
            {
                ammoLabelStyle = new GUIStyle(GUI.skin.label)
                {
                    fontSize = 15,
                    fontStyle = FontStyle.Bold,
                    alignment = TextAnchor.MiddleCenter
                };
            }

            if (reloadLabelStyle == null)
            {
                reloadLabelStyle = new GUIStyle(GUI.skin.label)
                {
                    fontSize = 14,
                    fontStyle = FontStyle.Bold,
                    alignment = TextAnchor.MiddleLeft
                };
                reloadLabelStyle.normal.textColor = colorHeadshot;
            }

            if (headerLabelStyle == null)
            {
                headerLabelStyle = new GUIStyle(GUI.skin.label)
                {
                    fontSize = 10,
                    fontStyle = FontStyle.Bold,
                    alignment = TextAnchor.MiddleLeft
                };
                headerLabelStyle.normal.textColor = new Color(0.7f, 0.85f, 0.95f, 0.7f);
            }
        }

        void HandleAmmoChanged(int left, int right, int max)
        {
            leftAmmo = left;
            rightAmmo = right;
            maxAmmo = max;
        }

        void HandleReloadStarted(float duration)
        {
            isReloading = true;
            reloadTotalDuration = duration;
            reloadElapsed = 0f;
            reloadProgress = 0f;
        }

        void HandleReloadCompleted()
        {
            isReloading = false;
            reloadProgress = 1f;
        }

        void HandleAimStateChanged(bool aiming)
        {
            isAiming = aiming;
        }

        void HandleHitFeedback(HitFeedbackData feedback)
        {
            hitmarkerTimer = hitmarkerDuration;
            currentHitType = feedback.HitType;
            currentHitIsKill = feedback.IsKill;
        }

        void HandleBloomChanged(float bloom)
        {
            currentBloomAngle = bloom;
        }

        void HandleLockTargetChanged(ZeroProtocol.CameraSystem.LockOnTarget target)
        {
            if (target != null && target != currentLockTarget)
            {
                lockAcquireTimer = 0.30f;
            }
            currentLockTarget = target;
        }

        void EnsureCanvasReticle()
        {
            if (uiCanvas != null) return;

            var existingCanvas = GameObject.Find("CombatCanvas");
            GameObject canvasGo = existingCanvas != null ? existingCanvas : new GameObject("CombatCanvas");
            uiCanvas = canvasGo.GetComponent<Canvas>();
            if (uiCanvas == null)
            {
                uiCanvas = canvasGo.AddComponent<Canvas>();
                uiCanvas.renderMode = RenderMode.ScreenSpaceOverlay;
                uiCanvas.sortingOrder = 50;
            }

            var scaler = canvasGo.GetComponent<UnityEngine.UI.CanvasScaler>();
            if (scaler == null)
            {
                scaler = canvasGo.AddComponent<UnityEngine.UI.CanvasScaler>();
                scaler.uiScaleMode = UnityEngine.UI.CanvasScaler.ScaleMode.ScaleWithScreenSize;
                scaler.referenceResolution = new Vector2(1920, 1080);
                scaler.matchWidthOrHeight = 0.5f;
            }

            var raycaster = canvasGo.GetComponent<UnityEngine.UI.GraphicRaycaster>();
            if (raycaster == null)
            {
                canvasGo.AddComponent<UnityEngine.UI.GraphicRaycaster>();
            }

            // Create Lock Reticle Root
            Transform existingReticle = canvasGo.transform.Find("LockReticle");
            GameObject reticleGo = existingReticle != null ? existingReticle.gameObject : new GameObject("LockReticle");
            reticleGo.transform.SetParent(canvasGo.transform, false);
            lockReticleRect = reticleGo.GetComponent<RectTransform>();
            if (lockReticleRect == null) lockReticleRect = reticleGo.AddComponent<RectTransform>();
            lockReticleRect.sizeDelta = new Vector2(64, 64);

            lockReticleCanvasGroup = reticleGo.GetComponent<CanvasGroup>();
            if (lockReticleCanvasGroup == null) lockReticleCanvasGroup = reticleGo.AddComponent<CanvasGroup>();
            lockReticleCanvasGroup.alpha = 0f;

            if (reticleGo.transform.childCount == 0)
            {
                // Create 4 corner brackets
                CreateReticleBracket(reticleGo.transform, "Bracket_TL", new Vector2(-22, 22), 0f);
                CreateReticleBracket(reticleGo.transform, "Bracket_TR", new Vector2(22, 22), 90f);
                CreateReticleBracket(reticleGo.transform, "Bracket_BR", new Vector2(22, -22), 180f);
                CreateReticleBracket(reticleGo.transform, "Bracket_BL", new Vector2(-22, -22), 270f);

                // Create center diamond pip
                var pipGo = new GameObject("DiamondPip");
                pipGo.transform.SetParent(reticleGo.transform, false);
                var pipRect = pipGo.AddComponent<RectTransform>();
                pipRect.sizeDelta = new Vector2(8, 8);
                pipRect.localEulerAngles = new Vector3(0, 0, 45f);
                var pipImg = pipGo.AddComponent<UnityEngine.UI.Image>();
                pipImg.color = colorNeonCyan;
            }
        }

        void CreateReticleBracket(Transform parent, string name, Vector2 pos, float rotZ)
        {
            var bGo = new GameObject(name);
            bGo.transform.SetParent(parent, false);
            var bRect = bGo.AddComponent<RectTransform>();
            bRect.anchoredPosition = pos;
            bRect.sizeDelta = new Vector2(16, 16);
            bRect.localEulerAngles = new Vector3(0, 0, rotZ);

            var hBar = new GameObject("HBar");
            hBar.transform.SetParent(bGo.transform, false);
            var hRect = hBar.AddComponent<RectTransform>();
            hRect.anchorMin = new Vector2(0, 1);
            hRect.anchorMax = new Vector2(0, 1);
            hRect.pivot = new Vector2(0, 1);
            hRect.sizeDelta = new Vector2(12, 2.5f);
            var hImg = hBar.AddComponent<UnityEngine.UI.Image>();
            hImg.color = colorNeonCyan;

            var vBar = new GameObject("VBar");
            vBar.transform.SetParent(bGo.transform, false);
            var vRect = vBar.AddComponent<RectTransform>();
            vRect.anchorMin = new Vector2(0, 1);
            vRect.anchorMax = new Vector2(0, 1);
            vRect.pivot = new Vector2(0, 1);
            vRect.sizeDelta = new Vector2(2.5f, 12);
            var vImg = vBar.AddComponent<UnityEngine.UI.Image>();
            vImg.color = colorNeonCyan;
        }

        void UpdateLockReticle(float dt)
        {
            if (lockOn == null)
            {
                lockOn = FindFirstObjectByType<ZeroProtocol.CameraSystem.LockOnSystem>();
            }

            bool isLocked = lockOn != null && lockOn.Current != null;
            if (isLocked)
            {
                currentLockTarget = lockOn.Current;
                if (lockReticleCanvasGroup != null)
                {
                    lockReticleCanvasGroup.alpha = Mathf.MoveTowards(lockReticleCanvasGroup.alpha, 1f, dt * 10f);
                }

                Camera cam = combat != null && combat.mainCamera != null ? combat.mainCamera : Camera.main;
                if (cam != null && currentLockTarget != null)
                {
                    Vector3 sp = cam.WorldToScreenPoint(currentLockTarget.AimPoint);
                    if (sp.z > 0f)
                    {
                        Vector2 targetPos = new Vector2(sp.x, sp.y);
                        if (smoothedScreenPos == Vector2.zero) smoothedScreenPos = targetPos;
                        smoothedScreenPos = Vector2.Lerp(smoothedScreenPos, targetPos, 1f - Mathf.Exp(-24f * dt));

                        if (lockReticleRect != null)
                        {
                            lockReticleRect.position = smoothedScreenPos;
                            float pulse = lockAcquireTimer > 0f ? Mathf.Lerp(1.6f, 1.0f, 1f - (lockAcquireTimer / 0.30f)) : 1.0f;
                            float breathing = 1.0f + 0.04f * Mathf.Sin(Time.time * 6f);
                            float finalScale = pulse * breathing;
                            lockReticleRect.localScale = new Vector3(finalScale, finalScale, 1f);
                            lockReticleRect.localEulerAngles = new Vector3(0, 0, Mathf.Sin(Time.time * 2f) * 4f);
                        }
                    }
                    else if (lockReticleCanvasGroup != null)
                    {
                        lockReticleCanvasGroup.alpha = 0f;
                    }
                }
            }
            else
            {
                currentLockTarget = null;
                smoothedScreenPos = Vector2.zero;
                if (lockReticleCanvasGroup != null)
                {
                    lockReticleCanvasGroup.alpha = Mathf.MoveTowards(lockReticleCanvasGroup.alpha, 0f, dt * 12f);
                }
            }
        }
    }
}
