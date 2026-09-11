from __future__ import annotations

import base64
import io
import math
import struct
import wave
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

RATE = 22050
COUNT_LEN = 10


def _tone_samples(notes: list[tuple[float, int]], vol: float = 0.32) -> list[int]:
    frames: list[int] = []
    for freq, ms in notes:
        n = max(1, int(RATE * ms / 1000))
        fade = max(1, int(RATE * 0.008))
        for i in range(n):
            env = 1.0
            if i < fade:
                env = i / fade
            elif i > n - fade:
                env = (n - i) / fade
            sample = vol * env * math.sin(2 * math.pi * freq * i / RATE)
            frames.append(int(max(-1, min(1, sample)) * 32767))
        frames.extend([0] * int(RATE * 0.02))
    return frames


def _wav(samples: list[int]) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", s) for s in samples))
    return buf.getvalue()


def _tone(notes: list[tuple[float, int]], vol: float = 0.32) -> bytes:
    """짧은 사인파. 직접 만든 신호음이라 저작권 음원을 쓰지 않는다."""
    return _wav(_tone_samples(notes, vol))


def _chime_samples(notes: list[tuple[float, int]], vol: float = 0.3) -> list[int]:
    """배음만 섞은 짧은 종소리. 시중 효과음·게임음을 베끼지 않는다."""
    frames: list[int] = []
    for freq, ms in notes:
        n = max(1, int(RATE * ms / 1000))
        fade = max(1, int(RATE * 0.012))
        for i in range(n):
            env = 1.0
            if i < fade:
                env = i / fade
            elif i > n - fade:
                env = (n - i) / fade
            t = 2 * math.pi * i / RATE
            sample = vol * env * (
                math.sin(t * freq) * 0.70
                + math.sin(t * freq * 2) * 0.20
                + math.sin(t * freq * 3) * 0.10
            )
            frames.append(int(max(-1, min(1, sample)) * 32767))
        frames.extend([0] * int(RATE * 0.016))
    return frames


def _chime(notes: list[tuple[float, int]], vol: float = 0.3) -> bytes:
    return _wav(_chime_samples(notes, vol))


def _countdown_samples() -> list[int]:
    """0초에 10, 9초에 1, 10초에 시작음."""
    tick = _tone_samples([(980, 90)])
    go = _tone_samples([(523, 100), (784, 180)])
    total = int(RATE * (COUNT_LEN + 0.5))
    samples = [0] * total

    def blit(src: list[int], at_sec: float) -> None:
        start = int(at_sec * RATE)
        for i, v in enumerate(src):
            if start + i < len(samples):
                samples[start + i] = v

    for i in range(COUNT_LEN):
        blit(tick, float(i))
    blit(go, float(COUNT_LEN))
    return samples


@st.cache_data
def _clip(kind: str) -> bytes:
    if kind == "tick":
        return _tone([(980, 90)], 0.40)
    if kind == "pick":
        return _tone([(760, 55)], 0.38)
    if kind in ("submit", "ok"):
        return _chime([(659, 70), (880, 130)], 0.38)
    if kind == "combo2":
        return _chime([(659, 65), (784, 75), (988, 160)], 0.40)
    if kind == "combo3":
        return _chime([(523, 55), (659, 65), (784, 75), (1047, 190)], 0.42)
    if kind == "combo5":
        return _chime([(523, 50), (659, 50), (784, 55), (988, 70), (1175, 210)], 0.44)
    if kind == "combo8":
        return _chime([(392, 45), (523, 50), (659, 55), (784, 60), (988, 70), (1319, 230)], 0.46)
    if kind == "miss":
        # 저음은 폰 스피커에서 거의 안 들림 → 중고음·볼륨 보강
        return _tone([(520, 120), (390, 180)], 0.42)
    if kind == "go":
        return _tone([(523, 100), (784, 180)], 0.40)
    if kind == "done":
        return _chime([(523, 100), (659, 170)], 0.38)
    if kind == "count10":
        return _wav(_countdown_samples())
    if kind == "silent":
        return _wav([0] * int(RATE * 0.05))
    return _tone([(660, 80)], 0.38)


