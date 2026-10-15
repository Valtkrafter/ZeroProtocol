# Zero Protocol

> Arbeitstitel. Vor einer Veröffentlichung wird ein eigener Titel gewählt, weil es bereits ein Spiel namens "Zero Protocol" (Horror, 2024) gibt.

Ein Action-RPG im Stil von *Wuthering Waves*: Echtzeitkampf mit Ausweichen, Perfect Dodge und Konter sowie Charakterwechsel im Kampf. Ziel ist eine offene Welt mit Haupt- und Nebenmissionen.

**Setting:** Eine Stadt der Zukunft nach einer Katastrophe. Taktisch, agentenhaft, sci-fi.

**Protagonistin:** Shirogane Yoru, ein Agentin mit silbern-lila Haar, Katzenohren und -schwanz sowie schwarzem taktischem Outfit.

## Status

Frühe Entwicklung. Aktuell gibt es eine flache Test-Arena mit:
- Bewegung, Sprung, Dash und Lock-On-Kamera (Third-Person)
- Animation im Leerlauf
- Haar-, Schwanz- und Ohrphysik über Spring Bones

Geplant ist die Reihenfolge: Gehen und Laufen, Kampfkern, Gegner, Fähigkeiten und Ultimate, UI, Charakterwechsel, kleine offene Welt mit Quests, Feinschliff.

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
- `Tools/`: Hilfsskripte

## Einrichtung

1. Projekt mit Unity 6000.3.25f1 öffnen.
2. Menü `Zero Protocol > Build Test Arena` ausführen.
3. Den MCP-Server für Unity über `Window > MCP for Unity` starten, falls er für die Werkzeuge gebraucht wird.

## Lizenz

Noch offen. Das Modell der Protagonistin ist derzeit nur für den Autor freigegeben und darf vor einer Veröffentlichung nicht kommerziell genutzt werden.
