# Yoru – Charakter- und Bewegungs-Leitfaden

Für alle Posen, Animationen und Looks von **Shirogane Yoru** (Hauptfigur von Zero Protocol).
**Regel:** Bevor Claude etwas zu Posen, Positionen oder Look fragt, steht hier zuerst die Antwort. Gefragt wird nur, wenn es hier nicht steht oder echter Geschmack ist (dann mit 2–3 konkreten Bildern).
Das ist ein lebendiges Dokument: bitte korrigieren und ergänzen. **(N)** = hat der Nutzer so gesagt, **(A)** = Annahme von Claude, bitte prüfen.

## Wer sie ist
- **Spezialagentin, kein Neko-Kawaii.** (N, 14.10.)
- Silber-lila Haare, Katzenohren und Katzenschwanz, violette Augen, schwarzes taktisches Outfit mit Weste, Schulterpolstern, Oberschenkel-Holster und Taschen. (N)
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
- Roboterhaft steife Arme oder reine Sinus-Bewegungen.
- Stampfende, rhythmische Sprünge oder Wippen („tot, tot, tot“): wirkt leblos. Lieber ein ruhiger, durchgehender Fluss. (N, 16.10.)

## Bewegungs-Set (Stand 16.10.2026)
- **Gehen** 1,5 m/s: fertig und in Unity („Swagger“).
- **Run** 5 m/s: fertig und in Unity.
- **Dash:** in Arbeit. Wunsch des Nutzers:
  - Start aus Gehen **und** Run, kurzer Anlauf (ca. 0,3 s), etwas schneller als der Run.
  - Look wie bei WuWa / NTE / Genshin / Endfield **oder etwas Eigenes, das zu einer Agentin passt**.
  - **Gewählt (16.10.): „Gleitschritt“** = tiefer, langer Ausfallschritt, ruhiger Oberkörper, Hüfte leicht gedreht, beide Hände schützend an der Brust, die Füße gleiten über den Boden. Muss **richtig smooth** sein (N). Verworfen: Sprint-Schübe („nur ein schnellerer Lauf“) und Panther („tot tot tot“, stampfende Sprünge).
  - Danach: Taste gehalten, dann **Run**. Losgelassen, dann leichtes Joggen und zurück zum Gehen. (16.10.: Gleitschritt mit Joggen-Ausklang gebaut und vom Nutzer als „mega scheiße“ verworfen. Der Dash wird neu entworfen, Brief in `Docs/Moves/Dash.md`.)
  - Länge und Weite: so, dass es gut aussieht (Claude entscheidet, ca. 0,45 s und 5 m).
  - Kein bloß schnellerer Lauf: der Dash muss sich als eigener Move vom Run unterscheiden.
- Später: Ausweichen nach einem Angriff (Kampf), Dash-Varianten (Richtungen, Lock-on), Zielen und Schießen.
- **Verbesserungsplan aller Bewegungen** (nach 16 Referenz-Videos, 16.10.): `Docs/Animations_Plan.md`. Zuständig ist der Animations-Chef-Agent `animation-cao`.

## Entscheidungsregel für Rückfragen
1. Erst hier nachsehen und selbst entscheiden, mit kurzer Begründung („passt zu ihr, weil …“).
2. Echte Geschmacksfragen mit Bildern oder konkreten Optionen im Auswahl-Fenster stellen, nicht als Textliste.
3. Nach der Antwort dieses Dokument ergänzen, damit dieselbe Frage nie zweimal kommt.
