# Zero Protocol

> Arbeitstitel. Vor einer Veröffentlichung wird ein eigener Titel gewählt, weil es bereits ein Spiel namens "Zero Protocol" (Horror, 2024) gibt.

**Version:** <!-- version -->0.0.2<!-- /version --> · [Releases](https://github.com/Valtkrafter/ZeroProtocol/releases) · [Changelog](CHANGELOG.md) · [Versionsregeln](Docs/VERSIONING.md)

Ein Action-RPG im Stil von *Wuthering Waves*: Echtzeitkampf mit Ausweichen, Perfect Dodge und Konter sowie Charakterwechsel im Kampf. Ziel ist eine offene Welt mit Haupt- und Nebenmissionen.

**Setting:** Eine Stadt der Zukunft nach einer Katastrophe. Taktisch, agentenhaft, sci-fi.

**Protagonistin:** Shirogane Yoru, ein Agentin mit silbern-lila Haar, Katzenohren und -schwanz sowie schwarzem taktischem Outfit.

## Status

Frühe Entwicklung (Alpha). Aktuell gibt es eine flache Test-Arena mit:
- Bewegung: Gehen (1,5 m/s), Sprint (5 m/s), Ausweichen, Sprung und Lock-On-Kamera (Third-Person)
- Animationen für Leerlauf, Gehen, Laufen und Blinzeln (in Blender gebaut und mit Messwerten gegen Unity geprüft)
- Haar-, Schwanz-, Ohren- und Brustphysik über Spring Bones, im Sprint mit Fahrtwind
- Motion-Blur-Regler (Esc öffnet das Einstellungs-Panel)

Geplant ist die Reihenfolge: Kampfkern, Gegner, Fähigkeiten und Ultimate, UI, Charakterwechsel, kleine offene Welt mit Quests, Feinschliff.
Offen ist noch die Richtung des Kampfes (Action-RPG oder Third-Person-Shooter), siehe [Docs/Grafik_Plan.md](Docs/Grafik_Plan.md).

## Spielen

Fertige Alpha-Builds stehen unter [Releases](https://github.com/Valtkrafter/ZeroProtocol/releases) (das Repository ist privat). ZIP herunterladen, **ganz entpacken** und `ZeroProtocol.exe` starten. Die `.exe` allein läuft nicht, sie braucht die Ordner daneben.

| Taste | Aktion |
|---|---|
| WASD | Gehen |
| Shift halten | Sprint |
| Shift tippen | Ausweichen |
| Leertaste | Springen |
| Maus | Kamera |
| Mausrad klicken / drehen | Lock-On / Zoom |
| Esc | Maus freigeben und Einstellungen öffnen (Motion-Blur-Regler), F10 hält das Panel fest |

## Versionen und Releases

Versionsnummern folgen [Semantic Versioning](https://semver.org/lang/de/): jede Alpha-Veröffentlichung zählt die letzte Ziffer hoch (`0.0.1`, `0.0.2`, `0.0.3` ...), alle `0.x.y` sind Alpha, `1.0.0` ist die erste vollständige Version. Die Regeln stehen in [Docs/VERSIONING.md](Docs/VERSIONING.md), die Änderungen im [CHANGELOG](CHANGELOG.md). Ein Release entsteht mit `python Tools/release.py`.

## Technik

- Unity 6 (6000.3.25f1) mit Universal Render Pipeline
- Neues Input System
- Cinemachine 3.1.4
- UniVRM 0.131.3 für das VRM-Modell
- Animationen werden in Blender erstellt und über Pose-Streams nach Unity übernommen

## Projektstruktur

- `Assets/Scenes/Arena.unity`: Test-Arena
- `Assets/Scripts/Player/`: Steuerung, Kamera, Lock-On, Sekundärbewegung
- `Assets/Scripts/Dev/`: Tests im Play-Modus
- `Assets/Editor/`: Editor-Werkzeuge, z. B. Arena-Aufbau und Animator-Builder
- `Blender/`: Skripte und Quelldateien für Animationen
- `Docs/`: Grafik-Plan, Versionsregeln, Release-Texte
- `Tools/`: Hilfsskripte und `release.py` (Versionen und Releases)

## Einrichtung

1. Projekt mit Unity 6000.3.25f1 öffnen.
2. Menü `Zero Protocol > Build Test Arena` ausführen.
3. Den MCP-Server für Unity über `Window > MCP for Unity` starten, falls er für die Werkzeuge gebraucht wird.

## Lizenz

Noch offen. Das Modell der Protagonistin ist derzeit nur für den Autor freigegeben und darf vor einer Veröffentlichung nicht kommerziell genutzt werden.