def _silent_b64() -> str:
    return base64.b64encode(_clip("silent")).decode("ascii")


def _play_js(b64: str, *, offset: float | None = None) -> str:
    """겉 창(top) Audio로 재생. iframe autoplay 차단·콘솔 에러를 줄인다."""
    off = "null" if offset is None else str(float(offset))
    silent = _silent_b64()
    return f"""
<script>
(function () {{
  function host() {{
    try {{ if (window.top && window.top.document) return window.top; }} catch (e) {{}}
    try {{ return window.parent; }} catch (e) {{}}
    return window;
  }}
  var w = host();
  try {{
    if (!w.__tbUnlockBound) {{
      w.__tbUnlockBound = true;
      var unlock = function () {{
        try {{
          var Ctx = w.AudioContext || w.webkitAudioContext;
          if (Ctx) {{
            w.__tbCtx = w.__tbCtx || new Ctx();
            if (w.__tbCtx.state === "suspended") w.__tbCtx.resume();
          }}
          var s = w.__tbSilent || new w.Audio("data:audio/wav;base64,{silent}");
          w.__tbSilent = s;
          s.volume = 0.01;
          var p = s.play();
          if (p && p.then) p.then(function () {{
            try {{ s.pause(); }} catch (e) {{}}
            w.__tbAudioReady = true;
          }}).catch(function () {{}});
        }} catch (e) {{}}
      }};
      w.document.addEventListener("touchstart", unlock, {{ capture: true, passive: true }});
      w.document.addEventListener("click", unlock, {{ capture: true, passive: true }});
    }}
  }} catch (e) {{}}
  function go() {{
    try {{
      var a = w.__tbSfx;
      if (!a) {{
        a = new w.Audio();
        w.__tbSfx = a;
      }}
      a.pause();
      a.src = "data:audio/wav;base64,{b64}";
      a.volume = 1;
      var start = function () {{
        try {{
          var off = {off};
          if (off !== null && !isNaN(off)) a.currentTime = off;
          else a.currentTime = 0;
        }} catch (e) {{}}
        var p = a.play();
        if (p && p.catch) p.catch(function () {{}});
      }};
      if (a.readyState >= 2) start();
      else {{
        a.addEventListener("loadeddata", start, {{ once: true }});
        a.addEventListener("canplaythrough", start, {{ once: true }});
        setTimeout(start, 40);
      }}
    }} catch (e) {{}}
  }}
  go();
}})();
</script>
"""


def arm_unlock() -> None:
    """앱 로드 시 한 번. 첫 터치로 소리를 풀어 둔다."""
    if st.session_state.get("_sfx_armed"):
        return
    st.session_state._sfx_armed = True
    components.html(_play_js(_silent_b64()), height=0, width=0)


def play(kind: str, token: str) -> None:
    if st.session_state.get("_sfx_token") == token:
        return
    st.session_state._sfx_token = token
    b64 = base64.b64encode(_clip(kind)).decode("ascii")
    components.html(_play_js(b64), height=0, width=0)


def countdown(play_at: str, token: str) -> None:
    """10부터 1까지 매 초 신호음, 0에 시작음."""
    if st.session_state.get("_sfx_token") == token:
        return
    st.session_state._sfx_token = token
    try:
        end_ms = int(datetime.fromisoformat(play_at).timestamp() * 1000)
    except Exception:
        return
    b64 = base64.b64encode(_clip("count10")).decode("ascii")
    left = max(0, math.ceil((end_ms - datetime.now().timestamp() * 1000) / 1000))
    offset = min(10, max(0, 10 - left))
    components.html(_play_js(b64, offset=float(offset)), height=0, width=0)
