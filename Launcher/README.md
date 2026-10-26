# Zero Protocol Launcher

Stilvoller, leichtgewichtiger Desktop-Launcher für **Zero Protocol**, gebaut mit **Tauri v2** und **Vanilla HTML/CSS/JavaScript**.

## Features (Phase 1)
* **Design:** Rahmenloses Sci-Fi-Fenster (1020x640) mit Glassmorphism, dezenten Partikel-Regeneffekten und Yoru-Visual.
* **Audio-Player:** Eingebauter, prozeduraler Web-Audio-Synthesizer für Beethovens **Mondscheinsonate (1. Satz)** mit animierten Equalizer-Balken.
* **Story & Lore Tab:** Zusammenfassung des *Zero Protocol*, des *Chronos-Sturms* und der *Hollows*.
* **Patchnotes & Status:** Überblick über Alpha-Version v0.0.2.
* **Steuerung:** Tastenbelegung für PC (WASD, Sprint, Dodge, Lock-On).
* **Aktionen:** Direkte Verlinkung zu den GitHub-Releases.

## Starten im Entwicklungsmodus
Im Projekt-Hauptverzeichnis oder im `Launcher/`-Ordner ausführen:

```powershell
cd Launcher
npx tauri dev
```

## Produktions-Build erzeugen (.exe)
Erzeugt eine extrem kleine Standalone-`.exe` (unter 10 MB) im Ordner `src-tauri/target/release/`:

```powershell
cd Launcher
npx tauri build
```
