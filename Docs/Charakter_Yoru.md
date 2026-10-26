# Yoru – Charakter- und Bewegungs-Leitfaden

Für alle Posen, Animationen und Looks von **Shirogane Yoru** (Hauptfigur von Zero Protocol).
**Regel:** Bevor Claude etwas zu Posen, Positionen oder Look fragt, steht hier zuerst die Antwort. Gefragt wird nur, wenn es hier nicht steht oder echter Geschmack ist (dann mit 2–3 konkreten Bildern).
Das ist ein lebendiges Dokument: bitte korrigieren und ergänzen. **(N)** = hat der Nutzer so gesagt, **(A)** = Annahme von Claude, bitte prüfen.

## Wer sie ist
- **Spezialagentin, kein Neko-Kawaii.** (N, 14.10.)
- Silber-lila Haare, Katzenohren und Katzenschwanz, violette Augen, schwarzes taktisches Outfit mit Weste, Schulterpolstern, Oberschenkel-Holster und Taschen. (N)
- **Waffen-Identität:** Keine anderen Waffen, kein Schwert, keine Gewehre, kein Waffenrad. **Ausschließlich zwei Dual Pistols** in den Oberschenkel-Holstern – kompromisslos im **John-Wick-Stil** (Gun-Fu). Sämtlicher Nahkampf, Konter und Exekutionen laufen über die Pistolen (Schlitten-Schläge, Hebeln, Kontaktschüsse). (N, 25.10.)
- Welt: Zukunftsstadt nach einer Katastrophe, taktische Agenten-Sci-Fi, ähnlich Endfield. Gespielt als **Third-Person-Shooter**, kein WuWa-/Gacha-Klon. (N, 15.10.)
- Auftreten: souverän, kontrolliert, „richtig bad“ (cool, mit Attitüde, Hüftschwung beim Gehen), dabei weiblich und geschmeidig. (N: „soll richtig bad sein“, „Arme zu weit weg vom Körper, wirkt zu maskulin“)

## Bewegungsprinzipien
1. **Kontrolliert und sparsam.** Keine überflüssigen Bewegungen, nichts wedelt oder zappelt. (A)
2. **Katzenhaft geschmeidig.** Fuß rollt weich ab (Ferse, Ball, Zeh), die Wirbelsäule ist organisch (Brustkorb federt, Schultern folgen), nie ein steifes Brett. (N/A)
3. **Schmal und windschnittig.** Arme eng am Körper, Ellbogen kompakt, schmale „Catwalk“-Spur der Füße. (N)
4. **Arme:** Hände und Fäuste auf Brust- bis Bauchhöhe, nie am Kinn. Rückschwung locker, Unterarm öffnet sich nach unten. Die Ausrüstung (Schulterpolster, Weste, Hüft-Gear) hält die Arme ein Stück vom Körper weg, das ist okay, aber nicht abgespreizt. (N/A)
5. **Schwanz:** schlank, ruhig, elegant. Langsames kleines Schwingen, **kein Wedeln**. Beim Gehen sanfte S-Kurve (Schwanenhals), beim Laufen stromlinienförmig nach hinten. In Ruhe eng eingerollt. (N)
6. **Haare und Ohren** reagieren auf Tempo und Ruck, aber dezent. Der Haarwind soll eher schwach sein. (N)
7. **Brust und Haare** federn weich nach. (N: Brust-Bounce und animierte Haare gewünscht)
8. **Kopf** bleibt ruhig und schaut nach vorne, auch wenn der Körper sich stark neigt. (A)
9. **Waffe:** Später kommen Zielen und Schießen. Arme und Haltung müssen sich dazu überblenden lassen, also eher kompakt vor dem Körper als weit ausgebreitet. (A)
10. **Technik:** Keine Durchdringungen (Arme gegen Gear, Beine gegeneinander), keine rutschenden Füße. Alles in Blender zeigen, bevor es nach Unity geht. (N)

