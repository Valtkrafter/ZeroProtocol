# Versionsnummern und Releases

Zero Protocol zählt Versionen als **MAJOR.MINOR.PATCH** nach *Semantic Versioning 2.0.0* (SemVer), dem Standard bei fast allen
professionellen Projekten. Beispiel: `0.0.2`. Eine Nummer sagt sofort, wie groß die Änderung ist und wie fertig der Stand ist.

```
0.0.2
│ │ └─ PATCH: jede normale Veröffentlichung zählt hier eins hoch (0.0.1 → 0.0.2 → 0.0.3 ...)
│ └─── MINOR: ein größerer Meilenstein ist fertig (z. B. 0.1.0 = alle Bewegungen komplett)
└───── MAJOR: 0 = Alpha-Zeit. 1.0.0 = erste vollständige, spielbare Version
```

**Alle Versionen 0.x.y sind Alpha.** Das steht im Titel des Releases: `ZeroProtocol Alpha 0.0.2`.
Der Git-Tag heißt `v0.0.2`. Im Spiel steht unten rechts `Zero Protocol Alpha 0.0.2`.

Die Datei `VERSION` im Projekt-Hauptordner ist die **einzige Quelle**: Unity (`PlayerSettings.bundleVersion`), `CHANGELOG.md`,
Tag, GitHub-Release und die Anzeige im Spiel werden daraus abgeleitet.

## Wann wird was erhöht?

| Teil | Wann | Beispiel |
|---|---|---|
| PATCH | jedes normale Release in der Alpha: neue Animation, neue Funktion, Fehlerkorrektur | 0.0.2 → 0.0.3 |
| MINOR | ein größerer Meilenstein ist komplett (siehe Vorschlag unten) | 0.0.9 → 0.1.0 |
| MAJOR | erst bei der ersten vollständigen Version, danach bei großen Brüchen (z. B. alte Spielstände gehen nicht mehr) | 0.9.0 → 1.0.0 |

Reihenfolge (kleiner → größer): `0.0.1` < `0.0.2` < ... < `0.0.10` < `0.1.0` < `0.1.1` < ... < `1.0.0`. (Die Zahlen werden einzeln verglichen,
`0.0.10` ist also größer als `0.0.9`.)

Später möglich, wenn wir es brauchen: ein Kanal-Zusatz für Vorabversionen, z. B. `0.5.0-beta.1` (Beta, Funktionen komplett, wird getestet)
oder `0.5.0-rc.1` (Release Candidate, nur noch Fehler beheben). Solche Versionen werden auf GitHub automatisch als **Pre-release** markiert,
normale `0.x.y` nicht (damit das neueste Release auf der Startseite als „Latest“ erscheint).

### Vorschlag für die Meilensteine (die Richtung ist deine Entscheidung)

| Version | Inhalt |
|---|---|
| 0.0.1 | erster Stand: Arena, Gehen, Blinzeln, Federknochen (**ist draußen**) |
| 0.0.2 | Run Update: Sprint, Motion-Blur-Regler, Kamera-Gefühl (**ist draußen**) |
| 0.0.3 | Ausweichen im Gehen |
| 0.0.4 ... | weitere Varianten: Ausweichen aus dem Stand und aus dem Sprint, Richtungen, Jog, Sprung und Landung |
| 0.1.0 | Bewegung komplett |
| 0.2.0 | Zielen und Schießen |
| 0.3.0 | Gegner und KI |
| 0.4.0 | Treffer-Gefühl (Hit-Stop, Effekte, Audio) und UI |
| 0.5.0 | Grafik-Durchgang (Toon-Shader, Licht, Post-Processing) |
| 1.0.0 | erste vollständige, spielbare Version |

## So wird ein Release gemacht

Alles im Projekt-Hauptordner. Vorher müssen alle Änderungen committet sein und unter `## [Unreleased]` im `CHANGELOG.md` stehen.
Der Release-Text steht in `Docs/releases/vX.Y.Z.md`.

```bash
python Tools/release.py show                 # aktuelle Version und was jeder Befehl daraus machen würde
python Tools/release.py patch                # NÄCHSTE ALPHA-NUMMER: 0.0.2 → 0.0.3 (der Normalfall)
python Tools/release.py minor                # Meilenstein: 0.0.3 → 0.1.0
python Tools/release.py set 0.0.5            # genaue Version setzen
python Tools/release.py publish --asset Build/ZeroProtocol-0.0.3-win-x64.zip --name "Dodge Update"   # hochladen, GitHub-Release anlegen
python Tools/release.py selftest             # prüft die Versionsrechnung
```

Zusatz: `--dry-run` zeigt nur, was passieren würde. Der erste Befehl (`patch`, `minor`, `set` ...) schreibt `VERSION`, die Unity-Einstellung
und den `CHANGELOG.md`, committet (`chore(release): vX`) und legt den Tag an. `publish` schiebt Commit und Tag auf GitHub und legt das Release an.

### Was an ein Release gehört

- Titel: `ZeroProtocol Alpha 0.0.3 – Name` (wird aus Version und `--name` gebaut)
- Release-Text: Datei `Docs/releases/vX.Y.Z.md` (sonst der Abschnitt aus dem `CHANGELOG.md`)
- Anhang: `ZeroProtocol-X.Y.Z-win-x64.zip` mit dem **ganzen** Build-Ordner. Die `.exe` allein läuft nicht, sie braucht die Ordner daneben
  (`ZeroProtocol_Data`, `MonoBleedingEdge`, `UnityPlayer.dll`).
- Build in den Ordner `Build/` (steht in `.gitignore`), nie in den Downloads-Ordner.

## Commit-Nachrichten (Conventional Commits)

Format: `typ(bereich): Beschreibung`. Daraus lässt sich später automatisch ein Changelog bauen.

| Typ | Bedeutung |
|---|---|
| `feat` | neue Funktion |
| `fix` | Fehler behoben |
| `perf` | schneller gemacht |
| `refactor` | umgebaut, Verhalten gleich |
| `docs` | nur Dokumentation |
| `test` | Tests und Prüfwerkzeuge |
| `build` | Build, Einstellungen, Werkzeuge |
| `chore` | Aufräumen, Release-Commit (`chore(release): v0.0.3`) |

Bereiche: `player`, `camera`, `animation`, `blender`, `settings`, `dev`, `docs`, `release`.

## Frühere Version

Das erste Release auf GitHub ("ZeroProtocol Alpha 0.0.1", Tag `ZeroProtocol`) ist in dieser Zählung `0.0.1`. Der Tag `v0.0.1` zeigt auf denselben
Commit; das alte Release selbst wurde nicht verändert.
