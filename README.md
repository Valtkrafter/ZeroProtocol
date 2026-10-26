# Zero Protocol

> **Arbeitstitel.** Vor einer kommerziellen Veröffentlichung wird ein eigener Titel gewählt, da 2024 bereits ein gleichnamiges Horror-Spiel erschienen ist.

**Version:** <!-- version -->0.0.2<!-- /version --> · [Releases](https://github.com/Valtkrafter/ZeroProtocol/releases) · [Changelog](CHANGELOG.md) · [Versionsregeln](Docs/VERSIONING.md)

---

## 1. High Concept & Genre

**Zero Protocol** ist ein stilvoller, düsterer **Third-Person Tactical Shooter mit Gun-Fu-Fokus** in einer dystopischen Sci-Fi-Zukunftsstadt. 

Das Spiel verbindet das messerscharfe, unaufhaltsame Auftreten von *John Wick* und *The Eminence in Shadow* mit der taktischen Ästhetik von *Arknights: Endfield* und der visuellen Brillanz moderner Anime-Actionspiele:
* **Kampffokus:** Schnelle, präzise Schusswechsel aus der Schulterperspektive (Over-the-Shoulder), Doppelpistolen, Rutsch- und Ausweichmanöver, begrenzte Bullet Time (Zeitlupe) und brutales Nahkampf-Gun-Fu. Kein träger Deckungsshooter, sondern hochdynamische, akrobatische Gefechte.
* **Tonalität:** Ernst, atmosphärisch, düster und kompromisslos. Keine albernen Slapstick-Elemente oder kitschige Klischees.
* **Audio-Signatur:** Klassische Musik – insbesondere Ludwig van Beethoven (**Mondscheinsonate**) –, die die Protagonistin während ihrer Einsätze über ein Ohr-Implantat hört, um ihren Puls im Kugelhagel absolut ruhig zu halten.

---

## 2. Welt & Story-Lore

### Die Katastrophe: Der Chronos-Sturm
Vor Jahren riss ein unnatürliches Phänomen den Himmel auf: das **„Schwarze Gewitter“**. Ein ununterbrochener Sturm aus violetter Strahlung und atmosphärischer Entropie, der die Außenwelt unbewohnbar machte. Wer dem Niederschlag ungeschützt ausgesetzt ist, dessen Zellen zersetzen sich im Rekordtempo.

### Das Zonen-System & die Serum-Währung
Die verbliebene vertikale Megacity ist in hermetisch abgeriegelte Ringe unterteilt:
* **Ring 0 / Der Abgrund (Slums & Ruinen):** Die Heimat der Ausgestoßenen, Gesetzlosen und Schmuggler. Hier regiert das nackte Überleben.
* **Mittlere Sektoren:** Industrie, Frondienst und kontrollierte Kasernen.
* **Sektor 1 / Der Kern (Sanctum):** Wolkenkratzer über der Wolkendecke, in denen die korrupte Elite und Konzernlenker in unendlichem Luxus leben.

**Das Stasis-Serum:**  
Um in den vergifteten Zonen zu überleben, benötigt jeder Mensch regelmäßige Dosen von stabilisierendem Serum.
* In den Slums gibt es nur minderwertiges, gestrecktes Serum (*„Sludge“*), das wie Säure in den Adern brennt und den Verfall nur um wenige Tage aufschiebt.
* Die Eliten im Zentrum horten reinstes Serum, das sie praktisch unsterblich macht.
* **Die Bedrohung (Körperhorror):** Sinkt die Zell-Stabilität eines Menschen auf 0 %, stirbt er nicht einfach – er mutiert in einem schmerzhaften Prozess zu den **„Hollows“** (agile, knöcherne Schattenbestien), die Jagd auf das Serum im Blut lebender Menschen machen.

### Das „Zero Protocol“ & der Verrat
Als die Katastrophe außer Kontrolle geriet, aktivierten die Konzerne das **Zero Protocol**: Ein geheimes Säuberungs- und Abriegelungsdekret. Die regulären Streitkräfte und alle unteren Distrikte wurden als lebender Puffer geopfert und eingekesselt, um den Rückzug der Eliten zu sichern. 

Die Spezialeinheit der Protagonistin wurde vorsätzlich ausgelöscht. Ihr Kommandant brannte jedoch in seinen letzten Atemzügen den Master-Schlüssel des Protokolls in ihr System.

---

## 3. Die Protagonistin: Shirogane Yoru

* **Design:** Zierliche, aber durchtrainierte Spezialagentin. Silber-lila Haare, feine Katzenohren und Katzenschwanz (Resultat militärischer Gen-Optimierung für gesteigerte Reflexe und Sinne), kühle violette Augen.
* **Kleidung:** Mattschwarzes Taktik-Outfit, enge Weste, Schulterpolster, Oberschenkel-Holster für Doppelpistolen, taktische Beintaschen.
* **Persönlichkeit:** Souverän, extrem kontrolliert, unbeeindruckt, fokussiert. Sie verkörpert pure Badass-Attitüde („Swagger Walk“), ist weiblich und geschmeidig, aber absolut tödlich. **Kein Neko-Kawaii, kein Niedlichkeitsgehabe.**
* **Ihr Status (Die Anomalie):** Durch das überlebte Zero Protocol hat ihr Körper eine permanente Immunität entwickelt. Während die gesamte Stadt vom Serum versklavt wird, steht ihr Bio-Wert auf `[STATUS: ANOMALIE]`. Sie kann weder erpresst noch infiziert werden.
* **Ihr Ziel:** Sie ist keine barmherzige Retterin. Sie wandert von Zone zu Zone, um das Zero Protocol zu vollenden: die Zerschlagung der Barrieren und die bedingungslose Vernichtung der Eliten an der Spitze der Stadt.

Das vollständige filmische Intro und Drehbuch zur Einstiegsszene ist dokumentiert in [Docs/Drehbuch_Prolog.md](Docs/Drehbuch_Prolog.md).

---

## 4. Aktueller technischer Status (Alpha)

Das Projekt befindet sich in der aktiven Alpha-Entwicklung (**v0.0.2**).

* **Test-Arena:** Flaches Testgelände mit modularen Hindernissen (`Assets/Scenes/Arena.unity`).
* **Bewegungssystem:**
  * Gehen (1,5 m/s), Sprint (5,0 m/s), Ausweichen per Shift-Tipp, Sprung.
  * Third-Person-Kamera mit dynamischem Lock-On-System und verstellbarem Sichtfeld beim Sprint.
  * Aktuell arbeitet Claude (Subagent `yoru-animator`) an der Feinabstimmung der Locomotion-Zyklen in Blender (orientiert an den schnellen Laufphasen aus *NTE*).
* **Sekundärphysik:**
  * Haar-, Schwanz-, Ohren- und Brustphysik über Spring Bones (UniVRM).
  * Gesichts-Controller für subtile Mimik (`YoruFaceExpression.cs`) und dynamisches Blinzeln.
* **Grafik & Post-Processing:**
  * Unity 6 (6000.3.25f1) mit Universal Render Pipeline (URP 17.3).
  * Post-Processing-Volume mit justierbarem Motion-Blur-Regler (Esc öffnet Menü, F10 pinnt es).
  * Geplant: Toon-Shader (lilToon oder MToon-URP) mit dezentem Outline-Rendering und PBR-Materialien für taktische Ausrüstung (siehe [Docs/Grafik_Plan.md](Docs/Grafik_Plan.md)).

---

## 5. Steuerung (PC / Tastatur & Maus)

| Taste | Aktion |
|---|---|
| **W / A / S / D** | Gehen / Laufen |
| **Shift (halten)** | Sprint (5,0 m/s mit dynamischer Kamera) |
| **Shift (tippen)** | Ausweichen (Dodge / Dash) |
| **Leertaste** | Springen |
| **Maus** | Kamera drehen |
| **Mausrad (Klick)** | Lock-On auf Ziel aufschalten |
| **Mausrad (Drehen)** | Kamera-Zoom |
| **Esc** | Mauszeiger freigeben / Einstellungs-Panel öffnen (Motion Blur) |
| **F10** | Einstellungs-Panel auf dem Bildschirm fixieren |

---

## 6. Projektstruktur

* `Assets/Scenes/Arena.unity`: Haupt-Test-Arena für Gameplay, Physik und Rendering.
* `Assets/Scripts/Player/`: Controller, Movement, Lock-On, Blinzeln und Gesichts-Mimik.
* `Assets/Scripts/Camera/`: Third-Person-Cinemachine-Steuerung und Lock-On-Kamera.
* `Assets/Scripts/Settings/`: Post-Processing- und Grafikeinstellungen.
* `Assets/Editor/`: Editor-Werkzeuge (z. B. `ArenaBuilder.cs`, Animator-Tools).
* `Blender/`: Blender-Dateien (`.blend`), Generierungsskripte für Bewegungszyklen und Pose-Streams.
* `Docs/`:
  * `Charakter_Yoru.md`: Verbindlicher Leitfaden zu Posen, Attitüde und Bewegungsregeln.
  * `Drehbuch_Prolog.md`: Vollständiges Drehbuch für das filmische Intro und den Einstiegskampf.
  * `Grafik_Plan.md`: Schrittweiser Fahrplan für Toon-Shader, Beleuchtung und Post-Processing.
  * `Animations_Referenzen.md`: Messwerte und Vergleiche (NTE, WuWa, Genshin, Endfield).
  * `VERSIONING.md`: Regeln für Semantic Versioning und Releases.
* `Tools/`: Python-Werkzeuge für Release-Builds (`release.py`), Animator-Bakes und MCP-Unity-Bridge.

---

## 7. Setup & Erste Schritte

1. Projekt in **Unity 6 (6000.3.25f1)** öffnen.
2. In der oberen Menüleiste den Befehl `Zero Protocol > Build Test Arena` ausführen (initialisiert die Arena mit Yoru, Licht und Kamera).
3. Die Szene `Assets/Scenes/Arena.unity` laden und **Play** drücken.
4. Fertige Test-Builds stehen unter [Releases](https://github.com/Valtkrafter/ZeroProtocol/releases) zur Verfügung. ZIP-Datei vollständig entpacken und `ZeroProtocol.exe` starten.

---

## 8. Lizenz & Rechte

Alle Rechte vorbehalten. Das 3D-Modell der Protagonistin und zugehörige Assets sind derzeit ausschließlich für Entwicklungs- und Testzwecke freigegeben und vor einer offiziellen Freigabe nicht für kommerzielle Zwecke lizenziert.