## Was sie nicht macht
- Hüpfen, Armrudern, abgespreizte Arme, Boxer-Fäuste am Kinn.
- Niedliche Neko-Gesten (Pfötchen, Schwanzwedeln, Hüpfen).
- Keine Schwerter, Katanas, Fantasie-Großwaffen oder Waffenrad-Wechsel (nur Dual Pistols / Gun-Fu). (N, 25.10.)
- Roboterhaft steife Arme oder reine Sinus-Bewegungen.
- Stampfende, rhythmische Sprünge oder Wippen („tot, tot, tot“): wirkt leblos. Lieber ein ruhiger, durchgehender Fluss. (N, 16.10.)

## Bewegungs-Set (Stand 16.10.2026)
- **Gehen** 1,5 m/s: fertig und in Unity („Swagger“).
- **Run** 5 m/s: fertig und in Unity.
- **Dash:** in Arbeit. Wunsch des Nutzers:
  - Start aus Gehen **und** Run, kurzer Anlauf (ca. 0,3 s), etwas schneller als der Run.
  - Look wie bei WuWa / NTE / Genshin / Endfield **oder etwas Eigenes, das zu einer Agentin passt**.
  - **Gewählt (16.10.): „Gleitschritt“** = tiefer, langer Ausfallschritt, ruhiger Oberkörper, Hüfte leicht gedreht, beide Hände schützend an der Brust, die Füße gleiten über den Boden. Muss **richtig smooth** sein (N). Verworfen: Sprint-Schübe („nur ein schnellerer Lauf“) und Panther („tot tot tot“, stampfende Sprünge).
  - Danach: Taste gehalten, dann **Run**. Losgelassen, dann leichtes Joggen und zurück zum Gehen. (16.10.: Gleitschritt mit Joggen-Ausklang gebaut und vom Nutzer als „mega scheiße“ verworfen. Der Dash wird neu entworfen, Stand offen.)
  - Länge und Weite: so, dass es gut aussieht (Claude entscheidet, ca. 0,45 s und 5 m).
  - Kein bloß schnellerer Lauf: der Dash muss sich als eigener Move vom Run unterscheiden.
