# Animations-Verbesserungsplan für Yoru

Stand 16.10.2026. Erstellt vom Animations-Chef (CAO) nach Sichtung von 16 Referenz-Videos (WuWa, Genshin, Endfield, Honkai Star Rail, ZZZ, Tower of Fantasy), jedes Bild für Bild, und dem Vergleich mit unseren eigenen Bildern aus Blender.
**(M)** = gemessen, **(G)** = geschätzt nach Augenmaß, **(U)** = aus unserem Code gelesen.

## 1. Was die Referenzen zeigen

1. **Gehen ist ein langer, ruhiger Rhythmus.** Ein Doppelschritt dauert bei WuWa 1,27 s, Genshin 1,33 s, Star Rail 1,35 s, Tower of Fantasy 1,25 s, Endfield 1,17 s. Nur ZZZ geht flott mit 0,63 s. (M)
2. **Laufen ist schneller getaktet.** Doppelschritt: Genshin 0,47 s, WuWa 0,53 s, Endfield 0,58 s, Star Rail 0,58 s, ZZZ 0,60 s. (M)
3. **Starke Vorlage beim Laufen.** WuWa und Genshin lehnen sich etwa 25 bis 35° nach vorn, mit langer Flugphase und Fersenkick. Haare und Stoff strömen fast waagrecht nach hinten (Video "Run Physics"). (G)
4. **Von hinten (so sieht man sie im Spiel) schmale Spur.** Die Füße stehen fast auf einer Linie, die Hüfte schwingt deutlich, der Kopf bleibt ruhig, Rock und Zubehör schwingen gegen die Hüfte. (G)
5. **Jede Figur hat ihren eigenen Gang.** WuWa hat in Version 3.1 pro Charakter ein eigenes "Walking Module" eingebaut. Der Gang ist Teil der Persönlichkeit, kein Standard für alle.
6. **Treppen:** WuWa hebt das Knie sichtbar auf die Stufe, es wirkt wie Fuß-IK oder eine Steig-Anpassung. Genshin, Star Rail und ZZZ spielen die normale Gehanimation wie auf einer Rampe, die Füße schweben über den Stufen. Das Treppen-Video hat 23.000 Likes, Spieler achten also darauf.
7. **Idle:** lange Schleifen (7,6 s), pro Figur eine eigene Haltung, die den Charakter zeigt, dazu kleine Gewichtsverlagerungen und schwingende Haare und Stoffe.
8. **Wasser, Schnee, Schwimmen** wirken über Effekte (Wellen, Gischt, Fußspuren), nicht über die Animation selbst. Das kommt später als VFX.
9. **Klettern und Gleiten** sind eigene Bewegungssets pro Figur (Anke-Video). Für uns später relevant.

## 2. Wo wir stehen (ehrlich)

| Bewegung | Unser Ist-Stand | Gegenüber den Referenzen |
|---|---|---|
| **Walk** | 1,5 m/s, Doppelschritt 0,70 s (171 Schritte/min), Vorlage 6°, Füße stehen fest, schmale Spur, Schwanz ruhig (U) | Sauber und ohne Rutschen. Der Rhythmus ist aber fast doppelt so schnell wie bei den Referenzen (0,70 s gegen etwa 1,3 s), das wirkt "tippelnder" und hastiger. Grund: ihre Beine sind nur 0,743 m lang und wir erlauben kein Rutschen, bei 1,5 m/s bleibt ein Fuß nur etwa 0,4 s am Boden. Die Spiele lassen ihre Füße etwas rutschen. |
| **Run** | 5 m/s, Doppelschritt 0,60 s, Vorlage 17° am oberen Brustkorb, Flugphase 0,17 s pro Schritt, Haare strömen, Arme kompakt (U) | Der Rhythmus passt (Star Rail und ZZZ 0,58 bis 0,60 s). Weniger Vorlage als WuWa und Genshin (17° gegen etwa 25 bis 35°), dadurch weniger Tempo-Gefühl. |
| **Dash** | Gleitschritt, 0,70 s, 5,3 m, eigener Move (nicht nur ein schnellerer Lauf) | Joggen-Ausklang fehlt, Unity-Einbau fehlt. In Unity ist der Dash bisher nur ein Tempo-Schub (14 m/s, 0,24 s) ohne Clip (U). |
| **Idle** | 6 s Schleife: Atmen, Gewicht, Kopf (U) | Gut als Basis. Es fehlt die Haltung, die zur Figur passt (Waffe bereit), und Idle-Breaks nach einigen Sekunden. |
| **Unity-Steuerung** | Ein einziger Blend-Baum Idle, Walk, Run nach Tempo. Drehen mit 900°/s, also praktisch sofort. Keine Neigung, keine IK (U) | Es fehlen Start, Stopp, Wende, Neigen in Kurven, Fuß-IK, Sprung, Fallen, Landen. Genau das macht den Unterschied beim "Spielgefühl". |

