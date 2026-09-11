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


def _noise_pop(ms: int = 40, vol: float = 0.22) -> list[int]:
    """짧은 화이트노이즈 팝. 상용 샘플이 아니라 난수로 만든다."""
    n = max(1, int(RATE * ms / 1000))
    fade = max(1, int(RATE * 0.004))
    frames: list[int] = []
    seed = 1234567
    for i in range(n):
        seed = (1103515245 * seed + 12345) & 0x7FFFFFFF
        raw = (seed / 0x7FFFFFFF) * 2 - 1
        env = 1.0
        if i < fade:
            env = i / fade
        elif i > n - fade:
            env = (n - i) / fade
        frames.append(int(max(-1, min(1, vol * env * raw)) * 32767))
    return frames


def _fanfare(notes: list[tuple[float, int]], vol: float = 0.4) -> bytes:
    """콤보·승리용. 노이즈 팝 + 배음 종소리."""
    frames = _noise_pop(36, 0.18)
    frames.extend(_chime_samples(notes, vol))
    return _wav(frames)


@st.cache_data
def _clip(kind: str) -> bytes:
    if kind == "tick":
        return _tone([(980, 90)], 0.40)
    if kind == "pick":
        return _tone([(760, 55)], 0.38)
    if kind in ("submit", "ok"):
        return _chime([(659, 70), (880, 130)], 0.38)
    if kind == "combo2":
        return _fanfare([(698, 55), (880, 70), (1047, 150)], 0.42)
    if kind == "combo3":
        return _fanfare([(523, 45), (659, 50), (784, 55), (1047, 90), (1319, 170)], 0.44)
    if kind == "combo5":
        return _fanfare(
            [(392, 40), (523, 40), (659, 45), (784, 50), (988, 55), (1175, 70), (1568, 200)],
            0.46,
        )
    if kind == "combo8":
        return _fanfare(
            [
                (330, 35),
                (392, 35),
                (523, 40),
                (659, 40),
                (784, 45),
                (988, 50),
                (1175, 55),
                (1319, 60),
                (1760, 220),
            ],
            0.48,
        )
    if kind == "miss":
        return _tone([(520, 120), (390, 180)], 0.42)
    if kind == "go":
        return _tone([(523, 100), (784, 180)], 0.40)
    if kind == "done":
        return _chime([(523, 100), (659, 170)], 0.38)
    if kind == "win":
        return _fanfare([(523, 80), (659, 80), (784, 90), (1047, 220)], 0.46)
    if kind == "lose":
        return _tone([(440, 160), (349, 220)], 0.36)
    if kind == "draw":
        return _chime([(523, 100), (523, 140)], 0.34)
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