- **Grundbewegungen komplett neu (21.10.)**, Reihenfolge Idle, Gehen, Laufen, Sprinten, immer nur eine Bewegung, danach Freigabe durch den Nutzer. Antworten des Nutzers (N):
  - **Laufen** = Dauerlauf (Jog) mit ca. 3,4 m/s, fehlte bisher. **Sprinten** = der bisherige Run mit 5 m/s, neu entworfen.
  - **Gehen** etwas langsamer: ca. 0,95 s pro Doppelschritt, Tempo ca. 1,2 m/s (bisher 0,70 s und 1,5 m/s).
  - **Neigung** beim Sprinten ca. 25° (bisher 17°), beim Dauerlauf etwa die Hälfte (ca. 12°).
  - Die alten Clips (Idle, Walk, Run) bleiben unangetastet und sind nur technische Vorlage. Neue Dateien heißen `Blender/Yoru_<Bewegung>_v2.blend`.
  - **Idle, Runde 1 (21.10.):** Stand **A Kontrapost** gewählt (Gewicht auf einem Bein, Hüfte seitlich), aber von hinten wirkte er „komisch“, wird überarbeitet. Arme **locker hängend**, wirkten noch zu steif, werden lebendiger. **Hände vorn** (links hält das rechte Handgelenk) ist als späteres **Special Idle** vorgemerkt (N). Schwanz in Ruhe eng eingerollt (Leitfaden). Der Nutzer will die Animation früh sehen: Korrektur und erstes Blockout kommen in Runde 2 zusammen.
  - **Idle, Runde 2 (21.10.):** **A2** (Stand A mit senkrechtem freiem Bein, Hüfte 4,5°, Arme locker und nicht gespiegelt) ist von hinten freigegeben (N). Die Bewegung soll **deutlicher** sein (Brust und Schultern vorher nur 3 mm, aus Spielkamera-Abstand kaum zu sehen), bleibt aber ruhig (N). **Schwanz** bleibt hängend mit eingerollter Spitze (N). Schleife: 8 s, 30 fps, Atmen alle 4 s.
  - **Idle, Runde 3 (21.10.):** Schleife 12 s, 30 fps, Atmung (Schultern 14 mm, im Spielkamera-Bild 2 bis 3 px) **passt** (N), **zwei Lidschläge in 12 s passen** (N). Der Nutzer sagt „ja, sonst ist alles gut“, nur das **Gesicht hat keine Emotionen**. Der Gesichtsausdruck wird ergänzt (Runde 4: drei Varianten als Bild), danach ist das Idle fertig.
  - **Idle, Runde 4 (21.10.), Gesicht:** Grundausdruck **B kühl-wachsam** (Augen fokussiert und schmaler, Mund gerade, Ohren leicht nach vorn), **so subtil wie auf dem Blatt** (N). Die helle Iris (fast weiß-lila, der Steckbrief nennt violette Augen) **bleibt so** (N), es gibt keine Modelländerung. Das Modell hat 58 Shape Keys, brauchbar für die Stimmung sind EYE_Fun/Angry/Sorrow und MTH_Fun/Up/Neutral/Close/Angry. Die Brauen-Keys verdeckt der Pony, EYE_Joy und MTH_Joy sind zu niedlich. Dieser Ausdruck gilt als Grundwert auch für Gehen, Laufen und Sprinten, beim Sprinten darf er etwas fokussierter werden.
  - **Idle, Runde 5 (22.10.):** Ausdruck B ist eingebaut, aber der Nutzer sagt **nein** zur Schluss-Freigabe (N): Die **Arme und Hände schweben** in der Luft und lehnen sich nicht an, es gibt **keine Bewegung** in den Armen, und die **Ellbogen verbiegen sich komisch**. Sonst passt alles. Runde 6 (Sonderrunde) behandelt nur Arme und Hände. **Regel für alle Bewegungen:** Arme brauchen Kontakt zum Körper oder Gear (Hände auf Tasche, Holster oder Hüfte, Oberarme locker an der Weste) und die Hände sind am Gear verankert, damit sie mit dem Körper mitgehen. Ellbogen und Handgelenke müssen im Nahbild glatt biegen (Scharnierachse, Twist), nicht nur in Millimetern stimmen.
  - **Idle FERTIG (22.10., Runde 6, Freigabe „Ja“ durch den Nutzer, N):** Datei `Blender/Yoru_Idle_v2.blend` (12 s, 30 fps, Körper-Action `Yoru_Idle_v2`, Gesichts-Action `Yoru_Idle_v2_Face`). Stand A2, Arme locker, die Hände liegen auf dem Gear (rechts auf dem Oberschenkel-Holster, links außen am Oberschenkel unter der Gürteltasche) und gehen mit dem Körper mit, die Ellbogen zeigen fast gerade nach hinten, die Unterarm-Verdrehung ist auf ca. 18° begrenzt. Die Hände wandern nur 6 bis 8 mm, das lässt der Nutzer so (N). Gesicht B kühl-wachsam, zwei Lidschläge in 12 s, Atmung deutlich (Schultern 14 mm). Bilder und Videos: `Blender/previews/Idle_v2/` (`final_idle.mp4`, `round6_idle_arme.mp4`). **Ursache des Schwebens:** Die Handziele hingen im leeren Raum, und der Ellbogen war 55° nach außen gestellt, das Modell hat keine Twist-Knochen. Regel: ruhende Hände an Gear-Punkten verankern, den Ellbogen fast gerade nach hinten führen, Durchdringung mit dem exakten Schnitttest prüfen.
  - **Idle, Zusatzwunsch (22.10., nach „fertig“):** mehr Dynamik, **Ohren und Schwanz dürfen leicht wackeln**, die **Haare wehen ganz leicht im Wind**, es soll gut aussehen (N). Das lockert „kein Wedeln“ (Schwanz) für das Idle: klein, langsam und elegant (S-Welle, Spitze zuckt leicht), kein Hin-und-her-Wedeln.
  - **Idle, Runde 7 (22.10.):** Ohren (einzelne Zuckungen, viermal in 12 s, N) und Schwanz (S-Welle etwa doppelt so weit, Spitze rollt ein und aus, N) **passen so**. Der Wind soll **etwas mehr** werden (N). Der Idle gilt erst nach dem nächsten „ja“ als fertig.
  - **Idle ENDGÜLTIG FERTIG (23.10., Runde 8, „Ja“ des Nutzers, N):** Wind „so passt es“ (stetige Neigung der Strähnenspitze 6,3°, zwei Böen bei 3,9 s und 9,3 s, Ohrenzuckungen viermal in 12 s, Schwanzwelle doppelt so weit mit einrollender Spitze). Datei `Blender/Yoru_Idle_v2.blend`, Vorgänger-Fassungen als Kopien in `Blender/work/Idle_v2/` (`..._final_v1_arme_schweben`, `..._final_v2_arme_ok`, `..._final_v3_wind_leicht`). Video `Blender/previews/Idle_v2/round8_idle_wind.mp4`.
  - **Idle in Unity eingebaut (23.10., vom Hauptagenten, auf Wunsch des Nutzers):**
    - **Körper:** `Assets/Animations/Yoru/Yoru_Idle.anim` ist jetzt das neue Idle (361 Bilder, 12 s, 30 fps, Loop-Naht 0). In Unity gegen Blender gemessen: Becken, Füße, Hände, Ellbogen und Kopf stimmen auf ca. 1 mm, die Füße driften über den Loop 1,4 mm, im Spielmodus 2 mm. Das alte Idle liegt gesichert in `Archiv/Idle_v1/` (Stream, Pose-Datei, Clip). Der Controller bleibt unverändert, der Clip hat dieselbe GUID.
    - **Gesicht:** neue Komponente `Assets/Scripts/Player/YoruFaceExpression.cs` (Ausdruck B mit der langsamen Schwankung und dem Lidschlag-Zusammenspiel). Sie ist in `Assets/Editor/ArenaBuilder.cs` eingetragen und an Yoru in der Szene `Arena.unity` angehängt. Der Ausdruck bleibt auch beim Gehen und Rennen.
    - **Schwanz, Ohren, Haare** (`YoruSecondaryMotion.cs`, nur im Stand, Gehen und Rennen unverändert): Schwanzform aus Blender (Mittel über den Loop, Rotationen je Gelenk, Abweichung 1,2 mm), Schwanz-Pendeln auf 45 % und Spitzenzucken auf 40 % (der hängende Schwanz hat den längeren Hebel), Ohren-Grundwinkel 9° nach hinten (in Blender gemessen), leichter Wind in den Haaren (im Spielmodus gemessen: ca. 6 bis 7° stetig, Böen bis ca. 12°, zwei Böen alle 12 s).
    - **Wieder machen für Gehen, Laufen, Sprinten:** `blender -b <Datei>.blend --python Blender/scripts/export_pose_v2.py -- Blender/Yoru_<Name>_v2_pose.json <Action>`, dann `python Blender/scripts/export_stream.py Blender/Yoru_<Name>_v2_pose.json Tools/AnimStreams/Yoru_<Name>.json Yoru_<Name> 1`, dann in Unity nur `ZeroProtocol.EditorTools.YoruClipBaker.Bake("Tools/AnimStreams/Yoru_<Name>.json")` (nicht BakeAll). Vergleich mit `Blender/scripts/dump_bonepos.py`. Unity wird über `Tools/umcp.py` gesteuert.
    - **Augen:** In Unity wirkt die Iris violett, die helle Iris war ein Effekt der Blender-Vorschau. Keine Modelländerung nötig.
  - **Gehen, Runden 1 und 2 (23.10.):** Runde 1 (drei fast gleiche Swagger-Varianten) lehnte der Nutzer ab („schlechter als das alte, ich sehe keinen Unterschied“). Das alte Gehen (Blender/Yoru_Walk.blend, in Unity) fand er „nicht schlecht“: Der Neubau soll besser sein als das alte (N, „immer von Anfang an richtig geil“). Runde 2 (Alt, Neu, Neu+): „das alte schaut besser aus, nur die **Ellbogen sind gerade und sehen komisch aus**, und die **Geschwindigkeit ist komisch**“ (N). Folgen: Ellbogen deutlich gebeugt (Hände auf Bauch- bis Hüfthöhe, kompakt, wie im Leitfaden), drei Tempi zum Vergleichen, Knie darf nach dem Aufsetzen nicht tiefer einsacken als beim alten Gehen.
  - **Gehen, Runde 3 (23.10.):** Der Nutzer wählt als Tempo den **Mittelweg 0,83 s pro Doppelschritt, ca. 1,35 m/s** (N; ersetzt die früheren 0,95 s). Die Arme (Ellbogen gebeugt, Hände vor der Hüfte) gefallen ihm noch nicht: „die Arme sollen viel eleganter sein, es sieht immer noch robotermäßig aus“ (N). Runde 4 baut die Arme organisch und elegant (Nachziehen von Schulter über Ellbogen und Handgelenk bis zu den Fingern, Bögen statt Pendel, Handgelenkspiel).
  - **Neue Richtung (23.10., nach den Gehen-Runden 1 bis 4):** Der Nutzer sagt, alles bisherige „schaut Arsch aus“ (N), und liefert Bildschirmaufnahmen aus NTE (Downloads/NTE recording): „das ist, wenn ich **W** drücke, das will ich bauen, nicht diesen langsamen Walk“ (N). Die Hauptbewegung auf **W** ist also der **NTE-Lauf**: Doppelschritt 20 Bilder = 0,667 s (180 Schritte pro Minute), Oberkörper ca. 25° nach vorn, Ellbogen ca. 90° gebeugt und eng am Körper, Arme pendeln aus der Schulter und ziehen nach, lockere Faust, Schwungbein klappt bis zum Gesäß hoch, Geschwindigkeit grob 4,5 bis 5 m/s. Das langsame Gehen (0,83 s) ruht, die Ergebnisse bleiben in `Blender/work/Walk_v2/`. Vorgehen: der Agent vergleicht seine Bewegung **Bild für Bild** mit den NTE-Bildern (lokal in `Blender/previews/ref_nte/`, nicht im Repository), nah dran, aber auf Yoru angepasst (schmal, Arme eng, Gear, Schwanz, Gesicht B). Gehen, Joggen und Idle aus NTE reicht der Nutzer eventuell nach.
  - **Special Idle (vorgemerkt, nicht Teil der vier Bewegungen):** Hände vorn, die linke hält das rechte Handgelenk (N).
  - **Messregel für Arme (aus Idle Runde 2):** Der Abstand der Arme zum Gear muss gegen das echte Netz gemessen werden, nicht gegen die Gelenke. Die Unterarme steckten in der ersten Fassung 0,7 bis 2,2 cm im Gürtel. Das gilt auch für Gehen, Laufen und Sprinten.
- **Richtung (20.10.):** Third-Person-Shooter mit Schulterkamera, Doppelpistolen, Deckung, Lock-On auf den Körper (ohne Fadenkreuz). Zeitlupe als begrenzte Fähigkeit. Zuerst Schießen, dann Nahkampf und Stealth. (N)
- Als Nächstes zu bauen: Zielhaltung, Strafe, Schießen, Nachladen, Deckung, dazu Ausweichen und Dash-Varianten. Referenzen: `Docs/Animations_Referenzen.md`.

## Entscheidungsregel für Rückfragen
1. Erst hier nachsehen und selbst entscheiden, mit kurzer Begründung („passt zu ihr, weil …“).
2. Echte Geschmacksfragen mit Bildern oder konkreten Optionen im Auswahl-Fenster stellen, nicht als Textliste.
3. Nach der Antwort dieses Dokument ergänzen, damit dieselbe Frage nie zweimal kommt.
