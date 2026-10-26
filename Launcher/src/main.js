// Zero Protocol Launcher Controller

// 0. Live Cloud Auto-Sync (Loads updates from GitHub Pages automatically)
async function checkLiveWebUpdate() {
  if (window.location.hostname.includes('github.io')) {
    return;
  }
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 1800);
    const res = await fetch('https://valtkrafter.github.io/ZeroProtocol/version.json', {
      cache: 'no-cache',
      signal: controller.signal
    });
    clearTimeout(timeoutId);
    if (res.ok) {
      const data = await res.json();
      if (data && data.url) {
        window.location.replace(data.url);
      }
    }
  } catch (err) {
    console.log('Running in local offline launcher mode.');
  }
}
checkLiveWebUpdate();

// 1. Robust Tauri IPC Helper
function invoke(cmd, args = {}) {
  try {
    if (window.__TAURI__ && window.__TAURI__.core && typeof window.__TAURI__.core.invoke === 'function') {
      return window.__TAURI__.core.invoke(cmd, args);
    }
    if (window.__TAURI__ && typeof window.__TAURI__.invoke === 'function') {
      return window.__TAURI__.invoke(cmd, args);
    }
  } catch (err) {
    console.error('Tauri invoke error:', err);
  }
  console.log(`[IPC fallback] ${cmd}`, args);
  return Promise.resolve();
}

function openExternal(url) {
  invoke('open_browser', { url });
}

// 2. Window Controls (Minimize & Close)
document.getElementById('btn-close')?.addEventListener('click', (e) => {
  e.preventDefault();
  invoke('close_launcher');
});

document.getElementById('btn-minimize')?.addEventListener('click', (e) => {
  e.preventDefault();
  invoke('minimize_launcher');
});

// 3. Action Buttons & Links
document.getElementById('btn-launch')?.addEventListener('click', (e) => {
  e.preventDefault();
  openExternal('https://github.com/Valtkrafter/ZeroProtocol/releases');
});

document.getElementById('link-github')?.addEventListener('click', (e) => {
  e.preventDefault();
  openExternal('https://github.com/Valtkrafter/ZeroProtocol/releases');
});

document.getElementById('link-repo')?.addEventListener('click', (e) => {
  e.preventDefault();
  openExternal('https://github.com/Valtkrafter/ZeroProtocol');
});

document.getElementById('link-build')?.addEventListener('click', (e) => {
  e.preventDefault();
  invoke('open_build_folder');
});

// 4. Tab Navigation (100% reliable click handling)
const tabButtons = document.querySelectorAll('.tab-btn');
const tabContents = document.querySelectorAll('.tab-content');

tabButtons.forEach(btn => {
  btn.addEventListener('click', function(e) {
    e.preventDefault();
    const targetId = this.getAttribute('data-tab');

    tabButtons.forEach(b => b.classList.remove('active'));
    tabContents.forEach(c => c.classList.remove('active'));

    this.classList.add('active');
    const targetContent = document.getElementById(targetId);
    if (targetContent) {
      targetContent.classList.add('active');
    }
  });
});

// 5. Ambient Cyberpunk Rain Animation
const canvas = document.getElementById('rain-canvas');
if (canvas) {
  const ctx = canvas.getContext('2d');
  let width, height;
  const drops = [];
  const dropCount = 80;

  function resizeCanvas() {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
  }
  window.addEventListener('resize', resizeCanvas);
  resizeCanvas();

  for (let i = 0; i < dropCount; i++) {
    drops.push({
      x: Math.random() * width,
      y: Math.random() * height,
      length: Math.random() * 20 + 10,
      speed: Math.random() * 7 + 8,
      opacity: Math.random() * 0.35 + 0.1
    });
  }

  function renderRain() {
    ctx.clearRect(0, 0, width, height);
    for (let i = 0; i < drops.length; i++) {
      const d = drops[i];
      ctx.beginPath();
      ctx.moveTo(d.x, d.y);
      ctx.lineTo(d.x - 1, d.y + d.length);
      ctx.strokeStyle = `rgba(157, 180, 255, ${d.opacity})`;
      ctx.lineWidth = 1.2;
      ctx.stroke();

      d.y += d.speed;
      d.x -= 0.5;

      if (d.y > height) {
        d.y = -d.length;
        d.x = Math.random() * width;
      }
    }
    requestAnimationFrame(renderRain);
  }
  renderRain();
}

// 6. Beethoven Moonlight Sonata Synthesizer (Web Audio API)
let audioCtx = null;
let isMusicPlaying = false;
let musicTimer = null;
let currentStep = 0;

const NOTES = {
  'C#2': 69.30, 'E2': 82.41, 'G#2': 103.83, 'A1': 55.00, 'B1': 61.74, 'C#1': 34.65,
  'G#3': 207.65, 'C#4': 277.18, 'E4': 329.63,
  'A3': 220.00, 'D4': 293.66, 'F#4': 369.99,
  'B3': 246.94, 'G#4': 415.30,
};

