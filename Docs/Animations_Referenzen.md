# Animations-Referenzen (Stand 2026-10-21)

Zweck: Vergleichsmaterial für Yoru (Shooter, Schulterkamera, Doppelpistolen). Nur Notizen und Zahlen, keine Bilder aus fremden Spielen speichern.
Zu jedem Punkt steht, ob er **gemessen**, **nach Augenmaß** oder **nicht geprüft** ist.

Aufnahme-Methode: `Tools/AnimRef/capture_frames.js` (Bilder während des langsamen Abspielens, keine Seeks; siehe Kopf der Datei).

## Pose-Referenzen vom Nutzer (21.10., Bilder von PoseMy.Art, nur beschrieben)

Der Nutzer findet diese Haltungen gut. Regel: **nah dran, aber nicht 1:1, und immer zur Persona passend.**
1. Eine Hand streckt die Pistole gerade nach vorn, der andere Arm hängt (Rückansicht und Vorderansicht).
2. Eine Pistole nach vorn-oben gestreckt, die andere tief neben dem Körper. Stand locker, Beine eng. **→ Vorlage für Variante A.**
3. Dynamisch in der Luft: beide Arme gestreckt auseinander nach vorn, ein Bein hochgezogen.
4. Zweihandgriff, in der Luft, Knie hochgezogen.
5. Beide Arme weit zur Seite gestreckt, Pistolen nach außen (stark gespreizt). **→ nur abgeschwächt (Variante B, Arme ca. 30° auseinander), weil Yoru schmal und kontrolliert wirken soll.**

Zielhaltung Runde 1 (Stand 21.10.): drei Varianten A, B, C wurden gebaut und auf Wunsch des Nutzers wieder gelöscht (Papierkorb). `Blender/scripts/build_aim_pose.py` erzeugt sie neu. Beschreibung und Maße stehen im Agenten `yoru-animator`. Entscheidung des Nutzers steht aus.

## 0. Zusammenfassung: neue Erkenntnisse (Stand 2026-10-21)

Rahmen: Yoru ist ein Third-Person-Shooter mit Schulterkamera, Lock-On auf den Körper, Doppelpistolen, Deckung. Zeitlupe ist eine begrenzte Fähigkeit. Zuerst kommt das Schießen, dann Nahkampf und Stealth.

### 0.1 Gemessen (Pixel-Autokorrelation, tiefstes Minimum = ein Vollzyklus aus zwei Schritten)

| Spiel | Laufen | Gehen | Bemerkung |
|---|---|---|---|
| Genshin | 0,47 s | 1,33 s | Laufen heute in zwei Clips bestätigt |
| WuWa | 0,53 s | 1,27 s | Laufen in uHVR3s4n9TE: 0,25 s, ungeklärt |
| Star Rail | 0,55 s | 1,35 s | heute 0,55 s, früher 0,58 s |
| Endfield | 0,58 s | 1,17 s | heute 0,583 s |
| ToF | 0,48 s | 1,25 s | Laufen nur 1,2 s Ausschnitt, unsicher |
| ZZZ | 0,60 s | 0,63 s | früher gemessen, Gehen ist der flotte Ausreißer |
| **Yoru (aus dem Code, nicht gerendert)** | **0,60 s** | **0,70 s** | Oberkörperneigung beim Laufen 17° |

### 0.2 Was die Referenzen für die Fortbewegung zeigen (nach Augenmaß)
1. **Laufen:** Oberkörper leicht nach vorn, Arme angewinkelt, lange Flugphase, Umhänge und Haare fliegen mit. Die Neigung wirkt bei den Gacha-Spielen stärker (auf Augenmaß 25 bis 35°). Yoru liegt bei 17°, also aufrechter. Das passt zu „kontrolliert“, ist aber eine bewusste Entscheidung wert.
2. **Gehen:** Die Vergleichsspiele gehen mit 1,17 bis 1,35 s pro Zyklus. Yoru geht mit 0,70 s deutlich flotter. Grund sind die kurzen Beine (0,743 m) bei 1,5 m/s. Ob das gewollt ist, ist offen.
3. **Zielhaltung:** Die Mocap-Demo hält das Gewehr auf Brusthöhe. Das passt zur Yoru-Regel „Hände auf Brust- bis Bauchhöhe“.
4. **Deckung:** Beim Peek aus der Ecke (Battlefield 6 gegen ARC Raiders) führt der Oberkörper die Bewegung an, die Waffe ist schon vor der Brust, die Figur tritt kurz hervor.
5. **Nachladen:** Die Low-Poly-Demo zeigt nur einen Zweihandgriff, das Nachladen selbst ist nicht zu lesen. Dafür braucht es eine bessere Referenz.

