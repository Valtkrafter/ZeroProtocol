# Zero Protocol – Grafik-Plan und Richtung (Stand 2026-10-16)

Dieser Plan ist zum **späteren** Anschrauben der Grafik gedacht. Nichts davon ist umgesetzt, außer dem Motion-Blur-Regler.
Reihenfolge = Wirkung pro Aufwand. Jede Stufe ist einzeln machbar und einzeln testbar.

## 0. Wo wir heute stehen (gemessen, nicht geschätzt)

| Punkt | Ist-Zustand |
|---|---|
| Pipeline | Unity 6000.3, URP 17.3, Render Graph an, HDR an, MSAA aus, Kamera-Antialiasing aus |
| Schatten | Hauptlicht 2048, 4 Kaskaden, 50 m, weiche Schatten Stufe 3 |
| Post Processing | nur ein globales Volume `PostProcessing` mit **Motion Blur** (Regler im Spiel) |
| Yoru-Material | **alle 20 Materialien benutzen `UniUnlit`** = nur Textur, **kein Licht, keine Schatten auf ihr, keine Outline**. Der MToon-Shader liegt im Paket, wird aber nicht benutzt. Das ist der größte Hebel für den Look. |
| Welt | graue Testarena mit Raster und Kisten (`Zero Protocol/Build Test Arena`) |
| Tempo | Editor ca. 73 Bilder/s im Leerlauf bei 1482 x 829 mit allen Schatten und Motion Blur (Hoch). Die Verifikationstests laufen mit 13–14 Bildern/s, weil sie dabei Bilder aufnehmen. |
| Feder-Knochen | 26 Komponenten (ca. 74 Haarknochen + Schwanz + Brust + Ohren): **1,2 ms pro 1/60 s** im Editor (Mono). Im fertigen Spiel (IL2CPP) vermutlich ein Drittel bis ein Viertel davon. Für viele NPCs später nötig: weniger Knochen pro Gegner oder schnelle Variante (Burst/Jobs). |

## 1. Charakter-Look (G1) – größter Effekt, etwa ein halber Tag

Ziel: Yoru sieht aus wie ein hochwertiger Anime-Charakter statt wie ein flaches Textur-Blatt.

1. **Toon-Shader statt Unlit.** Zwei Wege, ich empfehle Weg A:
   - A) **lilToon** (frei; vor dem Einbau prüfe ich, ob die aktuelle Version mit URP 17 / Unity 6 läuft): Schatten-Rampe (2-stufig, weiche Kante), Rim-Light, Haar-Glanzband (Anisotropie), Outline, Matcap. Sehr viele Regler, gute Werkzeuge.
   - B) **MToon** aus dem VRM-Paket (liegt schon im Projekt): weniger Regler, Outline und Schatten-Rampe vorhanden, aber unter URP umständlicher.
   - Umsetzung: ein Menü-Befehl `Zero Protocol/Rebuild Yoru Materials`, der die 20 Materialien umstellt (Texturen bleiben, nur der Shader wechselt). Rückgängig machbar, weil die alten Materialien archiviert werden.
2. **Outline** (dünn, 1,5–2 px, dunkel statt schwarz, an Gesicht dünner als am Körper) – entweder im Shader oder als Render-Feature.
3. **Haare:** Glanzband, das mit der Kamera wandert; leichter Rim-Light in Lichtfarbe.
4. **Gesicht:** Schatten im Gesicht etwas aufgehellt (kein harter Nasenschatten), Augen heller als der Rest (Augen-Highlight leuchtet leicht).
5. **Waffen/Ausrüstung:** später PBR (Metall, Matt-Schwarz) neben dem Toon-Körper, damit die Ausrüstung „hart“ wirkt.

## 2. Licht und Welt (G2) – etwa ein halber Tag

1. **Licht-Rig:** Hauptlicht (warm, tief, weiche Schatten), Gegenlicht (kühl) für Rim, Himmelslicht aus einem eigenen Skybox/HDRI.
2. **Adaptive Probe Volumes** (statt Light Probes) und **Reflexions-Probes** für Böden und Metall.
3. **Schatten:** Kaskaden auf 3 reduzieren und Distanz auf 35–40 m (spart Zeit), dafür Schattenauflösung der ersten Kaskade erhöhen, damit der Schatten der Figur sauber ist.
4. **Nebel:** leichter Distanznebel (Volume), farblich zum Himmel passend – gibt Tiefe und versteckt das Level-Ende.

## 3. Post Processing (G3) – ein paar Stunden

Alles im vorhandenen Volume, jeder Effekt mit Regler im Grafik-Menü (wie der Motion-Blur-Regler):

1. **Tonemapping** (ACES oder Neutral) + **Farb-Korrektur / LUT** (der „Look“ des Spiels: kühle Schatten, warme Lichter).
2. **Bloom** (dezent, Schwellwert hoch, damit nur Lichter und Effekte glühen).
3. **Vignette** schwach, **Chromatic Aberration** nur bei Treffer/Dash.
4. **SSAO** (Screen Space Ambient Occlusion) für Kontakt-Schatten an Füßen und Kisten.
5. **Anti-Aliasing:** SMAA oder TAA (TAA passt gut zum Motion Blur, braucht aber Motion Vectors – die sind schon an).
6. **Tiefenunschärfe** nur für Kamera-Fahrten/Menüs, nicht im Kampf.

## 4. Umgebung und Level-Kit (G4) – der größte Aufwand, aber nur Content

