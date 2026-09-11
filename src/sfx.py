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
    """현재 창 Web Audio 재생. 공유 Audio pause를 쓰지 않아 소리가 덜 씹힌다."""
    off = "null" if offset is None else str(float(offset))
    silent = _silent_b64()
    return f"""
<script>
(function () {{
  var w = window;
  function unlock() {{
    try {{
      var Ctx = w.AudioContext || w.webkitAudioContext;
      if (Ctx) {{
        w.__tbCtx = w.__tbCtx || new Ctx();
        if (w.__tbCtx.state === "suspended") w.__tbCtx.resume();
      }}
      if (!w.__tbSilent) {{
        w.__tbSilent = new w.Audio("data:audio/wav;base64,{silent}");
        w.__tbSilent.volume = 0.01;
      }}
      var p = w.__tbSilent.play();
      if (p && p.then) p.then(function () {{
        try {{ w.__tbSilent.pause(); }} catch (e) {{}}
        w.__tbAudioReady = true;
      }}).catch(function () {{}});
    }} catch (e) {{}}
  }}
  if (!w.__tbUnlockBound) {{
    w.__tbUnlockBound = true;
    w.document.addEventListener("touchstart", unlock, {{ capture: true, passive: true }});
    w.document.addEventListener("pointerdown", unlock, {{ capture: true, passive: true }});
    w.document.addEventListener("click", unlock, {{ capture: true, passive: true }});
  }}
  unlock();
  function viaTag(data, offset) {{
    try {{
      var a = new w.Audio("data:audio/wav;base64," + data);
      a.volume = 1;
      w.__tbKeep = w.__tbKeep || [];
      w.__tbKeep.push(a);
      if (w.__tbKeep.length > 8) w.__tbKeep.shift();
      var start = function () {{
        try {{
          if (offset !== null && !isNaN(offset) && offset > 0) a.currentTime = offset;
        }} catch (e) {{}}
        a.play().catch(function () {{}});
      }};
      if (a.readyState >= 2) start();
      else {{
        a.addEventListener("loadeddata", start, {{ once: true }});
        setTimeout(start, 60);
      }}
    }} catch (e) {{}}
  }}
  function playWav(data, offset) {{
    unlock();
    var ctx = w.__tbCtx;
    if (!ctx) {{ viaTag(data, offset); return; }}
    try {{
      var bin = atob(data);
      var bytes = new Uint8Array(bin.length);
      for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      ctx.decodeAudioData(bytes.buffer.slice(0), function (ab) {{
        try {{
          if (ctx.state === "suspended") ctx.resume();
          var src = ctx.createBufferSource();
          src.buffer = ab;
          src.connect(ctx.destination);
          var off = (offset === null || isNaN(offset)) ? 0 : Math.max(0, offset);
          if (off > 0 && off < ab.duration) src.start(0, off);
          else src.start(0);
        }} catch (e) {{ viaTag(data, offset); }}
      }}, function () {{ viaTag(data, offset); }});
    }} catch (e) {{ viaTag(data, offset); }}
  }}
  playWav("{b64}", {off});
}})();
</script>
"""


def arm_unlock() -> None:
    """앱 로드 시 한 번. 첫 터치로 소리를 풀어 둔다."""
    if st.session_state.get("_sfx_armed"):
        return
    st.session_state._sfx_armed = True
    components.html(_play_js(_silent_b64()), height=1, width=1)


def play(kind: str, token: str) -> None:
    if st.session_state.get("_sfx_token") == token:
        return
    st.session_state._sfx_token = token
    b64 = base64.b64encode(_clip(kind)).decode("ascii")
    components.html(_play_js(b64), height=1, width=1)


def _fx_meta(ok: bool, streak: int) -> tuple[str, str, str, int, bool]:
    """(title, note, tier, life_ms, soft). soft면 상단 작은 토스트만(문제 가림 없음)."""
    n = max(0, int(streak or 0))
    if ok:
        if n >= 8:
            return f"{n}연속!", "대폭발 콤보", "big", 1500, False
        if n >= 5:
            return f"{n}연속!", "콤보가 터졌습니다", "big", 1500, False
        if n >= 3:
            return f"{n}연속!", "연속 정답", "hot", 1400, False
        if n >= 2:
            return f"{n}연속!", "콤보 시작", "hot", 1300, False
        return "정답", "", "ok", 700, True
    return "아쉽", "다음 문항에서 다시", "miss", 900, True


