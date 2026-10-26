// Bildaufnahme für Videoreferenzen mit dem eingebauten Browser (javascript_tool auf einer youtube.com-Seite).
//
// Warum so: Bilder per Seek (currentTime = t) können veraltet sein. Wenn der Seek zu lange dauert, zieht das Skript
// das alte Bild noch einmal. Dann sehen alle Bilder gleich aus und es wirkt, als gäbe es keine Bewegung.
// Diese Funktion nimmt die Bilder während des langsamen Abspielens auf (requestVideoFrameCallback). Jedes Bild ist
// das echte, gezeigte Bild zu seiner Zeit.
//
// Einrichten: zuerst die Hilfsfunktionen laden, z. B. mit eval(localStorage.getItem('__animref')) und __init(),
// oder diese Datei komplett einfügen. Danach die Funktion einmal definieren:
//   window.__cap2 = async (o) => { ... }   (unten)
//
// Aufruf:
//   const r = await __cap2({rows: [{crop: [fx, fy, fw, fh]}, ...], t0: 1.0, t1: 1.5, n: 8, cellW: 95, rate: 0.5});
//   rows:  eine Zeile pro Feld (bei geteilten Videos). Jede Zeile ist ein Ausschnitt des Bildes (Anteile 0..1).
//          Alle Zeilen nutzen dasselbe Bild.
//   t0, t1: Sekunden. n: Anzahl Bilder, gleichmäßig verteilt.
//   rate:  Abspielgeschwindigkeit. 0.5 liefert etwa jedes Videobild. Die echte Zeit ist (t1 - t0) / rate.
//          Die Aufnahme muss unter etwa 30 Sekunden bleiben, sonst bricht javascript_tool bei 45 s ab.
// Ergebnis: ein Bild oben links auf der Seite. Danach ein Screenshot. r.got zeigt die Zeiten der Bilder.
//
// Regeln:
//   - Für Bewegung: 8 bis 12 Bilder über EINEN Zyklus (Schritt ca. 0,5 s), nicht über das ganze Video.
//   - Für die Abschnitte eines langen Videos: grobe Übersicht mit rate 2 bis 3, dann das gewünschte Stück dicht aufnehmen.

window.__cap2 = async (o) => {
  const v = window.__vid(); window.__clear();
  const {rows, t0, t1, n = 8, cellW = 95, rate = 0.5} = o;
  const cellHs = rows.map(r => Math.round(cellW * (v.videoHeight * r.crop[3]) / (v.videoWidth * r.crop[2])));
  const offs = []; let acc = 0; for (const h of cellHs) { offs.push(acc); acc += h; }
  const c = document.createElement('canvas'); c.id = '__sheet'; c.width = n * cellW; c.height = acc;
  Object.assign(c.style, {position: 'fixed', left: '0', top: '0', zIndex: 2147483647, background: '#000', width: c.width + 'px', height: c.height + 'px'});
  const g = c.getContext('2d'); g.fillStyle = '#000'; g.fillRect(0, 0, c.width, c.height);
  document.body.appendChild(c);
  const targets = []; for (let i = 0; i < n; i++) targets.push(t0 + (t1 - t0) * i / (n - 1));
  v.muted = true; v.pause();
  await window.__seek(v, t0);
  let k = 0; const got = [];
  v.playbackRate = rate;
  await v.play();
  await new Promise(res => {
    const cb = (now, md) => {
      while (k < n && md.mediaTime >= targets[k] - 0.008) {
        const x = k * cellW;
        rows.forEach((r, ri) => {
          const sx = v.videoWidth * r.crop[0], sy = v.videoHeight * r.crop[1], sw = v.videoWidth * r.crop[2], sh = v.videoHeight * r.crop[3];
          g.drawImage(v, sx, sy, sw, sh, x, offs[ri], cellW, cellHs[ri]);
          g.strokeStyle = '#333'; g.strokeRect(x + 0.5, offs[ri] + 0.5, cellW - 1, cellHs[ri] - 1);
        });
        g.fillStyle = '#000'; g.fillRect(x, 0, 34, 13); g.fillStyle = '#ff0'; g.font = '11px sans-serif'; g.fillText(md.mediaTime.toFixed(2), x + 2, 10);
        got.push(+md.mediaTime.toFixed(3)); k++;
      }
      if (k < n && md.mediaTime <= t1 + 0.3 && !v.ended) v.requestVideoFrameCallback(cb); else res();
    };
    v.requestVideoFrameCallback(cb);
  });
  v.pause(); v.playbackRate = 1;
  return {got, canvas: [c.width, c.height]};
};
try { localStorage.setItem('__cap2src', window.__cap2.toString()); } catch (e) {}