### 0.3 Konzepte aus Texten (nicht in Videos verifiziert)
- **Split-Body:** Oberkörper (Zielen) und Beine (Laufen) werden getrennt gesteuert und überblendet. Das passt zu Schießen im Laufen. (Overdare-Dokumentation)
- **Strafe in acht Richtungen** mit Diagonalen statt einer allgemeinen Laufanimation. (Overdare)
- **Bullet-Time mit Varianten:** Max Payne 3 nutzt viele Animationsvarianten, damit sich jede Zeitlupe anders anfühlt. (Gaming Nexus)
- **Dead Eye (RDR2):** Zeitlupe in Stufen, zuerst verlangsamen, dann Ziele markieren. Die Quellen nennen unterschiedliche Tasten (R3 oder L3).
- **Gears of War:** Das Hochziehen in Deckung (Perching) wurde gestrichen, weil es zu viel Übersicht von oben gab. (Engadget)
- **Ghost of Tsushima:** Zeitlupe beim Zielen ist nicht belegt. Nicht als Referenz nutzen.

### 0.4 Methode für alle künftigen Referenzen
- **Seek-Bilder können veraltet sein.** Ein Seek, der zu lange dauert, zeichnet das alte Bild noch einmal. Dann sehen alle Bilder gleich aus. Bilder deshalb während des langsamen Abspielens aufnehmen: `Tools/AnimRef/capture_frames.js`.
- **Pro Zyklus 8 bis 12 Bilder.** Raster über ganze Videos nur zum Finden von Abschnitten.
- **Layout zuerst prüfen:** Felder übereinander, Felder nebeneinander oder eine Abfolge (uHVR3s4n9TE ist eine Abfolge).
- **Zyklus:** Das tiefste Minimum ist der Vollzyklus. Ist es unklar (WuWa 0,25 oder 0,53 s), mehr Zyklen messen.
- **Werbung** abwarten, nicht anklicken. `javascript_tool` bricht nach 45 s ab.
- Die Beobachtungen aus den älteren Rasterbildern (Schnee, Treppen, Wasser usw.) können veraltete Bilder enthalten. Ihre Zahlen sind verlässlich, die Beschreibungen nur grob.

### 0.5 Was fehlt: Animationen und ihre Referenz-Lage

| Animation | Stand bei Yoru | Referenz-Lage |
|---|---|---|
| Idle | vorhanden, wird neu gebaut | Gacha-Idle dicht gesichtet (21.10.): Gesten-Sequenzen, kaum Gewichtsverlagerung, siehe Abschnitt 4.1 |
| Gehen | vorhanden (0,70 s) | gemessen, Vergleich oben |
| Laufen | vorhanden (0,60 s) | gemessen, Vergleich oben |
| Dash / Ausweichen | offen | keine Shooter-Referenz, Gacha-Ausweichen nicht gesucht |
| Zielhaltung (Idle mit Waffe) | fehlt | Mocap-Demo, Gewehr auf Brust, gesichtet |
| Strafe in acht Richtungen | fehlt | Mocap-Demo seitwärts gesichtet, Diagonalen nur Text |
| Schießen (Oberkörper-Layer) | fehlt | keine dichte Referenz |
| Nachladen | fehlt | Demo zu schwach |
| Deckung / Peek | fehlt | BF6 gegen ARC Raiders gesichtet |
| Sprung, Landung | fehlt | nicht gesucht |
| Treffer, Tod | fehlt | nicht gesucht |

**Vorschlag für die Reihenfolge:** Zielhaltung (Standbild) → Strafe mit Oberkörper-Layer → Schießen → Nachladen → Deckung. Das ist eine Empfehlung, die der Nutzer bestätigen muss.