def cue(ok: bool, streak: int, kind: str, token: str) -> None:
    """정답 소리+화면을 한 번에. 단체전 첫 정답은 상단 토스트만."""
    if st.session_state.get("_fx_token") == token:
        return
    st.session_state._fx_token = token
    st.session_state._sfx_token = token
    n = max(0, int(streak or 0))
    title, note, tier, life_ms, soft = _fx_meta(ok, n)
    b64 = base64.b64encode(_clip(kind)).decode("ascii")
    burst_n = 0 if soft or not ok else (14 if n < 5 else (18 if n < 8 else 26))
    components.html(
        f"""
<script>
(function () {{
  var ok = {str(bool(ok)).lower()};
  var soft = {str(bool(soft)).lower()};
  var tier = {tier!r};
  var title = {title!r};
  var note = {note!r};
  var burstN = {int(burst_n)};
  var lifeMs = {int(life_ms)};
  var b64 = {b64!r};
  var w = window;
  var doc = w.document;

  function unlock() {{
    try {{
      var Ctx = w.AudioContext || w.webkitAudioContext;
      if (Ctx) {{
        w.__tbCtx = w.__tbCtx || new Ctx();
        if (w.__tbCtx.state === "suspended") w.__tbCtx.resume();
      }}
    }} catch (e) {{}}
  }}
  function viaTag(data) {{
    try {{
      var a = new w.Audio("data:audio/wav;base64," + data);
      a.volume = 1;
      w.__tbKeep = w.__tbKeep || [];
      w.__tbKeep.push(a);
      if (w.__tbKeep.length > 8) w.__tbKeep.shift();
      var start = function () {{ a.play().catch(function () {{}}); }};
      if (a.readyState >= 2) start();
      else {{ a.addEventListener("loadeddata", start, {{ once: true }}); setTimeout(start, 60); }}
    }} catch (e) {{}}
  }}
  function playWav(data) {{
    unlock();
    var ctx = w.__tbCtx;
    if (!ctx) {{ viaTag(data); return; }}
    try {{
      var bin = atob(data);
      var bytes = new Uint8Array(bin.length);
      for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      ctx.decodeAudioData(bytes.buffer.slice(0), function (ab) {{
        try {{
          if (ctx.state === "suspended") ctx.resume();
          var src = ctx.createBufferSource();
          src.buffer = ab;
          src.connect(ctx.destination);
          src.start(0);
        }} catch (e) {{ viaTag(data); }}
      }}, function () {{ viaTag(data); }});
    }} catch (e) {{ viaTag(data); }}
  }}
  playWav(b64);

  try {{
    var old = doc.getElementById("tb-fx-layer");
    if (old && old.parentNode) old.parentNode.removeChild(old);
  }} catch (e) {{}}

  if (soft) {{
    var toast = doc.createElement("div");
    toast.id = "tb-fx-layer";
    toast.style.cssText = "position:fixed;left:50%;top:10px;transform:translateX(-50%);z-index:2147483000;"
      + "pointer-events:none;font-family:Pretendard,Malgun Gothic,sans-serif;"
      + "font-weight:800;font-size:14px;letter-spacing:-.02em;padding:7px 14px;border-radius:999px;"
      + "box-shadow:0 4px 14px rgba(0,0,0,.18);animation:tbToast .65s ease-out forwards;";
    if (ok) {{
      toast.style.background = "rgba(16,185,129,.92)";
      toast.style.color = "#ecfdf5";
    }} else {{
      toast.style.background = "rgba(163,59,50,.9)";
      toast.style.color = "#fdeceb";
    }}
    toast.textContent = title;
    if (!doc.getElementById("tb-fx-style-soft")) {{
      var st = doc.createElement("style");
      st.id = "tb-fx-style-soft";
      st.textContent = "@keyframes tbToast{{0%{{opacity:0;transform:translateX(-50%) translateY(-8px);}}"
        + "18%{{opacity:1;transform:translateX(-50%) translateY(0);}}"
        + "75%{{opacity:1;}}100%{{opacity:0;transform:translateX(-50%) translateY(-4px);}}}}";
      try {{ (doc.head || doc.documentElement).appendChild(st); }} catch (e) {{}}
    }}
    try {{ doc.body.appendChild(toast); }} catch (e) {{ return; }}
    setTimeout(function () {{ try {{ if (toast.parentNode) toast.parentNode.removeChild(toast); }} catch (e) {{}} }}, lifeMs);
    return;
  }}

  var style = doc.getElementById("tb-fx-style");
  if (style && style.parentNode) style.parentNode.removeChild(style);
  style = doc.createElement("style");
  style.id = "tb-fx-style";
  style.textContent = `
#tb-fx-layer {{position:fixed; inset:0; z-index:2147483000; pointer-events:none; overflow:hidden;
  font-family:Pretendard,Malgun Gothic,sans-serif;}}
#tb-fx-layer .tb-flash {{position:absolute; inset:0; opacity:0; animation:tbFlash 1.1s ease-out forwards;}}
#tb-fx-layer.hot .tb-flash {{background:radial-gradient(ellipse at 50% 28%, rgba(255,196,72,.42), rgba(226,85,61,.12) 42%, transparent 68%);}}
#tb-fx-layer.big .tb-flash {{background:radial-gradient(ellipse at 50% 26%, rgba(255,230,140,.5), rgba(226,85,61,.16) 40%, transparent 70%);}}
#tb-fx-layer .tb-pop {{position:absolute; left:50%; top:26%; transform:translate(-50%,-50%); text-align:center;
  animation:tbPop 1.3s ease-out forwards;}}
#tb-fx-layer .tb-pop b {{display:block; font-size:clamp(2rem, 7vw, 3rem); font-weight:800; color:#ffe7a3;
  letter-spacing:-.03em; text-shadow:0 8px 28px rgba(0,0,0,.45), 0 0 24px rgba(255,196,72,.55);
  animation:tbShake .45s ease-out;}}
#tb-fx-layer .tb-pop span {{display:block; margin-top:6px; color:#f7ecd0; font-weight:700;
  font-size:clamp(.95rem, 3.4vw, 1.15rem); text-shadow:0 2px 10px rgba(0,0,0,.35);}}
#tb-fx-layer .tb-ring {{position:absolute; left:50%; top:26%; width:28px; height:28px; border-radius:50%;
  border:3px solid rgba(255,220,100,.9); transform:translate(-50%,-50%); animation:tbRing 1s ease-out forwards;}}
#tb-fx-layer .tb-ring.r2 {{animation-delay:.08s; border-color:rgba(255,255,255,.5);}}
#tb-fx-layer .tb-ring.r3 {{animation-delay:.16s; border-color:rgba(255,160,80,.65);}}
#tb-fx-layer .tb-spark, #tb-fx-layer .tb-burst i {{position:absolute; left:50%; top:26%; width:10px; height:10px;
  margin:-5px 0 0 -5px; border-radius:50%; background:#ffd978; box-shadow:0 0 12px rgba(255,200,80,.85);}}
#tb-fx-layer .tb-spark {{animation:tbSpark .95s ease-out forwards;}}
#tb-fx-layer .tb-burst i {{animation:tbBurst .9s ease-out forwards;}}
#tb-fx-layer .tb-burst i:nth-child(odd) {{background:#fff; width:7px; height:7px;}}
#tb-fx-layer .tb-burst i:nth-child(3n) {{background:#e2553d;}}
@keyframes tbFlash {{0%{{opacity:1;}} 100%{{opacity:0;}}}}
@keyframes tbPop {{0%{{opacity:0; transform:translate(-50%,-40%) scale(.7);}}
  18%{{opacity:1; transform:translate(-50%,-50%) scale(1.08);}}
  70%{{opacity:1;}} 100%{{opacity:0; transform:translate(-50%,-62%) scale(1);}}}}
@keyframes tbRing {{0%{{opacity:1; width:24px; height:24px;}} 100%{{opacity:0; width:280px; height:280px;}}}}
@keyframes tbSpark {{0%{{opacity:1; transform:translate(0,0) scale(1);}}
  100%{{opacity:0; transform:translate(var(--dx), var(--dy)) scale(.2);}}}}
@keyframes tbBurst {{0%{{opacity:1; transform:rotate(var(--rot)) translate(0,0) scale(1);}}
  100%{{opacity:0; transform:rotate(var(--rot)) translate(var(--dx), var(--dy)) scale(.15);}}}}
@keyframes tbShake {{0%{{transform:translateX(0);}} 25%{{transform:translateX(-4px);}}
  50%{{transform:translateX(4px);}} 100%{{transform:translateX(0);}}}}
`;
  try {{ (doc.head || doc.documentElement).appendChild(style); }} catch (e) {{}}
  var layer = doc.createElement("div");
  layer.id = "tb-fx-layer";
  layer.className = tier;
  var html = '<div class="tb-flash"></div><i class="tb-ring"></i>';
  if (tier === "hot" || tier === "big") html += '<i class="tb-ring r2"></i>';
  if (tier === "big") html += '<i class="tb-ring r3"></i>';
  [[-80,-40],[85,-50],[0,-85],[-60,55],[70,60]].forEach(function (p) {{
    html += '<i class="tb-spark" style="--dx:' + p[0] + 'px;--dy:' + p[1] + 'px"></i>';
  }});
  if (burstN > 0) {{
    html += '<span class="tb-burst">';
    for (var i = 0; i < burstN; i++) {{
      var ang = (360 / burstN) * i;
      var dist = 78 + (i % 5) * 18;
      var rad = ang * Math.PI / 180;
      html += '<i style="--dx:' + Math.round(dist * Math.cos(rad)) + 'px;--dy:'
        + Math.round(dist * Math.sin(rad)) + 'px;--rot:' + ang + 'deg"></i>';
    }}
    html += '</span>';
  }}
  html += '<div class="tb-pop"><b></b><span></span></div>';
  layer.innerHTML = html;
  layer.querySelector(".tb-pop b").textContent = title;
  layer.querySelector(".tb-pop span").textContent = note;
  try {{ doc.body.appendChild(layer); }} catch (e) {{ return; }}
  setTimeout(function () {{
    try {{ if (layer.parentNode) layer.parentNode.removeChild(layer); }} catch (e) {{}}
  }}, lifeMs);
}})();
</script>
""",
        height=1,
        width=1,
    )


def flash_fx(ok: bool, streak: int, token: str) -> None:
    """하위 호환."""
    n = max(0, int(streak or 0))
    if ok:
        if n >= 8:
            kind = "combo8"
        elif n >= 5:
            kind = "combo5"
        elif n >= 3:
            kind = "combo3"
        elif n >= 2:
            kind = "combo2"
        else:
            kind = "ok"
    else:
        kind = "miss"
    cue(ok, n, kind, token)


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
    components.html(_play_js(b64, offset=float(offset)), height=1, width=1)