const sonataSequence = [
  { bass: 'C#2', arpeggio: ['G#3', 'C#4', 'E4'] },
  { bass: null,  arpeggio: ['G#3', 'C#4', 'E4'] },
  { bass: null,  arpeggio: ['G#3', 'C#4', 'E4'] },
  { bass: null,  arpeggio: ['G#3', 'C#4', 'E4'] },
  { bass: 'B1',  arpeggio: ['G#3', 'C#4', 'E4'] },
  { bass: null,  arpeggio: ['G#3', 'C#4', 'E4'] },
  { bass: null,  arpeggio: ['G#3', 'C#4', 'E4'] },
  { bass: null,  arpeggio: ['G#3', 'C#4', 'E4'] },
  { bass: 'A1',  arpeggio: ['A3', 'C#4', 'E4'] },
  { bass: null,  arpeggio: ['A3', 'C#4', 'E4'] },
  { bass: 'A1',  arpeggio: ['A3', 'D4',  'F#4'] },
  { bass: null,  arpeggio: ['A3', 'D4',  'F#4'] },
  { bass: 'G#2', arpeggio: ['G#3', 'C#4', 'E4'] },
  { bass: null,  arpeggio: ['G#3', 'C#4', 'E4'] },
  { bass: 'G#2', arpeggio: ['G#3', 'C#4', 'E4'] },
  { bass: null,  arpeggio: ['G#3', 'C#4', 'E4'] },
  { bass: 'C#2', arpeggio: ['G#3', 'C#4', 'E4'], melody: 'G#4' },
  { bass: null,  arpeggio: ['G#3', 'C#4', 'E4'] },
  { bass: null,  arpeggio: ['G#3', 'C#4', 'E4'] },
  { bass: null,  arpeggio: ['G#3', 'C#4', 'E4'], melody: 'G#4' },
];

function initAudio() {
  if (!audioCtx) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
  if (audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
}

function playPianoTone(freq, duration, gainLevel = 0.15) {
  if (!audioCtx) return;
  const now = audioCtx.currentTime;

  const osc = audioCtx.createOscillator();
  const oscHarmonic = audioCtx.createOscillator();
  const gain = audioCtx.createGain();

  osc.type = 'sine';
  osc.frequency.setValueAtTime(freq, now);

  oscHarmonic.type = 'triangle';
  oscHarmonic.frequency.setValueAtTime(freq * 2, now);

  gain.gain.setValueAtTime(0.0001, now);
  gain.gain.linearRampToValueAtTime(gainLevel, now + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + duration);

  const harmGain = audioCtx.createGain();
  harmGain.gain.setValueAtTime(gainLevel * 0.25, now);

  osc.connect(gain);
  oscHarmonic.connect(harmGain);
  harmGain.connect(gain);
  gain.connect(audioCtx.destination);

  osc.start(now);
  oscHarmonic.start(now);
  osc.stop(now + duration);
  oscHarmonic.stop(now + duration);
}

function playNextSonataBeat() {
  if (!isMusicPlaying) return;

  const step = sonataSequence[currentStep % sonataSequence.length];

  if (step.bass && NOTES[step.bass]) {
    playPianoTone(NOTES[step.bass], 3.2, 0.22);
  }

  const tripDelay = 0.22;
  step.arpeggio.forEach((noteName, idx) => {
    setTimeout(() => {
      if (isMusicPlaying && NOTES[noteName]) {
        playPianoTone(NOTES[noteName], 1.8, 0.08);
      }
    }, idx * tripDelay * 1000);
  });

  if (step.melody && NOTES[step.melody]) {
    playPianoTone(NOTES[step.melody], 2.8, 0.25);
  }

  currentStep++;
  musicTimer = setTimeout(playNextSonataBeat, tripDelay * 3 * 1000);
}

const btnAudio = document.getElementById('btn-audio');
btnAudio?.addEventListener('click', (e) => {
  e.preventDefault();
  initAudio();
  isMusicPlaying = !isMusicPlaying;

  if (isMusicPlaying) {
    btnAudio.classList.add('playing');
    playNextSonataBeat();
  } else {
    btnAudio.classList.remove('playing');
    clearTimeout(musicTimer);
  }
});

// 7. Live GitHub Commits Fetcher
async function fetchCommits() {
  const container = document.getElementById('commits-container');
  if (!container) return;

  try {
    const res = await fetch('https://api.github.com/repos/Valtkrafter/ZeroProtocol/commits?per_page=5', {
      headers: { 'Accept': 'application/vnd.github.v3+json' }
    });
    if (!res.ok) return;

    const data = await res.json();
    if (!Array.isArray(data) || data.length === 0) return;

    container.innerHTML = '';
    data.forEach(item => {
      const msg = (item.commit.message || '').split('\n')[0];
      const sha = item.sha ? item.sha.substring(0, 7) : '';
      let dateStr = '';
      if (item.commit.author && item.commit.author.date) {
        const d = new Date(item.commit.author.date);
        dateStr = d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' });
      }

      const el = document.createElement('div');
      el.className = 'commit-item';
      el.innerHTML = `
        <div class="commit-meta"><span class="sha">${sha}</span><span class="time">${dateStr}</span></div>
        <div class="msg">${msg}</div>
      `;
      el.addEventListener('click', () => {
        if (item.html_url) openExternal(item.html_url);
      });
      container.appendChild(el);
    });
  } catch (e) {
    console.log('GitHub fetch silent fallback:', e);
  }
}

document.getElementById('btn-refresh-commits')?.addEventListener('click', (e) => {
  e.preventDefault();
  fetchCommits();
});

fetchCommits();