### 0.6 Offen
- **Nicht gesichtet:** lLjM-sAKpNI, I45amgGjJf4, wyBf4ZWOYio, f2g6zMag4mA, 4uhWl03Ht3w, WVB_J1BUr6g, 8rYKGVLBBpU, I-Qmf6YwEfY, KoVq7CzRjVw, phT67PM_uDI
- **Teilweise:** o8nWx5qsvg8, jFC_7SmlJZo
- **Nicht gesucht:** Gacha-Shooter (Endfield, Snowbreak, ZZZ, NTE)

## 1. Fortbewegung (die 16 Links aus dem Nutzer-Auftrag)

Zyklus = zwei Schritte. Gemessen mit Pixel-Autokorrelation (tiefstes Minimum).

| Link | Inhalt | Format | Status |
|---|---|---|---|
| 6K3tIwmfNKw | Laufen: WuWa / Endfield / Genshin | 3 Felder übereinander | Zyklus gemessen: Genshin 0,47 s, WuWa 0,53 s, Endfield 0,58 s |
| 3-XjCBivUeg | Gehen: WuWa / Endfield / Genshin | 3 Felder | Bilder angeschaut; Zyklus früher gemessen (WuWa 1,27 s, Endfield 1,17 s, Genshin 1,33 s) |
| vHFJhooMQ14 | Schnee | 3 Felder | Überblick, nach Augenmaß |
| BA2dxovNZfg | Treppen | 3 Felder | Überblick: Figuren steigen die Stufen, Knie nicht genau geprüft |
| ym0J5zCaFsw | Wasser | 4 Felder (HSR / ZZZ / WuWa / Genshin) | Überblick. Spritzer ist Effekt (VFX), keine Animation |
| X2q3FIE1OcI | Gehen mit Physik | 4 Felder | Überblick, nach Augenmaß |
| 5xxfzHVuIl8 | Treppen mit Physik | 4 Felder | Überblick, nach Augenmaß |
| bxuS8Q_Pf-M | Treppen mit Physik, Teil 2 | 3 Felder (HSR / ZZZ / Genshin) | Überblick, nach Augenmaß |
| tbpPWLvnaZo | Idle (7,6 s) | 3 Felder (HSR / ZZZ / Genshin) | Überblick: Gewichtsverlagerung, kleine Posenwechsel |
| 1Qpcu3_272U | Laufen | 3 Felder (HSR / ZZZ / Genshin) | Überblick: starker Vorlauf, lange Flugphase (Augenmaß) |
| uHVR3s4n9TE | Laufen, 4 Spiele nacheinander (20 s Schleife) | **kein Feld-Layout**, nacheinander | siehe Abschnitt 1a |
| o8nWx5qsvg8 | Schwimmen (Gacha-Montage, ToF und weitere) | Short | **teilweise**: Überblick unvollständig, Aufnahme hängte sich auf. Wasser-Spritzer sind Effekt |
| a_lwJ9rEabg | Gehen (Montage: Star Rail 0–3,5 s, WuWa 4–6,8 s, Genshin 8–10,7 s, ToF ab 12 s) | Short, 16 s | Überblick gesichtet, nach Augenmaß |
| HzrHESjBsSo | Laufen, Run-Physik (WuWa), 17,5 s | Short, Erklärvideo mit Untertiteln | Überblick gesichtet: eine Figur, Umhang und Haare fliegen mit. Keine Zahlen im Video |
| GMSbq1R3Tw0 | Gehen in Version 3.1, „Movement Optimization“ (WuWa), 23 s | Hochformat | Überblick gesichtet: Figur geht am Strand auf die Kamera zu. Keine Zahlen |
| jFC_7SmlJZo | Gleiten mit Schirm, Klettern, Laufen (WuWa, 88 s) | normales Video, Werbung davor | **teilweise**: Werbung abgewartet, nur 2 Bilder aufgenommen (Aufnahme brach ab). Gleiten mit Schirm gesehen. Rest nicht geprüft |

### 1a. uHVR3s4n9TE (Laufen, 20 s)

Die Spiele folgen einander, es gibt keine Felder:
- Genshin: 0,0 bis 5,5 s
- WuWa: 6,0 bis 12,0 s
- Star Rail: 12,3 bis 17,4 s
- ToF: 17,5 bis 18,9 s
- danach wieder Genshin (Schleife)

