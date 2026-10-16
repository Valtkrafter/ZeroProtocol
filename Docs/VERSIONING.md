# Versionsnummern und Releases

Zero Protocol nutzt **Semantic Versioning 2.0.0** (SemVer), so wie es große Firmen und fast alle professionellen Projekte tun.
Eine Nummer sagt dadurch sofort, wie groß die Änderung ist und wie fertig der Stand ist.

```
0.1.0-alpha.1
│ │ │  │     └─ Zähler im Kanal (1. Alpha dieser Version)
│ │ │  └─────── Kanal: alpha → beta → rc (ohne Kanal = fertig)
│ │ └────────── PATCH: nur Fehler behoben
│ └──────────── MINOR: ein neues Funktions-Paket ist fertig
└────────────── MAJOR: 0 bis zur ersten vollständigen Version (1.0.0)
```

Git-Tag und GitHub-Release heißen `v0.1.0-alpha.1`. Die Datei `VERSION` im Projekt-Hauptordner ist die **einzige Quelle**:
Unity (`PlayerSettings.bundleVersion`, im Spiel unten rechts sichtbar), `CHANGELOG.md`, Tag und Release werden daraus abgeleitet.

## Wann wird was erhöht?

| Teil | Wann | Beispiel |
|---|---|---|
| MAJOR | erst ab 1.0.0: großer Bruch (z. B. alte Spielstände gehen nicht mehr). Bis zur 1.0.0 bleibt es 0. | 1.0.0 → 2.0.0 |
| MINOR | ein neues Spiel-Paket ist fertig (Bewegung, Zielen und Schießen, Gegner, UI ...) | 0.1.0 → 0.2.0 |
| PATCH | nur Fehler und Feinschliff, nichts Neues | 0.1.0 → 0.1.1 |
| Kanal | wie fertig ist der Stand: **alpha** = roh, intern, vieles fehlt; **beta** = Paket komplett, wird getestet; **rc** = Release Candidate, nur noch Fehler beheben | 0.2.0-beta.1 |

Reihenfolge (kleiner → größer): `0.1.0-alpha.1` < `0.1.0-alpha.2` < `0.1.0-beta.1` < `0.1.0-rc.1` < `0.1.0` < `0.1.1` < `0.2.0-alpha.1` < ... < `1.0.0`.

### Vorschlag für die Meilensteine (Richtung ist deine Entscheidung)

| Version | Inhalt |
|---|---|
| 0.1 | Bewegung: Gehen, Sprint, Ausweichen, Kamera, Motion Blur (**alpha.1 ist draußen**) |
| 0.2 | Zielen und Schießen (Animationen, Schulterkamera, Waffen) |
| 0.3 | Gegner und KI |
| 0.4 | Treffer-Gefühl (Hit-Stop, Effekte, Audio) und UI |
| 0.5 | Grafik-Durchgang (Toon-Shader, Licht, Post-Processing) |
| 1.0 | erste vollständige, spielbare Demo |

## So wird ein Release gemacht

Alles in einem Befehl im Projekt-Hauptordner. Vorher müssen alle Änderungen committet sein und unter `## [Unreleased]` im
`CHANGELOG.md` stehen.

```bash
python Tools/release.py alpha      # 0.1.0-alpha.1 → 0.1.0-alpha.2   (von einer fertigen Version: nächste MINOR als alpha.1)
python Tools/release.py beta       # alpha → beta.1 derselben Version
python Tools/release.py rc         # beta → rc.1
python Tools/release.py release    # 0.1.0-rc.2 → 0.1.0 (Kanal entfällt)
python Tools/release.py patch      # nur von einer fertigen Version: 0.1.0 → 0.1.1
python Tools/release.py minor      # 0.1.0 → 0.2.0
python Tools/release.py set 0.3.0-alpha.1    # genaue Version setzen
python Tools/release.py publish --asset Build/ZeroProtocol-0.1.0-alpha.1-win-x64.zip   # hochladen und GitHub-Release anlegen
python Tools/release.py selftest   # prüft die Versionsrechnung
```

Zusatz: `--dry-run` zeigt nur, was passieren würde. Der erste Befehl (alpha, beta, ...) schreibt `VERSION`, die Unity-Einstellung
und den `CHANGELOG.md`, committet (`chore(release): vX`) und legt den Tag an. `publish` schiebt Commit und Tag auf GitHub und
legt das Release an (bei alpha, beta und rc automatisch als **Pre-release**).

### Was an ein Release gehört

- Titel: `ZeroProtocol vX – Name` (z. B. `ZeroProtocol v0.1.0-alpha.1 – Run Update`)
- Release-Text: Datei `Docs/releases/vX.md` (sonst der Abschnitt aus dem `CHANGELOG.md`)
- Anhang: `ZeroProtocol-X-win-x64.zip` mit dem **ganzen** Build-Ordner. Die `.exe` allein läuft nicht, sie braucht die Ordner daneben
  (`ZeroProtocol_Data`, `MonoBleedingEdge`, `UnityPlayer.dll`).
- Build in den Ordner `Build/` (steht in `.gitignore`), nie in den Downloads-Ordner.

## Commit-Nachrichten (Conventional Commits)

Format: `typ(bereich): Beschreibung`. Daraus lässt sich später automatisch ein Changelog bauen.

| Typ | Bedeutung |
|---|---|
| `feat` | neue Funktion (erhöht beim Release MINOR) |
| `fix` | Fehler behoben (PATCH) |
| `perf` | schneller gemacht |
| `refactor` | umgebaut, Verhalten gleich |
| `docs` | nur Dokumentation |
| `test` | Tests und Prüfwerkzeuge |
| `build` | Build, Einstellungen, Werkzeuge |
| `chore` | Aufräumen, Release-Commit (`chore(release): v0.1.0-alpha.1`) |

Bereiche: `player`, `camera`, `animation`, `blender`, `settings`, `dev`, `docs`, `release`.

## Frühere Version

Das erste Release auf GitHub ("ZeroProtocol Alpha 0.0.1", Tag `ZeroProtocol`) entspricht in dieser Zählung `v0.0.1-alpha.1`.
Der Tag `v0.0.1-alpha.1` zeigt auf denselben Commit; das alte Release wurde nicht verändert.