1. Ein kleines **modulares Kit** (Boden, Wand, Säule, Deckung, Kiste, Tür) in einer Farbpalette; erst Graybox (wie jetzt), dann Texturen/Trim-Sheets.
2. **Decals** (Einschusslöcher, Schmutz), **Skybox**, **Partikel in der Luft** (Staub, Funken).
3. **Ein einziges Arena-Setting** zuerst (z. B. nasse Stadtstraße bei Nacht mit Neon): sehr dankbar für Toon + Bloom + Reflexionen.

## 5. VFX und Game Feel (G5) – das, was „geil“ macht

1. **Sprint:** feine Windlinien am Bildrand, FOV +6 und Kamera-Abstand +0,35 m (ist schon drin), Staub an den Füßen.
2. **Dodge:** Nachbilder (Afterimage), kurze Zeitlupe, Chromatic Aberration.
3. **Waffen:** Mündungsfeuer, Hülsen, Einschlag-Funken, kurze Kamera-Schwingung, Treffer-Marker.
4. **Hit-Stop** (1–3 Bilder Pause bei Treffern) und **Slow-Mo** bei perfektem Ausweichen.
5. **Audio ist die Hälfte des Gefühls**: Schritte pro Untergrund, Waffen, Dodge-Whoosh.

## 6. Qualitätsstufen und Tempo (G6)

- 3 Stufen (Niedrig/Mittel/Hoch): Schattenauflösung und -distanz, SSAO an/aus, Motion-Blur-Qualität, Renderskalierung (FSR/STP-Upscaling), Anzahl Spring-Bone-Knochen.
- Ziel-Budget: **60 Bilder/s auf einer Mittelklasse-GPU in 1080p**, 16,6 ms pro Bild; die Figur selbst (Animation + Feder-Knochen + Skinning) soll unter 2 ms bleiben.
- Grafik-Menü: derselbe Mechanismus wie der Motion-Blur-Regler (Esc = Cursor frei, Regler oben rechts, Werte werden gespeichert).

## 7. Empfohlene Reihenfolge

1. **G1 Toon-Shader + Outline** (sofort sichtbarer Sprung)
2. **G3 Tonemapping + Bloom + LUT** (macht aus „grau“ einen Look)
3. **G2 Licht-Rig + Schatten + Nebel**
4. **G5 Sprint/Dodge-VFX** (Game Feel)
5. **G4 Umgebung** (wenn das Spielgefühl stimmt)
6. **G6 Qualitätsstufen** (kurz vor einer Demo)

---

# Richtung: Third-Person-Shooter statt WuWa-Klon

**Meine ehrliche Einschätzung: ja, das ist die bessere Richtung für dich.**

Warum es passt:
- Yoru ist eine **Spezialagentin mit Beinholstern, Taschen und Taktik-Ausrüstung** – das erzählt „Schützin“, nicht „Schwert-Heldin“.
- Die Laufanimation (Sprint 5 m/s mit Flugphase, Ausweichen per Shift-Tipp) ist schon **bewegungsorientiert**. Ein Shooter lebt von Bewegung + Zielen.
- **Machbar für eine Person:** kein Gacha-Content-Rad (ständig neue Figuren/Banner), keine riesige offene Welt. Ein enger, polierter Arena-Kampf ist genau das, was ein Solo-Entwickler in Qualität liefern kann.
- **Eigenständig:** Anime-Look + stilvolle Doppelpistolen-Bewegung (Gun-Fu, Ausweichen, Rutschen) ist ein klares Alleinstellungsmerkmal gegenüber „noch ein Gacha-Actionspiel“.

Ehrliche Einschränkungen:
- Anime-Shooter ist **nicht leer**: z. B. gibt es mit *Snowbreak: Containment Zone* schon einen Gacha-Anime-TPS. Eigenständig wird es durch **Bewegung + Spielgefühl + Stil + Einzelspieler ohne Gacha**, nicht durch das Genre allein.
- Ein Shooter braucht **viel mehr Animationen** als ein Läufer: Zielen, seitlich/rückwärts laufen (8 Richtungen), Schießen (additiv), Nachladen, Waffenwechsel, Treffer, Tod, Sprung/Landung, Rutschen, Deckung. Das sind etwa 40 Clips; die Pipeline (Blender-Skript -> Unity-Bake) steht, aber jeder Clip ist Arbeit.
- Dazu: **Zielkamera über der Schulter**, **Gegner-KI**, **Treffer-Feedback** (ohne das fühlt sich Schießen tot an), **Audio**.

Vorschlag für den ersten spielbaren Ausschnitt („Vertical Slice“):
1. Eine Arena, 3 Gegnertypen + 1 Boss
2. Doppelpistolen als alleinige Waffe (reines Gun-Fu / John-Wick-Stil, keine Schwerter/Zweitwaffen)
3. Sprint, Ausweichen, Rutschen; Zielen mit Schulterkamera
4. Treffer-Feedback (Hit-Stop, Funken, Treffer-Marker), einfache Gegner-KI
5. Toon-Look (G1) + Tonemapping/Bloom (G3)

Was **nicht** zuerst kommt: Charakterwechsel, Gacha, offene Welt, Multiplayer, Inventar.

## Nächste Animationen (in dieser Reihenfolge)

1. **Jog** (ca. 3,4 m/s): löst das Rutschen bei mittleren Geschwindigkeiten (Walk-Run-Mischung rutscht zwischen 2 und 4,5 m/s).
2. **Zielen im Stand + Gehen/Laufen in 8 Richtungen** (Strafe).
3. **Schießen (additiv), Nachladen.**
4. **Ausweichen in 4 Richtungen**, **Rutschen**.
5. **Sprung/Fall/Landung**, **Treffer/Tod**.