Zyklus (gemessen, Ausschnitt bei jedem Spiel):
- Genshin: **0,467 s** (bestätigt)
- Star Rail: **0,55 s**
- ToF: **0,483 s** (nur 1,2 s Ausschnitt, unsicher)
- WuWa: **0,25 s oder 0,53 s**. Das tiefste Minimum liegt bei 0,25 s, das ältere Ergebnis (0,53 s) passt besser zu den übrigen Läufen. Ungeklärt.

Acht Bilder über einen Zyklus zeigen für jedes Spiel einen klaren Ablauf: Beine wechseln, Arme schwingen, die Figur bleibt im Bild.

### Zusammenfassung Fortbewegung (Augenmaß)
- Laufen: Genshin und Endfield mit deutlichem Vorlauf, WuWa aufrechter. Star Rail und ToF mit flatternden Umhängen.
- Die Laufzyklen liegen zwischen 0,47 und 0,58 s. Gehen liegt bei 1,17 bis 1,35 s.

## 2. Schießen, Zielen, Deckung (Shooter)

Das fehlt im bisherigen Projekt fast vollständig. Gefunden auf YouTube, Stand der Prüfung unten.

| Link | Inhalt | Status |
|---|---|---|
| ryKfyogWBSE | Aus der Deckung lehnen (Battlefield 6 links, ARC Raiders rechts), 4,5 s | gesichtet, grob: Figur tritt aus der Ecke, Waffe vor der Brust, Oberkörper voran |
| h0GT8LGGxH4 | Nachladen Pistole, Low-Poly-Demo, 5 s | schwach: Zweihandgriff, Figur steht. Das Nachladen ist in dieser Auflösung kaum zu erkennen |
| JDPT4SUQhtk | Gewehr seitwärts gehen, anhalten (Mocap-Demo, 20 s) | gesichtet im Überblick: Zielhaltung, Seitwärtsschritt, Stopp. Keine dichte Aufnahme |
| lLjM-sAKpNI | Seitwärts starten, Gewehr (16,6 s) | Link gefunden, Bild nicht erzeugt. **nicht gesichtet** |
| I45amgGjJf4 | Vertikales Zielen, 3rd Person Shooter (25 s) | Link gefunden, Bild nicht erzeugt. **nicht gesichtet** |
| wyBf4ZWOYio | UE4 Pistolen-Animationen überarbeitet (1:02) | Beschreibung: Mixamo-Animationen wurden angepasst. **nicht gesichtet** |
| f2g6zMag4mA | ZeroStrike, UE5 Pistolenkampf (Short) | **nicht gesichtet** |
| 4uhWl03Ht3w | ZeroStrike, UE5 Pistolenkampf (1:55) | **nicht gesichtet** |
| WVB_J1BUr6g | Alle Strafe-Zielarten erklärt (0:53) | **nicht gesichtet** |
| 8rYKGVLBBpU | „3rd Person Aiming Is Cursed“ (12:55), Thema Zielen über die Schulter | **nicht gesichtet** |
| I-Qmf6YwEfY | UE4 Cover-Shooter, Zielen aus Deckung (38 min) | **nicht gesichtet** |
| KoVq7CzRjVw | „Your sight in third person shooters“ (Short) | **nicht gesichtet** |
| phT67PM_uDI | Zielen mit IK, Unity-Tutorial (3:33) | **nicht gesichtet** |

### Konzepte aus Texten (nicht aus Videos, nicht gemessen)
- **Split-Body:** Oberkörper (Zielen) und Beine (Laufen) werden getrennt gesteuert und überblendet. Passt zu Schießen im Laufen. (Overdare-Dokumentation)
- **Strafe in acht Richtungen** inklusive Diagonalen statt einer allgemeinen Laufanimation. (Overdare)
- **Bullet-Time mit vielen Varianten:** Max Payne 3 nutzt viele Animationsvarianten, damit sich die Zeitlupen nicht gleich anfühlen. (Gaming Nexus, Text)
- **Dead Eye (RDR2):** Zielmodus mit Zeitlupe und Stufen (erst Verlangsamung, dann Zielmarkierung). Die Quellen nennen unterschiedliche Tasten (R3 oder L3). Ungeprüft.
- **Gears of War:** Deckungssystem, ein „Perching“ genanntes Hochziehen wurde 2009 gestrichen. (Engadget, Text)
- **Ghost of Tsushima:** Zeitlupe beim Zielen ist nicht belegt. Die Quellen widersprechen sich. Nicht als Referenz verwenden, bis ein Video gesichtet ist.