**Was schon richtig gut ist:** Schwanz und Haare mit eigener Physik, Blinzeln, Hüft-Swagger, keine Durchdringungen, keine rutschenden Füße.

## 3. Der Plan, nach Wirkung sortiert

Aufwand: klein = ein Abend, mittel = einige Abende, groß = mehrere Etappen. Jeder Schritt läuft nach dem gleichen Muster: Standbilder oder zwei Varianten zeigen, du wählst, ich baue es in Blender (Live-Fenster plus Video), dein OK, dann erst Unity.

| Nr | Schritt | Warum (Beleg) | Aufwand |
|---|---|---|---|
| 1 | **Dash fertigstellen:** Joggen-Ausklang (losgelassen), Einbau in Unity (Clip, Übergänge, echtes Tempo statt 14 m/s). **Stand 16.10. abends:** der Gleitschritt mit Joggen-Ausklang wurde von dir verworfen. Messung: 5 g Start, 4 m Rutschen, schwebende Jog-Schritte, 2,1 s zu lang. Der CAO macht den Dash neu (Brief: `Docs/Moves/Dash.md`). | Dein Signature-Move | mittel |
| 2 | **Start, Stopp, Wende:** je ein kurzer Clip (Idle zu Walk und Run, Run und Walk zu Idle mit Bremsschritt, 180°-Wende), dazu **Neigen in Kurven und beim Beschleunigen** (Code, bewegt den Oberkörper) | Alle Referenzen lehnen sich in Kurven; WuWa 3.1 hat gerade das "Movement" überarbeitet. Bei uns dreht sie in Unity praktisch sofort. | mittel |
| 3 | **Run "Tempo-Gefühl":** Vorlage von 17° auf etwa 22 bis 26°, Doppelschritt von 0,60 auf etwa 0,54 s, mehr Flug und Fersenkick. Arme bleiben kompakt (passt zur Agentin). Vorher 3 Standbilder zur Wahl. | Referenzen (M) und (G) in Abschnitt 1 | klein |
| 4 | **Sprung, Fallen, Landen** (Grundausstattung für einen Third-Person-Shooter) | Der Animator hat die Parameter schon, aber keine Zustände (U) | mittel bis groß |
| 5 | **Fuß-IK und Treppen:** Füße landen auf Stufen und Schrägen, das Becken folgt, Knie hebt auf der Stufe wie bei WuWa | Treppen-Videos 4, 7, 8 | mittel |
| 6 | **Idle mit Charakter:** Haltung "Agentin, Waffe bereit", Idle-Breaks (Blick, Handschuh richten, Schwanz-Zucken) | Idle-Video: jede Figur hat ihre Haltung | klein bis mittel |
| 7 | **Walk-Rhythmus A/B:** A = jetzt (0,70 s), B = ruhigere Variante (etwa 0,9 s mit sauber begrenztem Rutschen unter 12 %). Du siehst beide nebeneinander, dann entscheidest du. | Die Referenzen gehen etwa doppelt so langsam im Takt | klein |
| 8 | **Sekundärbewegung in Unity angleichen:** Haare, Ohren, Schwanz laufen in Unity mit eigener Physik, prüfen ob sie wie in Blender wirken, Wind nach Tempo | "Run Physics"-Video | klein bis mittel |
| 9 | **Weitere Sets später:** Ducken und Deckung, Zielen und Schießen als Oberkörper-Ebene, Ausweichrolle, Treffer, Klettern | TPS-Roadmap | groß |