// Rasterversion für größere Bilder: ein Ausschnitt (crop), die Bilder in cols Spalten und mehreren Zeilen (Bild k steht in Spalte k % cols).
// Die Screenshots der Browser-Fläche sind verkleinert (etwa Faktor 0,61). Ein Blatt bis ca. 1200 x 950 CSS-Pixel passt in einen Screenshot.
//   const r = await __cap3({crop: [fx, fy, fw, fh], t0: 0.2, t1: 7.2, n: 6, cols: 3, cellW: 400, rate: 0.5});
// Regeln: Der Browser-Bereich muss sichtbar sein (tabs_context meldet "displayed"). Ist er ausgeblendet, feuert
// requestVideoFrameCallback nicht, das Skript hängt und javascript_tool bricht nach 45 s ab.
// Vorher immer `await window.__init()` (nicht ohne await aufrufen, sonst pausiert es das Video mitten in der Aufnahme).
// Bei kurzen Clips (5 bis 8 s) vorher v.loop = true setzen, sonst springt YouTube nach dem Ende zum nächsten Video.
window.__cap3 = async (o) => {
  const v = window.__vid(); window.__clear();
  const {crop, t0, t1, n = 6, cols = 3, cellW = 250, rate = 0.5} = o;
  const cellH = Math.round(cellW * (v.videoHeight * crop[3]) / (v.videoWidth * crop[2]));
  const rowsN = Math.ceil(n / cols);
  const c = document.createElement('canvas'); c.id = '__sheet'; c.width = cols * cellW; c.height = rowsN * cellH;
  Object.assign(c.style, {position: 'fixed', left: '0', top: '0', zIndex: 2147483647, background: '#000', width: c.width + 'px', height: c.height + 'px'});
  const g = c.getContext('2d'); g.fillStyle = '#000'; g.fillRect(0, 0, c.width, c.height);
  document.body.appendChild(c);
  const targets = []; for (let i = 0; i < n; i++) targets.push(t0 + (t1 - t0) * i / (n - 1));
  v.muted = true; v.pause(); await window.__seek(v, t0);
  let k = 0; const got = []; v.playbackRate = rate; await v.play();
  await new Promise(res => {
    const cb = (now, md) => {
      while (k < n && md.mediaTime >= targets[k] - 0.008) {
        const x = (k % cols) * cellW, y = Math.floor(k / cols) * cellH;
        g.drawImage(v, v.videoWidth * crop[0], v.videoHeight * crop[1], v.videoWidth * crop[2], v.videoHeight * crop[3], x, y, cellW, cellH);
        g.strokeStyle = '#333'; g.strokeRect(x + 0.5, y + 0.5, cellW - 1, cellH - 1);
        g.fillStyle = '#000'; g.fillRect(x, y, 34, 13); g.fillStyle = '#ff0'; g.font = '11px sans-serif'; g.fillText(md.mediaTime.toFixed(2), x + 2, y + 10);
        got.push(+md.mediaTime.toFixed(3)); k++;
      }
      if (k < n && md.mediaTime <= t1 + 0.3 && !v.ended) v.requestVideoFrameCallback(cb); else res();
    };
    v.requestVideoFrameCallback(cb);
  });
  v.pause(); v.playbackRate = 1;
  return {got, canvas: [c.width, c.height]};
};
try { localStorage.setItem('__cap3src', window.__cap3.toString()); } catch (e) {}