## 3. Offen

- Gacha-Shooter als Referenz (Endfield, Snowbreak, ZZZ, NTE, ToF): **noch nicht gesucht**.
- Dual-Pistolen in der dritten Person: bisher nur Kurzclips und Tutorials gefunden.
- Die Punkte mit **nicht gesichtet** brauchen dichte Aufnahme, bevor sie als Referenz gelten.

## 4. Grundbewegungen neu (Stand 2026-10-21)

Reihenfolge: Idle, Gehen, Laufen (Dauerlauf), Sprinten. Die Antworten des Nutzers (Tempo, Gehzyklus, Neigung) stehen in `Docs/Charakter_Yoru.md`. Hier stehen nur die Referenz-Beobachtungen zu den neuen Bewegungen.

### 4.0 NTE-Aufnahmen des Nutzers (Bildschirmaufnahmen vom 23.10., die Heldin, die Yoru am nächsten ist)
Die Dateien liegen beim Nutzer in `Downloads/NTE recording/` (5 Clips, 30 fps). Ausgewertet wurde Bild für Bild (alle Bilder eines Zyklus), nicht als Raster. Die Bilder liegen nur lokal in `Blender/previews/ref_nte/` (nicht im Git, nicht im Repository). Nach Augenmaß und gemessen:
- **Clips:** 194135 und 194212 (Seitenansicht: Stand, Lauf, Halt), 194448 (von hinten, Lauf), 194516 (von vorn, Lauf mit Handy in der rechten Hand, am Ende Gesichts-Nahaufnahme), 194618 (Draufsicht, nicht nutzbar).
- **Lauf (gemessen):** Das vertikale Auf und Ab der Figur hat in allen Laufstücken 10 Bilder Periode (ac 0,5 bis 0,7). Das ist ein Schritt, ein Doppelschritt sind **20 Bilder = 0,667 s** bei 30 fps (180 Schritte pro Minute). Zum Vergleich: Genshin 0,47 s, WuWa 0,53 s, Endfield 0,58 s.
- **Lauf, Körper (Augenmaß):** Oberkörper deutlich nach vorn geneigt (ca. 25°), Kopf nach vorn, langer Schritt, Fußspitze setzt zuerst auf, das Schwungbein klappt hoch bis zum Gesäß, Mantel und Haare wehen nach hinten.
- **Lauf, Arme (Augenmaß, Seiten- und Rückansicht):** Beide Ellbogen etwa 90° gebeugt und eng am Körper, der ganze Arm pendelt aus der Schulter heraus (Oberarm ca. -40° bis +35°), die Hand läuft zwischen Bauchhöhe (hinten) und Brusthöhe (vorn). Locker geschlossene Faust, Handgelenke entspannt, die Finger der hinteren Hand sind etwas offen. Der Arm zieht von Oberarm über Unterarm zur Hand nach, nichts ist steif oder parallel.
- **Lauf, nachgemessen (23.10., Lauf W Runde 1, Bild für Bild an Clip 194135 f96–123 und 194448 f56–84):**
  - Die Aufnahmen enthalten **doppelte Bilder** (ca. 6 von 20 je Zyklus, z. B. 102 = 101, 104 = 103, 110 = 109). Alle Zeiten gelten in Aufnahme-Bildern (30 fps), auch die 20 Bilder pro Zyklus.
  - **Bodentempo:** Der aufgesetzte Fuß wandert 45 px pro Aufnahme-Bild (f111→f116: 226 px in 5 Bildern), die Bodenkorrelation gibt 46 px. Ein Schritt (10 Bilder) ≈ 455 px. Standhöhe (f20, mit Absätzen) ≈ 520 px, Hüftgelenk ≈ 280 px über der Sohle, Bein (Hüfte–Knöchel) ≈ 252 px. **Schritt ≈ 0,87 Körperhöhen ≈ 1,8 Beinlängen.** Für Yoru (Bein 0,743 m): Schritt 1,33 m, **Tempo ≈ 4,0 m/s** (die früheren 4,5–5 m/s zählten nur die Bilder ohne Doppel).
  - **Kontakt und Flug:** Fuß setzt bei ca. f110,5 auf und löst bei ca. f116 (ca. 0,17–0,18 s Kontakt), danach ca. 0,15 s Flug. Die Haare sind ca. 8 Bilder nach dem Aufsetzen am höchsten (sie hängen ca. 1,5 Bilder hinter dem Körper).
  - **Haltung (Augenmaß mit Raster):** Rumpf Hüfte→Hals ca. 17–20° vor, Kopf deutlich vor den Schultern; Standknie in der Mitte ca. 30–35°, Schwungbein bis ca. 110° gefaltet, Knie-Antrieb ca. 55–60°; der Fuß landet ca. 0,4 Beinlängen vor der Hüfte.
  - **Arme:** Die Extreme liegen in der Mitte der Flugphase (der Arm ist kurz nach dem Abdruck derselben Seite ganz vorn). Vorn: Oberarm ca. 30° vor dem Lot, Ellbogen ca. 95°, Faust auf Schulter- bis Brusthöhe ca. 0,3 m vor der Schulter. Hinten: Oberarm ca. 25–35° hinter dem Lot, Ellbogen öffnet bis ca. 45–60°, Hand an der Hüfte. Vorn ca. 8, hinten ca. 6 Aufnahme-Bilder.
  - **Phasen zum Vergleich:** Seitenclip 194135: Kamera auf ihrer rechten Seite, rechter Fuß setzt bei f110,5 auf. Rückclip 194448: rechter Fuß bei ca. f59,5.