**Reihenfolge, die ich empfehle:** 1, 2, 3, danach 4 und 5 (sobald die Arena Treppen hat), dann 6 bis 8.

## 4. Qualitätsprüfung für jede neue Animation (CAO-Checkliste)

- **Rhythmus:** Doppelschritt im Rahmen der Referenzen (Walk 0,9 bis 1,35 s, Run 0,47 bis 0,60 s) oder bewusst begründet abweichend.
- **Füße:** unter 2 mm Rutschen auf festem Stand, Ausnahmen nur in benannten Gleit-Fenstern (Dash).
- **Glätte:** keine Sprünge zwischen Bildern, Beine unter 20° pro Bild, Arme unter 15° bei 60 fps.
- **Ansichten:** Rückansicht zuerst (so sieht man sie im Spiel), dann Seite, Vorderseite, Draufsicht.
- **Charakter:** passt zu `Docs/Charakter_Yoru.md` (kompakt, kontrolliert, kein Hüpfen, kein Wedeln).
- **Schleife:** Anfang und Ende nahtlos.
- **Erst Blender, dann Unity.** Geschmacksfragen mit konkreten Bildern, im Auswahlfenster.

## 5. Quellen (16 Videos)

Alle von WarbyGaming, außer 14 (ETHIX SLAYS), 15 (wuwarchie) und 16 (VokerZ).

| Nr | Video | Wichtigste Erkenntnis |
|---|---|---|
| 1 | WuWa vs Endfield vs Genshin, Running (6K3tIwmfNKw) | Run-Takt 0,47 bis 0,58 s, starke Vorlage |
| 2 | dito, Walking (3-XjCBivUeg) | Walk-Takt 1,17 bis 1,33 s |
| 3 | dito, Snow (vHFJhooMQ14) | Fußspuren und Schneeeffekte, kaum Animationsunterschied |
| 4 | dito, Stairs (BA2dxovNZfg) | WuWa hebt das Knie auf die Stufe |
| 5 | HSR vs ZZZ vs WuWa vs Genshin, Water Physics (ym0J5zCaFsw) | Wellen und Gischt (VFX) |
| 6 | Walking Physics (X2q3FIE1OcI) | Walk-Takt 1,27 bis 1,33 s, ZZZ 0,63 s |
| 7 | Stairs Physics (5xxfzHVuIl8) | 23.000 Likes, Treppen sind Spielern wichtig |
| 8 | Stairs Physics pt 2 (bxuS8Q_Pf-M) | normale Gehanimation wie auf einer Rampe |
| 9 | Idle Animation (tbpPWLvnaZo) | lange Idle-Schleife, Figuren-Haltung |
| 10 | Running Animation (1Qpcu3_272U) | Run-Takt 0,47 bis 0,60 s |
| 11 | Swimming (o8nWx5qsvg8) | Schwimmen als Rückansicht, Gischt |
| 12 | Walking Animation #gacha (a_lwJ9rEabg) | Rückansicht, Takt 1,25 bis 1,35 s |
| 13 | Running, Genshin vs Star Rail vs WuWa vs ToF (uHVR3s4n9TE) | Rückansicht, schmale Spur, Hüftschwung |
| 14 | RUN PHYSICS WuWa (HzrHESjBsSo) | Haare und Stoff strömen waagrecht |
| 15 | WuWa 3.1 Walking Modules (GMSbq1R3Tw0) | pro Figur eigener Gang |
| 16 | Anke Glide, Climb and Run (jFC_7SmlJZo) | Gleiten, Klettern, Laufen als eigene Sets |

Messmethode: Die Videos wurden in 1080p Bild für Bild abgetastet, die Schrittzeit kommt aus dem Bildvergleich über die Zeit (Pixelunterschied zwischen Bildern, das tiefste Minimum ist ein voller Zyklus). Die Vorlagewinkel sind nur nach Augenmaß geschätzt.