def flash_fx(ok: bool, streak: int, token: str) -> None:
    """정답·콤보 화면 이펙트. 겉창(body)에 붙여 Streamlit 칸·iframe에서도 보이게 한다."""
    if st.session_state.get("_fx_token") == token:
        return
    st.session_state._fx_token = token
    n = max(0, int(streak or 0))
    if ok:
        title = f"{n}연속!" if n >= 2 else "정답!"
        if n >= 8:
            note = "대폭발 콤보"
            tier = "big"
        elif n >= 5:
            note = "콤보가 터졌습니다"
            tier = "big"
        elif n >= 3:
            note = "연속 정답"
            tier = "hot"
        elif n >= 2:
            note = "콤보 시작"
            tier = "hot"
        else:
            note = "맞혔습니다"
            tier = "ok"
    else:
        title = "아쉽"
        note = "다음 문항에서 다시"
        tier = "miss"
    burst_n = 0 if not ok else (10 if n < 2 else (14 if n < 5 else (18 if n < 8 else 26)))
    components.html(
        f"""
<div id="tb-fx-seed" style="display:none"></div>
<script>
(function () {{
  var ok = {str(ok).lower()};
  var tier = {tier!r};
  var title = {title!r};
  var note = {note!r};
  var burstN = {burst_n};
  function host() {{
    try {{ if (window.top && window.top.document && window.top.document.body) return window.top; }} catch (e) {{}}
    try {{ if (window.parent && window.parent.document && window.parent.document.body) return window.parent; }} catch (e) {{}}
    return window;
  }}
  var w = host();
  var doc = w.document;
  try {{
    var old = doc.getElementById("tb-fx-layer");
    if (old && old.parentNode) old.parentNode.removeChild(old);
  }} catch (e) {{}}
  var style = doc.getElementById("tb-fx-style");
  if (!style) {{
    style = doc.createElement("style");
    style.id = "tb-fx-style";
    style.textContent = `
#tb-fx-layer {{position:fixed; inset:0; z-index:2147483000; pointer-events:none; overflow:hidden;
  font-family:Pretendard,Malgun Gothic,sans-serif;}}
#tb-fx-layer .tb-flash {{position:absolute; inset:0; opacity:0;
  background:radial-gradient(ellipse at 50% 30%, rgba(34,197,94,.45), rgba(34,197,94,.08) 42%, transparent 68%);
  animation:tbFlash 1.15s ease-out forwards;}}
#tb-fx-layer.hot .tb-flash {{background:radial-gradient(ellipse at 50% 28%, rgba(255,196,72,.55), rgba(226,85,61,.18) 40%, transparent 68%);}}
#tb-fx-layer.big .tb-flash {{background:radial-gradient(ellipse at 50% 26%, rgba(255,230,140,.62), rgba(226,85,61,.22) 38%, transparent 70%);}}
#tb-fx-layer.miss .tb-flash {{background:radial-gradient(ellipse at 50% 32%, rgba(192,57,43,.28), transparent 62%);}}
#tb-fx-layer .tb-pop {{position:absolute; left:50%; top:28%; transform:translate(-50%,-50%); text-align:center;
  animation:tbPop 1.35s ease-out forwards;}}
#tb-fx-layer .tb-pop b {{display:block; font-size:clamp(2.2rem, 8vw, 3.4rem); font-weight:800; color:#fff;
  letter-spacing:-.03em; text-shadow:0 8px 28px rgba(0,0,0,.45), 0 0 24px rgba(34,197,94,.55);}}
#tb-fx-layer.hot .tb-pop b, #tb-fx-layer.big .tb-pop b {{color:#ffe7a3; text-shadow:0 8px 28px rgba(0,0,0,.5), 0 0 28px rgba(255,196,72,.7);
  animation:tbShake .5s ease-out;}}
#tb-fx-layer.miss .tb-pop b {{color:#f3d0cc; font-size:clamp(1.6rem, 6vw, 2.2rem); text-shadow:0 6px 18px rgba(0,0,0,.4);}}
#tb-fx-layer .tb-pop span {{display:block; margin-top:6px; color:#f7ecd0; font-weight:700;
  font-size:clamp(1rem, 3.6vw, 1.2rem); text-shadow:0 2px 10px rgba(0,0,0,.35);}}
#tb-fx-layer .tb-ring {{position:absolute; left:50%; top:28%; width:28px; height:28px; border-radius:50%;
  border:3px solid rgba(255,220,100,.95); transform:translate(-50%,-50%);
  animation:tbRing 1.05s ease-out forwards;}}
#tb-fx-layer .tb-ring.r2 {{animation-delay:.08s; border-color:rgba(255,255,255,.55);}}
#tb-fx-layer .tb-ring.r3 {{animation-delay:.16s; border-color:rgba(255,160,80,.7);}}
#tb-fx-layer .tb-spark, #tb-fx-layer .tb-burst i {{position:absolute; left:50%; top:28%; width:10px; height:10px;
  margin:-5px 0 0 -5px; border-radius:50%; background:#ffd978; box-shadow:0 0 12px rgba(255,200,80,.9);}}
#tb-fx-layer .tb-spark {{animation:tbSpark 1s ease-out forwards;}}
#tb-fx-layer .tb-burst i {{animation:tbBurst .95s ease-out forwards;}}
#tb-fx-layer .tb-burst i:nth-child(odd) {{background:#fff; width:7px; height:7px;}}
#tb-fx-layer .tb-burst i:nth-child(3n) {{background:#e2553d;}}
@keyframes tbFlash {{0%{{opacity:1;}} 100%{{opacity:0;}}}}
@keyframes tbPop {{0%{{opacity:0; transform:translate(-50%,-40%) scale(.55);}}
  18%{{opacity:1; transform:translate(-50%,-50%) scale(1.12);}}
  70%{{opacity:1;}} 100%{{opacity:0; transform:translate(-50%,-64%) scale(1);}}}}
@keyframes tbRing {{0%{{opacity:1; width:24px; height:24px;}} 100%{{opacity:0; width:320px; height:320px;}}}}
@keyframes tbSpark {{0%{{opacity:1; transform:translate(0,0) scale(1);}}
  100%{{opacity:0; transform:translate(var(--dx), var(--dy)) scale(.2);}}}}
@keyframes tbBurst {{0%{{opacity:1; transform:rotate(var(--rot)) translate(0,0) scale(1);}}
  100%{{opacity:0; transform:rotate(var(--rot)) translate(var(--dx), var(--dy)) scale(.15);}}}}
@keyframes tbShake {{0%{{transform:translateX(0);}} 25%{{transform:translateX(-5px) rotate(-1.5deg);}}
  50%{{transform:translateX(5px) rotate(1.5deg);}} 100%{{transform:translateX(0);}}}}
`;
    try {{ (doc.head || doc.documentElement).appendChild(style); }} catch (e) {{}}
  }}
  var layer = doc.createElement("div");
  layer.id = "tb-fx-layer";
  layer.className = tier;
  var html = '<div class="tb-flash"></div>';
  if (ok) {{
    html += '<i class="tb-ring"></i>';
    if (tier === "hot" || tier === "big") html += '<i class="tb-ring r2"></i>';
    if (tier === "big") html += '<i class="tb-ring r3"></i>';
    [[-80,-40],[85,-50],[0,-85],[-60,55],[70,60],[-95,10],[95,15]].forEach(function (p) {{
      html += '<i class="tb-spark" style="--dx:' + p[0] + 'px;--dy:' + p[1] + 'px"></i>';
    }});
    if (burstN > 0) {{
      html += '<span class="tb-burst">';
      for (var i = 0; i < burstN; i++) {{
        var ang = (360 / burstN) * i;
        var dist = 78 + (i % 5) * 20;
        var rad = ang * Math.PI / 180;
        var dx = Math.round(dist * Math.cos(rad));
        var dy = Math.round(dist * Math.sin(rad));
        html += '<i style="--dx:' + dx + 'px;--dy:' + dy + 'px;--rot:' + ang + 'deg"></i>';
      }}
      html += '</span>';
    }}
  }}
  html += '<div class="tb-pop"><b></b><span></span></div>';
  layer.innerHTML = html;
  layer.querySelector(".tb-pop b").textContent = title;
  layer.querySelector(".tb-pop span").textContent = note;
  try {{ doc.body.appendChild(layer); }} catch (e) {{ return; }}
  setTimeout(function () {{
    try {{ if (layer.parentNode) layer.parentNode.removeChild(layer); }} catch (e) {{}}
  }}, 1500);
}})();
</script>
""",
        height=0,
        width=0,
    )


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