- **Noch nicht aufgenommen:** Gehen, Joggen, Idle von der Seite. Der Nutzer wurde gebeten, sie nachzureichen.

### 4.1 Idle (tbpPWLvnaZo, dicht gesichtet am 21.10.)
Clip 7,58 s, Hochformat, drei Spiele übereinander (oben Star Rail, Mitte ZZZ, unten Genshin). Pro Spiel 6 Bilder während des Abspielens (0,2 bis 7,3 s, Abstand ca. 1,2 bis 1,7 s). Das reicht für Haltungen, nicht für das Atmen. Nach Augenmaß, nichts gemessen.
- **Alle drei sind Lobby-Sequenzen mit einer Geste, keine kurzen Schleifen.** Als Vorlage taugen sie für Stand und Haltung, nicht für ein ruhiges Spiel-Idle.
- **Star Rail:** aufrecht, Arme hängen, Füße eng. Ab ca. 3 s hebt sie eine Hand mit Leuchteffekt vor das Gesicht, bei 7,3 s ist ein Arm zur Seite gestreckt. Kaum Gewichtsverlagerung.
- **ZZZ:** Die Figur läuft im Bild herum (bei ca. 3,3 s ist sie aus dem Bild, bei 4,5 s zurück mit großer Waffe). Ein ruhiger Stand ist nicht zu sehen.
- **Genshin:** sehr aufrecht, Füße eng, eine Hand an der Hüfte (0,2 s), später eine Hand mit Effekt (3,0 bis 4,7 s), Kopf leicht geneigt (5,8 s), Gewicht bleibt mittig. Zopf und Bänder schwingen leicht nach.
- **Kandidaten für ein echtes Spiel-Idle (nicht gesichtet, Stand 21.10.):** KuRKybZTuTE (Endfield, alle Operator-Idles und Menü-Animationen, 24:30), QyFhTp2G2fg (Snowbreak, Jingran Idle, 1:37), Cv5VwzSz718 (Short, Idle Endfield gegen Arknights). Gesucht ist ruhiges Stehen von hinten ohne Geste, 5 bis 10 s, mit Blick auf Gewichtsverlagerung und Armhaltung. Die Aufnahme braucht den sichtbaren Browser-Bereich.
- **Einschätzung für Yoru (nicht gemessen):** Schmaler Stand und ruhiger Oberkörper passen zur Persona. Eine deutliche Gewichtsverlagerung (Kontrapost) kommt in diesen Referenzen kaum vor, sie wäre also eine eigene Entscheidung. Die Atmung ist in den Bildern nicht zu erkennen, dafür gibt es keine Zahl.
