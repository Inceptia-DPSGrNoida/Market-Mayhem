"""
music_player.py — Background music for Market Mayhem
Strategy: serve the MP3 via st.audio (hidden), control play/pause via JS.
Music plays only during: lobby, between, ended phases.
1.3s fade in/out.
"""
import streamlit as st
import streamlit.components.v1 as components
import base64
from pathlib import Path
from functools import lru_cache

_MP3_NAME = "music.mp3"

@lru_cache(maxsize=1)
def _get_b64() -> str:
    here = Path(__file__).parent
    for p in [here / _MP3_NAME, here.parent / _MP3_NAME]:
        if p.exists():
            return base64.b64encode(p.read_bytes()).decode()
    return ""

MUSIC_PHASES = {"lobby", "between", "ended"}

def inject_music(phase: str, volume: int = 50):
    b64 = _get_b64()
    if not b64:
        return

    should_play = phase in MUSIC_PHASES
    vol = max(0.0, min(1.0, volume / 100))
    should_js  = "true" if should_play else "false"

    # Inject a real <audio> into the page via components.html (height=1 keeps iframe alive)
    # The audio src is a data URI so no server route needed
    components.html(f"""
<!DOCTYPE html><html>
<body style="margin:0;padding:0;background:transparent;overflow:hidden">
<script>
(function() {{
  var P = window.parent.document;
  var FADE = 1300, STEPS = 40, INTERVAL = FADE / STEPS;
  var targetVol = {vol:.3f};
  var shouldPlay = {should_js};

  function getAudio() {{
    return P.getElementById('mm-bg-audio');
  }}

  function createAudio() {{
    var a = P.createElement('audio');
    a.id = 'mm-bg-audio';
    a.loop = true;
    a.preload = 'auto';
    a.volume = 0;
    // Use blob URL to avoid CSP issues with data URIs
    var b64 = "{b64}";
    var binary = atob(b64);
    var bytes = new Uint8Array(binary.length);
    for (var i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    var blob = new Blob([bytes], {{type: 'audio/mpeg'}});
    a.src = URL.createObjectURL(blob);
    P.body.appendChild(a);
    return a;
  }}

  function fadeIn(audio) {{
    audio.volume = 0;
    audio.play().catch(function(e) {{
      // Autoplay blocked — add one-time click listener to parent
      P.addEventListener('click', function handler() {{
        audio.play().catch(function(){{}});
        P.removeEventListener('click', handler);
      }});
    }});
    var step = 0;
    var t = setInterval(function() {{
      step++;
      audio.volume = Math.min(targetVol, (step / STEPS) * targetVol);
      if (step >= STEPS) {{ audio.volume = targetVol; clearInterval(t); }}
    }}, INTERVAL);
  }}

  function fadeOut(audio, cb) {{
    var start = audio.volume;
    var step = 0;
    var t = setInterval(function() {{
      step++;
      audio.volume = Math.max(0, start * (1 - step / STEPS));
      if (step >= STEPS) {{ audio.volume = 0; clearInterval(t); if (cb) cb(); }}
    }}, INTERVAL);
  }}

  function sync() {{
    var audio = getAudio() || createAudio();

    if (shouldPlay) {{
      if (audio.paused) {{
        fadeIn(audio);
      }} else {{
        // Just update volume smoothly
        audio.volume = targetVol;
      }}
    }} else {{
      if (!audio.paused) {{
        fadeOut(audio, function() {{ audio.pause(); }});
      }}
    }}
  }}

  // Wait for parent DOM to be ready
  if (P.readyState === 'complete' || P.readyState === 'interactive') {{
    sync();
  }} else {{
    P.addEventListener('DOMContentLoaded', sync);
  }}
}})();
</script>
</body></html>
""", height=1)
