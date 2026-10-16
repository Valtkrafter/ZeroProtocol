# Changelog

Alle wichtigen Änderungen an Zero Protocol stehen hier. Format nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
Versionsnummern nach [Semantic Versioning](https://semver.org/lang/de/) (Regeln: [Docs/VERSIONING.md](Docs/VERSIONING.md)).
Überschriften: Neu = Added, Geändert = Changed, Behoben = Fixed, Bekannte Probleme = Known issues.

## [Unreleased]

### Neu
- **Sprint** (Shift halten): neuer 60-fps-Laufzyklus mit Flugphase, 5,0 m/s (auf eine 1,8 m große Figur hochgerechnet etwa 6 m/s). In Blender gebaut (`Blender/scripts/build_run.py`), als `Yoru_Run.anim` in Unity gebacken. Beine, Rumpf, Arme, Kopf, Schwanz, Haare, Ohren und Brust bewegen sich mit Fahrtwind mit.
- **Motion-Blur-Regler** (0–100 %, Standard 40 %): Esc öffnet das Panel oben rechts, F10 hält es fest, der Wert wird gespeichert. Globales Post-Processing-Volume `Assets/Settings/ArenaPostFx.asset`.
- **Kamera-Gefühl beim Sprint:** Sichtfeld +6, Abstand +0,35 m, weich überblendet.
- **Versionsverwaltung:** Datei `VERSION`, Regeln in `Docs/VERSIONING.md`, Release-Werkzeug `Tools/release.py`, Versionsanzeige im Spiel (unten rechts), Version wird automatisch in die Unity-Einstellungen übernommen.
- **Prüf-Tests im Play-Modus:** `RunVerifyTest`, `LocomotionQualityTest`, `SprintInputTest`, `MotionBlurCheck`, `RunFilmTest` (Messprotokolle unter `Tools/verify/`, nicht im Repository).
- **Dokumentation:** `Docs/Grafik_Plan.md` (Grafik-Plan und Richtung Third-Person-Shooter).

### Geändert
- Gehen von 1,15 auf 1,5 m/s beschleunigt (Blender und Unity neu gebaut, gleiche Knie- und Beckenbewegung).
- Sprint ist ein festes Tempo (5,0 m/s). Die Neigung des Sticks wirkt nur beim Gehen.
- Animator-Blendtree um den Lauf erweitert (Leerlauf 0, Gehen 1,5, Laufen 5,0 m/s).
- Arena neu gebaut: Post-Processing, getunte Sekundärbewegung für den Sprint.
- Unity hat die URP-Shader-Prefilter-Einstellungen neu geschrieben (wegen Post-Processing).
- Firmenname `Valtkrafter` und Bundle-ID `com.valtkrafter.zeroprotocol` statt der Unity-Vorlage. Gespeicherte Einstellungen des Spiels (z. B. der Motion-Blur-Regler) starten dadurch einmal wieder mit dem Standardwert.

### Behoben
- Build-Einstellungen enthielten nur die leere `SampleScene`: ein gebautes Spiel startete nicht in der Arena. Jetzt ist die Arena die Start-Szene.

### Bekannte Probleme
- Es gibt keinen Jog-Clip: zwischen Gehen (1,5 m/s) und Sprint (5,0 m/s) gibt es kein Dauertempo, kurze Übergänge können die Füße leicht rutschen lassen.
- Keine Luft-Animation (Sprung und Fall haben noch keinen eigenen Clip).
- Der Schwanz schwingt im Spiel höher und tiefer als in Blender (192 mm statt 110 mm Höhenausschlag).
- Die Figur nutzt noch einen Unlit-Shader (kein Licht, keine Schatten, keine Outline), Toon-Shader ist geplant.
- Noch kein Kampf, keine Gegner.

## [0.0.1] - 2026-10-15

Erster Alpha-Stand (auf GitHub als "ZeroProtocol Alpha 0.0.1").

### Neu
- Flache Test-Arena mit Third-Person-Kamera, Lock-On, Sprung und Dash.
- Yoru (VRoid-Modell V2) mit Leerlauf-, Geh- (1,15 m/s) und Blinzel-Animation, in Blender gebaut und per Pose-Streams nach Unity übernommen.
- Haar-, Schwanz-, Ohren- und Brustphysik über Spring Bones.
- Prüf-Tests im Play-Modus für Gehen, Blinzeln und Pose-Vergleich Blender gegen Unity.

[Unreleased]: https://github.com/Valtkrafter/ZeroProtocol/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/Valtkrafter/ZeroProtocol/releases/tag/v0.0.1
