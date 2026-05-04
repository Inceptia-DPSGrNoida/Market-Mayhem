"""
music_player.py — Background music for Market Mayhem
Injects a persistent <audio> element into the parent Streamlit page.
Music plays only during: lobby, between (break), ended (thank-you).
Fades in/out over 1.3 seconds.
Place this file and the .mp3 in the same folder (root or pages/).
"""

import base64, streamlit.components.v1 as components
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
        return  # MP3 not found — fail silently

    should_play = phase in MUSIC_PHASES
    vol = max(0.0, min(1.0, volume / 100))

    components.html(f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;overflow:hidden;background:transparent">
<script>
(function() {{
  var P   = window.parent.document;
  var vol = {vol:.3f};
  var shouldPlay = {'true' if should_play else 'false'};
  var FADE = 1300;
  var STEPS = 40;
  var INTERVAL = FADE / STEPS;

  function fadeIn(audio) {{
    audio.volume = 0;
    if (audio.paused) audio.play().catch(function(){{}});
    var step = 0;
    var t = setInterval(function() {{
      step++;
      audio.volume = Math.min(vol, (step / STEPS) * vol);
      if (step >= STEPS) {{ audio.volume = vol; clearInterval(t); }}
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

  function setupAudio() {{
    var audio = P.getElementById('mm-bg-audio');

    if (!audio) {{
      audio = P.createElement('audio');
      audio.id  = 'mm-bg-audio';
      audio.loop = true;
      audio.preload = 'auto';
      audio.volume  = 0;
      var src = P.createElement('source');
      src.src  = 'data:audio/mpeg;base64,{b64}';
      src.type = 'audio/mpeg';
      audio.appendChild(src);
      P.body.appendChild(audio);
    }}

    if (shouldPlay) {{
      if (audio.paused) {{
        fadeIn(audio);
      }} else {{
        audio.volume = vol;
      }}
    }} else {{
      if (!audio.paused) {{
        fadeOut(audio, function() {{ audio.pause(); }});
      }}
    }}
  }}

  try {{
    setupAudio();
  }} catch(e) {{
    setTimeout(setupAudio, 300);
  }}
}})();
</script>
</body></html>""", height=1)
