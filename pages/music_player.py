import streamlit.components.v1 as components
import base64
from pathlib import Path

_MP3_NAME = "solarflex-soft-background-music-515502.mp3"
_here = Path(__file__).parent
_MUSIC_FILE = next(
    (p for p in [_here / _MP3_NAME, _here.parent / _MP3_NAME] if p.exists()),
    _here / _MP3_NAME  # fallback (will fail silently below)
)
_cached_b64: str | None = None

def _get_b64() -> str:
    global _cached_b64
    if _cached_b64 is None and _MUSIC_FILE.exists():
        _cached_b64 = base64.b64encode(_MUSIC_FILE.read_bytes()).decode()
    return _cached_b64 or ""

# Phases where music should play
MUSIC_PHASES = {"lobby", "between", "ended"}

def inject_music(phase: str, volume: int = 50):
    """
    Inject an invisible audio player into the page.
    - phase: current game phase string
    - volume: 0–100 integer from the settings slider
    """
    should_play = phase in MUSIC_PHASES
    b64 = _get_b64()
    if not b64:
        return  # file not found — fail silently

    vol = max(0.0, min(1.0, volume / 100))
    fade_duration = 1.3  # seconds

    components.html(f"""
    <audio id="mm-bg-audio" loop preload="auto"
           src="data:audio/mpeg;base64,{b64}"
           style="display:none"></audio>
    <script>
    (function() {{
      var audio = document.getElementById('mm-bg-audio');
      if (!audio) return;
      var targetVol = {vol:.3f};
      var shouldPlay = {'true' if should_play else 'false'};
      var fadeDur = {fade_duration * 1000:.0f}; // ms
      var steps = 30;
      var interval = fadeDur / steps;

      function fadeIn() {{
        audio.volume = 0;
        if (audio.paused) audio.play().catch(function(){{}});
        var step = 0;
        var t = setInterval(function() {{
          step++;
          audio.volume = Math.min(targetVol, (step / steps) * targetVol);
          if (step >= steps) clearInterval(t);
        }}, interval);
      }}

      function fadeOut(cb) {{
        var startVol = audio.volume;
        var step = 0;
        var t = setInterval(function() {{
          step++;
          audio.volume = Math.max(0, startVol * (1 - step / steps));
          if (step >= steps) {{ clearInterval(t); if (cb) cb(); }}
        }}, interval);
      }}

      // Sync volume without fade if already playing at right vol
      function syncVolume() {{
        if (!audio.paused) audio.volume = targetVol;
      }}

      if (shouldPlay) {{
        if (audio.paused) {{
          fadeIn();
        }} else {{
          syncVolume();
        }}
      }} else {{
        if (!audio.paused) {{
          fadeOut(function() {{ audio.pause(); audio.currentTime = 0; }});
        }}
      }}
    }})();
    </script>
    """, height=0)
