from __future__ import annotations

import html
import random
import time
import uuid
from datetime import datetime
from urllib.parse import urlencode

import streamlit as st

from src.exam import RAND_EXAM, RAND_TOPIC, area_choices, circle, item_at, make_ox_quiz, make_quiz
from src.org import TEAMS, agencies, agency_label, org_key, path_text, station_label, stations, units
from src import rooms
from src import sfx
from src import precedent
from src import standings

APP_TITLE = "실무역량 평가 다통과 : The Battle"
EXAM_TITLE = "실무역량평가(객관식)"
EXAM_DESC = "객관식 문제로 개인전·단체전 등 여러 모드에서 겨룹니다."
OX_DESC = "OX문제로 개인전·단체전 등 여러 모드에서 겨룹니다."

# 객관식 보기는 다통과처럼 st.radio 사용 (버튼 안 긴 한글 줄바꿈 깨짐 방지)
_WJ = "\u2060"


def glue_kr(text: str) -> str:
    """공백·구두점 단위로만 줄바꿈되고, 단어 안 음절은 붙인다."""
    if not text:
        return text
    out: list[str] = []
    buf: list[str] = []

    def flush() -> None:
        if buf:
            out.append(_WJ.join(buf))
            buf.clear()

    for ch in text:
        if ch.isspace() or ch in "·•|/｜,.;:!?()[]{}「」『』\"'“”‘’":
            flush()
            out.append(ch)
        else:
            buf.append(ch)
    flush()
    return "".join(out)


st.set_page_config(page_title=APP_TITLE, page_icon="🛡️", layout="wide")
st.markdown(
    """
    <style>
    @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");
    @import url("https://fonts.googleapis.com/css2?family=Sora:wght@600;700&display=swap");
    :root {
      --ink:#1c2430; --ink-2:#334155;
      --accent:#e2553d; --accent-2:#f3a08f;
      --navy:#3b4658; --navy-2:#526074;
      --gold:var(--accent); --gold-2:var(--accent-2);
      --bg:#eef1f5; --card:#ffffff; --line:#dde3ec; --muted:#667285;
      --red:#b8332a; --blue:#1c5aa3; --ok:#12784a; --bad:#c0392b;
      --sh:0 1px 2px rgba(28,36,48,.04), 0 6px 16px rgba(28,36,48,.05);
    }
    html, body, [class*="css"], .stApp, .stMarkdown, button, input, textarea, select {
      font-family: "Pretendard", "Malgun Gothic", sans-serif !important;
    }
    /* 한글 줄바꿈 — 다통과(Police_Exam)와 같이 keep-all */
    .stApp p, .stApp li, .stApp label,
    .stApp [data-testid="stMarkdownContainer"],
    .qbox, .qbox *, .case-card, .case-card *, .brief, .brief *,
    .ok, .bad, .svc, .svc *, .mast, .mast * {
      word-break: keep-all !important;
      line-break: strict !important;
      overflow-wrap: break-word !important;
    }
    /* 객관식 보기: 다통과처럼 radio 라벨 (버튼 안 긴 한글 금지) */
    div[data-testid="stRadio"] label {
      background: var(--card) !important;
      border: 1px solid var(--line) !important;
      border-radius: 11px !important;
      padding: 0.75rem 0.95rem !important;
      margin-bottom: 0.45rem !important;
      word-break: keep-all !important;
      line-break: strict !important;
      white-space: normal !important;
      line-height: 1.55 !important;
      color: var(--ink) !important;
      align-items: flex-start !important;
    }
    div[data-testid="stRadio"] label p,
    div[data-testid="stRadio"] label span,
    div[data-testid="stRadio"] label div {
      word-break: keep-all !important;
      line-break: strict !important;
      white-space: normal !important;
      overflow-wrap: break-word !important;
      line-height: 1.55 !important;
      font-weight: 650 !important;
      color: var(--ink) !important;
    }
    div[data-testid="stRadio"] > div {
      gap: 0.35rem !important;
    }
    /* 같은 창 이동 링크(판례·개정 뒤로가기용). 학습하기 외부 링크만 새 탭 */
    .battle-nav-wrap {margin:0.35rem 0 0.55rem 0; width:100%;}
    a.battle-nav {
      display:flex !important; align-items:center; justify-content:center;
      width:100%; min-height:2.8rem; padding:0.72rem 0.85rem; box-sizing:border-box;
      border-radius:11px; border:1px solid var(--line);
      background:var(--card); color:var(--ink) !important;
      font-weight:650; font-size:.95rem; text-decoration:none !important;
      line-height:1.35; word-break:keep-all;}
    a.battle-nav.primary {
      background:var(--navy) !important; color:#fff !important; border-color:var(--navy) !important;}
    a.battle-nav:hover {border-color:var(--navy-2); background:#f5f7fa;}
    a.battle-nav.primary:hover {background:var(--navy-2) !important; border-color:var(--navy-2) !important;}
    .stApp {
      background:
        radial-gradient(800px 360px at 12% -8%, rgba(226,85,61,.07), transparent 55%),
        radial-gradient(640px 320px at 96% 0%, rgba(82,96,116,.08), transparent 52%),
        linear-gradient(180deg, #f7f8fb 0%, var(--bg) 45%, #e7ebf1 100%);}
    section.main > div.block-container {
      background:rgba(255,255,255,.78); border-radius:18px; max-width:980px;
      padding:.55rem 1.05rem 1.8rem; margin-top:.2rem;
      box-shadow:0 8px 24px rgba(28,36,48,.05); border:1px solid rgba(28,36,48,.05);
      backdrop-filter:blur(6px);
      height:auto !important; min-height:0 !important; overflow:visible !important;}
    section.main {padding-top:0 !important;}
    .stMainBlockContainer, div[data-testid="stMainBlockContainer"] {padding-top:.2rem !important;}
    .block-container div[data-testid="stMarkdownContainer"]:has(.mast) {
      margin:0 0 14px 0; width:100%;}
    .block-container .mast,
    .block-container .mast.slim {margin-bottom:0; border-radius:14px; box-shadow:none;}
    /* 흰 카드 테두리는 홈 메뉴(.svc) 칸에만 — 다른 화면 칸에 고정 흰 박스가 남지 않게 */
    div[data-testid="stHorizontalBlock"]:has(.svc) {
      flex-wrap:nowrap !important; align-items:stretch !important;}
    div[data-testid="stHorizontalBlock"]:has(.svc) > div[data-testid="stColumn"] {
      min-width:0 !important; display:flex !important; flex-direction:column;}
    div[data-testid="stHorizontalBlock"]:has(.svc) > div[data-testid="stColumn"] > div,
    div[data-testid="stHorizontalBlock"]:has(.svc) > div[data-testid="stColumn"] > div > [data-testid="stLayoutWrapper"] {
      height:auto !important; min-height:100% !important; display:flex !important; flex-direction:column !important;}
    div[data-testid="stHorizontalBlock"]:has(.svc) > div[data-testid="stColumn"] > div > [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"] {
      background:var(--card) !important; border:1px solid var(--line) !important;
      border-radius:14px !important; box-shadow:var(--sh) !important;
      padding:16px 14px 14px !important; height:auto !important; flex:1 1 auto !important;
      min-height:0; box-sizing:border-box; overflow:visible !important;
      display:flex !important; flex-direction:column !important;}
    div[data-testid="stHorizontalBlock"]:has(.svc) > div[data-testid="stColumn"] > div > [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"] > div {
      flex:1 1 auto !important; display:flex !important; flex-direction:column !important;
      background:transparent !important; min-height:0 !important;}
    div[data-testid="stHorizontalBlock"]:has(.svc) [data-testid="stVerticalBlock"] .svc,
    div[data-testid="stHorizontalBlock"]:has(.svc) [data-testid="stVerticalBlock"] .svc.lead {
      border:none !important; box-shadow:none !important; background:transparent !important;
      padding:0 !important; min-height:0 !important; margin:0 !important; flex:1 1 auto;}
    div[data-testid="stHorizontalBlock"]:has(.svc) [data-testid="stVerticalBlock"] .svc h3 {
      min-height:0; display:block; overflow:visible; word-break:keep-all;}
    div[data-testid="stHorizontalBlock"]:has(.svc) [data-testid="stVerticalBlock"] .svc p {
      margin-bottom:4px; min-height:0; display:block; overflow:visible; word-break:keep-all;}
    div[data-testid="stHorizontalBlock"]:has(.svc) [data-testid="stVerticalBlock"] div.stButton,
    div[data-testid="stHorizontalBlock"]:has(.svc) [data-testid="stVerticalBlock"] div.stLinkButton {
      margin-top:auto !important; padding-top:14px;}
    div[data-testid="stHorizontalBlock"]:has(.svc) [data-testid="stVerticalBlock"] [data-testid="stElementContainer"],
    div[data-testid="stHorizontalBlock"]:has(.svc) [data-testid="stVerticalBlock"] [data-testid="stMarkdownContainer"],
    div[data-testid="stHorizontalBlock"]:has(.svc) [data-testid="stVerticalBlock"] [data-testid="stMarkdown"] {
      background:transparent !important;}
    div[data-testid="stHorizontalBlock"]:has(.svc) [data-testid="stVerticalBlock"] [data-testid="stElementContainer"]:has(.svc) {
      flex:1 1 auto !important;}
    div[data-testid="stHorizontalBlock"] {
      flex-direction:row !important; gap:12px !important; align-items:stretch !important; margin-bottom:4px;}
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
      min-width:0 !important;}
    /* 이전·다음·나가기 */
    div[data-testid="stElementContainer"]:has(.nav-mark) + div[data-testid="stHorizontalBlock"],
    div[data-testid="stElementContainer"]:has(.nav-mark) + div [data-testid="stHorizontalBlock"] {
      flex-wrap:nowrap !important; gap:8px !important;}
    div[data-testid="stElementContainer"]:has(.nav-mark) + div div.stButton > button,
    div[data-testid="stElementContainer"]:has(.nav-mark) + div [data-testid="stHorizontalBlock"] div.stButton > button {
      white-space:nowrap !important; min-width:0 !important; padding:.55rem .35rem !important;
      font-size:.9rem !important; justify-content:center !important;}
    div[data-testid="stElementContainer"]:has(.nav-mark) + div div.stButton > button > div,
    div[data-testid="stElementContainer"]:has(.nav-mark) + div div.stButton > button > div > span,
    div[data-testid="stElementContainer"]:has(.nav-mark) + div [data-testid="stHorizontalBlock"] div.stButton > button > div,
    div[data-testid="stElementContainer"]:has(.nav-mark) + div [data-testid="stHorizontalBlock"] div.stButton > button > div > span {
      width:100% !important; justify-content:center !important;}
    div[data-testid="stElementContainer"]:has(.nav-mark) + div div.stButton > button [data-testid="stMarkdownContainer"],
    div[data-testid="stElementContainer"]:has(.nav-mark) + div div.stButton > button [data-testid="stMarkdownContainer"] p {
      white-space:nowrap !important; overflow:visible !important; text-overflow:clip !important;
      font-size:.9rem !important; color:var(--ink) !important; text-align:center !important;
      width:100% !important; margin:0 !important;}
    @media (max-width:640px) {
      section.main > div.block-container {padding:.45rem .7rem 1.4rem; margin-top:.1rem; border-radius:14px;}
      .block-container div[data-testid="stMarkdownContainer"]:has(.mast) {margin:0 0 12px 0; width:100%;}
      .mast-body {padding:14px 14px 15px;}
      .mast h1 {
        font-size:clamp(.92rem, 3.9vw + .55rem, 1.18rem);
        white-space:nowrap; letter-spacing:-.03em; line-height:1.2;}
      .mast h1 .battle {margin-left:.08em; font-size:inherit;}
      .mast p {font-size:clamp(.8rem, 3.4vw, .88rem); margin-top:6px;}
      .mast .tags span {font-size:.68rem; padding:3px 8px;}
      .sect {flex-wrap:wrap; gap:4px 8px; margin:14px 0 10px 0;}
      .sect strong {font-size:.95rem;}
      .sect span {font-size:.78rem;}
      div[data-testid="stHorizontalBlock"] {gap:8px !important;}
      div[data-testid="stHorizontalBlock"]:has(.svc) > div[data-testid="stColumn"] > div > [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"] {
        padding:12px 10px 10px !important; border-radius:12px !important;}
      .svc {min-height:0; padding:0;}
      .svc h3 {font-size:clamp(.88rem, 3.6vw, .96rem); margin-bottom:5px;}
      .svc p {font-size:clamp(.76rem, 3.2vw, .84rem); line-height:1.45;}
      .svc-no {font-size:.62rem; margin-bottom:6px;}
      div[data-testid="stHorizontalBlock"]:has(.svc) [data-testid="stVerticalBlock"] div.stButton,
      div[data-testid="stHorizontalBlock"]:has(.svc) [data-testid="stVerticalBlock"] div.stLinkButton {padding-top:10px;}
      div[data-testid="stHorizontalBlock"]:has(.svc) [data-testid="stVerticalBlock"] button {
        font-size:.82rem !important; min-height:2.2rem;}
      div[data-testid="stElementContainer"]:has(.nav-mark) + div div.stButton > button,
      div[data-testid="stElementContainer"]:has(.nav-mark) + div [data-testid="stHorizontalBlock"] div.stButton > button {
        font-size:.82rem !important; padding:.5rem .25rem !important; min-height:2.4rem !important;
        justify-content:center !important;}
      div[data-testid="stElementContainer"]:has(.nav-mark) + div div.stButton > button [data-testid="stMarkdownContainer"] p {
        font-size:.82rem !important; white-space:nowrap !important; text-align:center !important;}
      div[data-testid="stRadio"] label {
        padding: 0.65rem 0.8rem !important; font-size: clamp(.86rem, 3.4vw, .95rem) !important;}
      .qbox {font-size:clamp(.92rem, 3.8vw, 1.02rem); padding:14px 14px;
        word-break:keep-all; overflow-wrap:break-word; line-break:strict;}
      .qbox .stem {word-break:keep-all; overflow-wrap:break-word; line-break:strict;}
      .codebox {font-size:clamp(2rem, 12vw, 2.6rem); padding:16px 12px;}
    }
    header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
    .stAppDeployButton, #MainMenu, footer {display:none !important;}
    h1,h2,h3,h4 {word-break:keep-all; letter-spacing:-.02em;}

    /* ── 상단 배너 (라이트) ─────────────────────── */
    .mast {background:linear-gradient(180deg,#ffffff 0%,#f5f7fa 100%);
      color:var(--ink); border-radius:14px; overflow:hidden; margin-bottom:18px; position:relative;
      border:1px solid var(--line);}
    .mast::after {content:""; position:absolute; inset:auto 0 0 0; height:2px;
      background:linear-gradient(90deg,var(--accent),rgba(226,85,61,.15) 55%,transparent);}
    .mast-body {padding:12px 16px 14px;}
    .mast-meta {display:flex; align-items:center; justify-content:space-between; gap:10px;
      margin-bottom:6px; font-size:.72rem; letter-spacing:.04em; color:var(--muted);}
    .brand {display:flex; align-items:center; gap:8px;}
    .brand-name {font-family:"Sora", "Pretendard", sans-serif !important; font-weight:700;
      letter-spacing:.01em; color:var(--ink-2); word-break:keep-all; font-size:.78rem;}
    .mark {width:10px; height:10px; display:inline-block; flex-shrink:0; border-radius:3px;
      background:var(--accent);}
    .mast h1 {margin:0; font-size:1.48rem; line-height:1.25; font-weight:780; color:var(--ink);
      white-space:nowrap;}
    .mast h1 .battle {font-family:"Sora", "Pretendard", sans-serif !important; font-weight:700;
      color:var(--accent); margin-left:.15em; white-space:nowrap;}
    .mast p {margin:6px 0 0 0; color:var(--muted); line-height:1.55; max-width:38rem; font-size:.9rem; word-break:keep-all;}
    .mast.slim {margin-bottom:12px; display:flex; align-items:center; justify-content:space-between;
      gap:10px; padding:11px 16px;}
    .mast.slim .mast-body {padding:0;}
    .slim-title {color:var(--ink); font-weight:720; font-size:.92rem; margin-left:10px; padding-left:11px;
      border-left:1px solid var(--line); letter-spacing:-.01em;}
    .mast-right {font-size:.72rem; color:var(--muted); white-space:nowrap;}
    .mast .tags {margin-top:9px; display:flex; flex-wrap:wrap; gap:6px;}
    .block-container div[data-testid="stMarkdownContainer"]:has(.mast) {padding-top:0 !important;}
    .block-container div[data-testid="stElementContainer"]:has(.mast) {margin-top:0 !important; padding-top:0 !important;}
    .mast .tags span {font-size:.74rem; padding:4px 9px; border-radius:8px;
      background:#eef2f7; border:1px solid #d8e0ea; color:#516074;}

    .svc {background:var(--card); border:1px solid var(--line); border-radius:14px;
      padding:18px 18px 15px; min-height:0; box-shadow:var(--sh);
      transition:transform .14s ease, box-shadow .14s ease, border-color .14s ease;}
    .svc:hover {transform:translateY(-2px); box-shadow:0 10px 22px rgba(28,36,48,.08); border-color:#c9d3e0;}
    .svc.lead {border-color:#d5deea; background:linear-gradient(180deg,#fbfcfe,#fff);}
    .svc-no {display:inline-flex; align-items:center; gap:7px; font-size:.7rem; letter-spacing:.15em;
      color:var(--accent); font-weight:750; margin-bottom:9px;}
    .svc-no::before {content:""; width:16px; height:2px; background:var(--accent); border-radius:2px;}
    .svc h3 {margin:0 0 7px 0; font-size:1.13rem; color:var(--ink);}
    .svc p {margin:0; color:#5d6778; font-size:.9rem; line-height:1.62; word-break:keep-all;}

    .pill {display:inline-block; font-size:.78rem; font-weight:650; padding:4px 11px; border-radius:999px;
      background:#eef2f7; color:var(--ink-2); border:1px solid #d8e0ea; margin:0 5px 5px 0;}
    .pill.gold {background:#fce8e3; color:#a63d2c; border-color:#f0c4ba;}
    .pill.red {background:#fbeceb; color:var(--red); border-color:#f0c9c6;}
    .pill.blue {background:#e8f0fb; color:var(--blue); border-color:#c6d9f2;}
    .sect {display:flex; align-items:baseline; gap:10px; margin:18px 0 12px 0;}
    .sect strong {color:var(--ink); font-size:1.03rem; letter-spacing:-.01em;}
    .sect span {color:var(--muted); font-size:.88rem;}

    /* ── 게임 상황판(스티키) ───────────────────── */
    div[data-testid="stElementContainer"]:has(> .stMarkdown .hud),
    div[data-testid="element-container"]:has(> .stMarkdown .hud) {
      position:sticky; top:0; z-index:40; background:var(--bg); padding:6px 0 4px;
    }
    .hud {background:var(--navy); border-radius:13px; padding:11px 15px 12px; color:#fff;
      box-shadow:0 6px 16px rgba(59,70,88,.16);}
    .hud-row {display:flex; align-items:center; gap:6px; flex-wrap:wrap; justify-content:flex-start;}
    .hud .chip {font-size:.74rem; padding:4px 8px; border-radius:8px; background:rgba(255,255,255,.11);
      border:1px solid rgba(255,255,255,.14); color:#cddcec; white-space:nowrap;}
    .hud .chip b {color:#fff; font-weight:750; margin-left:4px;}
    .hud .chip.gold {background:rgba(201,162,39,.22); border-color:rgba(232,208,145,.5); color:#f2e2b8;}
    .hud .chip.hot {background:rgba(216,90,44,.26); border-color:rgba(240,150,110,.55); color:#ffd9c8;}
    .hud .grow {flex:1;}
    .prog {height:7px; border-radius:999px; background:rgba(255,255,255,.14); overflow:hidden; margin:0 0 10px 0;}
    .prog i {display:block; height:100%; border-radius:999px;
      background:linear-gradient(90deg,var(--gold),var(--gold-2)); transition:width .3s ease;}
    .tmr {height:9px; border-radius:999px; background:rgba(255,255,255,.14); overflow:hidden; margin-top:10px;}
    .tmr i {display:block; height:100%; border-radius:999px;
      background:linear-gradient(90deg,#35b37e,#e2b53f 60%,#e05a4a); animation:drain linear forwards;}
    @keyframes drain {from {width:var(--w);} to {width:0%;}}

    /* ── 순위표 ────────────────────────────────── */
    .rank {background:var(--card); border:1px solid var(--line); border-radius:14px; padding:8px 6px; box-shadow:var(--sh);}
    .rank-row {display:flex; align-items:center; gap:11px; padding:9px 12px; border-radius:10px;}
    .rank-row + .rank-row {border-top:1px solid #eef2f8;}
    .rank-row.me {background:#f2f7ff;}
    .rank-gap {text-align:center; color:#93a2b6; font-size:.78rem; letter-spacing:.28em;
      padding:4px 0 2px; border-top:1px dashed #e2e8f0;}
    .pos {width:26px; height:26px; border-radius:8px; display:grid; place-items:center; flex-shrink:0;
      font-size:.82rem; font-weight:800; background:#eef2f8; color:#6b7a8d;}
    .pos.p1 {background:linear-gradient(180deg,#f5d97a,#d4af37); color:#4a3906;}
    .pos.p2 {background:linear-gradient(180deg,#e2e8ef,#b9c4d1); color:#41505f;}
    .pos.p3 {background:linear-gradient(180deg,#e8c39c,#c08a55); color:#4b2f13;}
    .who {min-width:0; flex:1;}
    .who b {display:block; font-size:.96rem; color:var(--ink); font-weight:680;
      white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
    .who small {color:var(--muted); font-size:.78rem; display:block;
      white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
    .who .org-short {display:none;}
    .who .org-full {display:inline;}
    .who .meta-bit {display:inline;}
    .who em {font-style:normal; font-size:.72rem; padding:1px 7px; border-radius:999px; margin-left:6px;}
    .who em.red {background:#fbeceb; color:var(--red);}
    .who em.blue {background:#e8f0fb; color:var(--blue);}
    .rbar {width:120px; height:7px; border-radius:999px; background:#eaeff6; overflow:hidden; flex-shrink:0;}
    .rbar i {display:block; height:100%; border-radius:999px; background:linear-gradient(90deg,var(--navy-2),#3f77c4);}
    .val {width:78px; text-align:right; font-weight:750; color:var(--navy); font-size:.94rem; flex-shrink:0;}
    .val small {display:block; font-weight:500; color:var(--muted); font-size:.72rem;}
    @media (max-width:640px) {
      .rank {padding:4px 2px;}
      .rank-row {gap:8px; padding:8px 8px; align-items:center;}
      .pos {width:24px; height:24px; font-size:.78rem;}
      .who b {font-size:.9rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
      .who small {font-size:.7rem; line-height:1.3; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
      .who .org-full {display:none;}
      .who .org-short {display:inline;}
      .rbar {display:none;}
      .val {width:auto; min-width:3.1rem; font-size:.86rem;}
      .val small {font-size:.66rem;}
    }

    /* ── 팀 대항 점수판 ────────────────────────── */
    .teams {display:flex; align-items:stretch; gap:10px; margin:4px 0 6px;}
    .team {flex:1; border-radius:14px; padding:14px 16px; color:#fff; box-shadow:var(--sh);}
    .team.red {background:linear-gradient(135deg,#a82c24,#cf4b3e);}
    .team.blue {background:linear-gradient(135deg,#17457f,#2f74c4);}
    .team b {display:block; font-size:.9rem; opacity:.92; letter-spacing:.04em;}
    .team strong {display:block; font-size:2rem; font-weight:800; line-height:1.2; margin-top:2px;}
    .team span {font-size:.79rem; opacity:.85;}
    .vs {display:grid; place-items:center; font-weight:800; color:#93a2b6; font-size:.9rem; padding:0 2px;}
    .seat {border-radius:14px; padding:15px 18px; color:#fff; margin:8px 0 12px; box-shadow:var(--sh);}
    .seat.red {background:linear-gradient(135deg,#a82c24,#cf4b3e);}
    .seat.blue {background:linear-gradient(135deg,#17457f,#2f74c4);}
    .seat.wait {background:#3a4658;}
    .seat b {display:block; font-size:.8rem; letter-spacing:.05em; opacity:.9;}
    .seat strong {display:block; font-size:1.55rem; font-weight:800; margin-top:3px; letter-spacing:-.02em;}
    .seat span {display:block; margin-top:4px; font-size:.88rem; opacity:.9;}

    /* ── 참가자 칩 ─────────────────────────────── */
    .peers {display:flex; flex-wrap:wrap; gap:7px; margin:2px 0 4px;}
    .peer {display:inline-flex; align-items:flex-start; gap:6px; background:var(--card); border:1px solid var(--line);
      border-radius:12px; padding:5px 12px; font-size:.88rem; color:var(--ink); box-shadow:0 1px 2px rgba(11,31,58,.05);
      max-width:100%;}
    .peer i {width:7px; height:7px; border-radius:50%; background:#37b26b; display:inline-block; flex-shrink:0; margin-top:.4em;}
    .peer.red i {background:var(--red);} .peer.blue i {background:var(--blue);}
    .peer.host::after {content:"방장"; font-size:.68rem; color:#8a6d1c; background:#fbf3dd;
      border:1px solid #ecd9a3; border-radius:999px; padding:1px 6px; flex-shrink:0; align-self:center;}
    .peer .org {display:block; font-size:.72rem; color:var(--muted); font-weight:500; word-break:keep-all; line-height:1.35; margin-top:2px;}

    /* ── 문제 ─────────────────────────────────── */
    .qbox {background:var(--card); border:1px solid var(--line); border-radius:14px;
      padding:20px 22px; margin:12px 0 14px 0; line-height:1.78; word-break:keep-all;
      overflow-wrap:normal; line-break:strict; font-size:1.06rem; color:var(--ink); box-shadow:var(--sh); position:relative;}
    .qbox::before {content:""; position:absolute; left:0; top:16px; bottom:16px; width:4px;
      border-radius:0 4px 4px 0; background:linear-gradient(180deg,var(--navy-2),var(--gold));}
    .qbox.x2::before {background:linear-gradient(180deg,var(--gold),#e0743a);}
    .qbox .meta {color:var(--muted); font-size:.83rem; margin-bottom:10px; letter-spacing:.02em;
      display:flex; align-items:center; gap:8px; flex-wrap:wrap;}
    .qbox .meta .x2tag {background:#fdf0dd; color:#9a5a12; border:1px solid #f0cf9d;
      border-radius:999px; padding:2px 9px; font-weight:750;}
    .qbox .stem {white-space:normal; word-break:keep-all; overflow-wrap:break-word; line-break:strict;}
    .qbox .ox-ask {margin:0 0 10px; color:var(--muted); font-size:.9rem; word-break:keep-all;}
    .qbox .ox-ctx {margin:0 0 10px; color:#4d5b6e; font-size:.92rem; line-height:1.6; word-break:keep-all;}
    .qbox .ox-say {margin:0; background:#f4f7fb; border:1px solid #d9e1ed; border-radius:12px;
      padding:14px 16px; font-size:1.12rem; font-weight:650; line-height:1.7; word-break:keep-all;}
    .codebox {font-size:3rem; font-weight:800; letter-spacing:.22em; color:var(--navy); margin:8px 0 10px;
      background:var(--card); border:1px solid var(--line); border-radius:16px; padding:20px 16px 20px 26px;
      text-align:center; box-shadow:var(--sh);}

    /* ── 버튼 ─────────────────────────────────── */
    /* 1.59는 버튼을 감싼 칸을 글자 폭에 맞춰 줄인다. 칸부터 늘려야 버튼이 늘어난다. */
    div[data-testid="stElementContainer"]:has([data-testid="stButton"]),
    div[data-testid="stElementContainer"]:has([data-testid="stFormSubmitButton"]) {width:100% !important;}
    div[data-testid="stButton"], div[data-testid="stFormSubmitButton"] {width:100% !important;}
    div.stButton > button, div.stFormSubmitButton > button {width:100% !important;}
    div.stButton > button, div.stFormSubmitButton > button {
      white-space:normal !important; height:auto !important; min-height:2.8rem;
      line-height:1.45; word-break:keep-all !important; overflow-wrap:normal !important;
      line-break:strict; overflow:visible !important; text-overflow:clip !important;
      padding:.72rem .85rem; border-radius:11px !important; border:1px solid var(--line) !important;
      transition:transform .1s ease, box-shadow .12s ease, background .12s ease;}
    /* 글자는 button > div > span > stMarkdownContainer > p 안에 있다. */
    div.stButton > button [data-testid="stMarkdownContainer"] p,
    div.stFormSubmitButton > button [data-testid="stMarkdownContainer"] p,
    div.stLinkButton > a,
    div.stLinkButton > a [data-testid="stMarkdownContainer"] p,
    a[data-testid="stBaseLinkButton"],
    a[data-testid="stBaseLinkButton"] p {
      font-family: "Pretendard", "Malgun Gothic", sans-serif !important;
      font-weight:650 !important; font-size:.95rem !important; line-height:1.45 !important;
      letter-spacing:-.01em !important; margin:0;
      white-space:normal !important; overflow:visible !important; text-overflow:clip !important;
      word-break:keep-all !important; overflow-wrap:normal !important; line-break:strict !important;}
    div.stButton > button > div,
    div.stFormSubmitButton > button > div,
    div.stButton > button > div > span,
    div.stFormSubmitButton > button > div > span {
      max-width:100% !important; white-space:normal !important; overflow:visible !important;
      word-break:keep-all !important;}
    /* 짧은 액션(홈·방 열기·요지·원문)은 한 줄 유지 */
    div.stButton > button[kind="primary"] [data-testid="stMarkdownContainer"] p,
    div.stFormSubmitButton > button[kind="primary"] [data-testid="stMarkdownContainer"] p {
      color:#fff !important; text-align:center !important; white-space:nowrap !important;}
    div.stLinkButton > a [data-testid="stMarkdownContainer"] p,
    a[data-testid="stBaseLinkButton"] p {
      text-align:center !important; white-space:nowrap !important;}
    /* 객관식 보기(secondary + choice-mark)만 왼쪽 정렬. 그 외 secondary(뒤로·홈)는 가운데 */
    div.stButton > button[kind="secondary"] {background:var(--card); justify-content:center !important;
      color:var(--ink) !important;}
    div.stButton > button[kind="secondary"] > div,
    div.stButton > button[kind="secondary"] > div > span {width:100%; justify-content:center !important;}
    div.stButton > button[kind="secondary"] [data-testid="stMarkdownContainer"],
    div.stButton > button[kind="secondary"] [data-testid="stMarkdownContainer"] p {
      text-align:center !important; color:var(--ink) !important; white-space:normal !important;
      word-break:keep-all !important; overflow-wrap:normal !important; line-break:strict !important;}
    div[data-testid="stElementContainer"]:has(.choice-mark) + div div.stButton > button[kind="secondary"],
    div[data-testid="stElementContainer"]:has(.choice-mark) ~ div div.stButton > button[kind="secondary"] {
      justify-content:flex-start !important;}
    div[data-testid="stElementContainer"]:has(.choice-mark) + div div.stButton > button[kind="secondary"] > div,
    div[data-testid="stElementContainer"]:has(.choice-mark) + div div.stButton > button[kind="secondary"] > div > span,
    div[data-testid="stElementContainer"]:has(.choice-mark) ~ div div.stButton > button[kind="secondary"] > div,
    div[data-testid="stElementContainer"]:has(.choice-mark) ~ div div.stButton > button[kind="secondary"] > div > span {
      justify-content:flex-start !important;}
    div[data-testid="stElementContainer"]:has(.choice-mark) + div div.stButton > button[kind="secondary"] [data-testid="stMarkdownContainer"] p,
    div[data-testid="stElementContainer"]:has(.choice-mark) ~ div div.stButton > button[kind="secondary"] [data-testid="stMarkdownContainer"] p {
      text-align:left !important;}
    div.stButton > button[kind="secondary"]:hover {border-color:var(--navy-2) !important; background:#f5f7fa;}
    div.stButton > button[kind="primary"], div.stFormSubmitButton > button[kind="primary"],
    div.stLinkButton > a[kind="primary"], a[data-testid="stBaseLinkButton"] {
      justify-content:center !important; background:var(--navy) !important; color:#fff !important;
      border-color:var(--navy) !important; box-shadow:0 2px 8px rgba(59,70,88,.14);
      font-family: "Pretendard", "Malgun Gothic", sans-serif !important;
      font-weight:650 !important; font-size:.95rem !important;}
    div.stButton > button[kind="primary"]:hover, div.stFormSubmitButton > button[kind="primary"]:hover,
    div.stLinkButton > a[kind="primary"]:hover, a[data-testid="stBaseLinkButton"]:hover {
      background:var(--navy-2) !important; border-color:var(--navy-2) !important; transform:translateY(-1px);
      color:#fff !important;}
    div.stLinkButton > a {width:100% !important; border-radius:11px !important;
      min-height:2.8rem; display:inline-flex !important; align-items:center; justify-content:center;
      padding:.72rem .85rem !important; box-sizing:border-box; white-space:nowrap !important;}
    div.stButton > button:active {transform:translateY(0);}

    div[data-testid="stColumn"] [data-testid="stVerticalBlock"] div.stButton > button[kind="primary"],
    div[data-testid="stColumn"] [data-testid="stVerticalBlock"] div.stLinkButton > a[kind="primary"],
    div[data-testid="stColumn"] [data-testid="stVerticalBlock"] a[data-testid="stBaseLinkButton"] {
      font-family: "Pretendard", "Malgun Gothic", sans-serif !important;
      font-weight:650 !important; font-size:.95rem !important; letter-spacing:-.01em !important;}
    div[data-testid="stColumn"] [data-testid="stVerticalBlock"] div.stButton > button[kind="primary"] [data-testid="stMarkdownContainer"] p,
    div[data-testid="stColumn"] [data-testid="stVerticalBlock"] div.stLinkButton > a[kind="primary"] [data-testid="stMarkdownContainer"] p,
    div[data-testid="stColumn"] [data-testid="stVerticalBlock"] a[data-testid="stBaseLinkButton"] p {
      font-family: "Pretendard", "Malgun Gothic", sans-serif !important;
      font-weight:650 !important; font-size:.95rem !important; letter-spacing:-.01em !important;
      color:#fff !important; text-align:center !important;}
    div[data-testid="stColumn"] [data-testid="stVerticalBlock"] div.stButton > button[kind="secondary"] [data-testid="stMarkdownContainer"] p {
      color:var(--ink) !important;}

    /* 표시용 빈 div 바로 다음 줄에 오는 버튼을 골라 쓴다. */
    div[data-testid="stElementContainer"]:has(.ox-mark) + div div.stButton > button {
      min-height:4.6rem !important; justify-content:center !important;}
    div[data-testid="stElementContainer"]:has(.ox-mark) + div div.stButton > button > div,
    div[data-testid="stElementContainer"]:has(.ox-mark) + div div.stButton > button > div > span,
    div[data-testid="stElementContainer"]:has(.case-actions-mark) + div div.stButton > button > div,
    div[data-testid="stElementContainer"]:has(.case-actions-mark) + div div.stButton > button > div > span,
    div[data-testid="stElementContainer"]:has(.mini-mark) + div div.stButton > button > div,
    div[data-testid="stElementContainer"]:has(.mini-mark) + div div.stButton > button > div > span {
      justify-content:center !important;}
    div[data-testid="stElementContainer"]:has(.ox-mark) + div div.stButton > button
      [data-testid="stMarkdownContainer"] p {
      font-size:2.2rem !important; font-weight:800 !important; letter-spacing:.06em; text-align:center !important;}
    div[data-testid="stElementContainer"]:has(.case-actions-mark) + div div.stButton > button,
    div[data-testid="stElementContainer"]:has(.mini-mark) + div div.stButton > button {
      min-height:2.2rem !important; padding:.32rem .9rem !important; justify-content:center !important;}
    div[data-testid="stElementContainer"]:has(.case-actions-mark) + div div.stButton > button
      [data-testid="stMarkdownContainer"] p,
    div[data-testid="stElementContainer"]:has(.mini-mark) + div div.stButton > button
      [data-testid="stMarkdownContainer"] p {
      font-size:.87rem !important; text-align:center !important;}
    /* 개정 이유·요지 보기 옆 원문 링크 세로 맞춤 */
    div[data-testid="stElementContainer"]:has(.case-actions-mark) + div [data-testid="stHorizontalBlock"] {
      align-items:center !important;}
    div[data-testid="stElementContainer"]:has(.case-actions-mark) + div div.stLinkButton > a,
    div[data-testid="stElementContainer"]:has(.case-actions-mark) + div a[data-testid="stBaseLinkButton"] {
      min-height:2.2rem !important; padding:.32rem .9rem !important;
      display:inline-flex !important; align-items:center; justify-content:center;
      background:var(--card) !important; color:var(--ink-2) !important;
      border:1px solid var(--line) !important; box-shadow:none !important;
      font-size:.87rem !important; font-weight:650 !important;}
    div[data-testid="stElementContainer"]:has(.case-actions-mark) + div [data-testid="stMarkdownContainer"] p {
      margin:0 !important; display:flex; align-items:center; min-height:2.2rem;}
    div[data-testid="stElementContainer"]:has(.case-actions-mark) + div [data-testid="stMarkdownContainer"] a {
      line-height:1.3; font-weight:650;}

    /* ── 결과·판례 ─────────────────────────────── */
    .ok {background:#e9f7ef; border:1px solid #b3e0c6; border-left:4px solid var(--ok); border-radius:10px;
      padding:11px 13px; word-break:keep-all; overflow-wrap:normal; line-break:strict; white-space:pre-wrap;}
    .bad {background:#fdeeec; border:1px solid #f3c6c1; border-left:4px solid var(--bad); border-radius:10px;
      padding:11px 13px; word-break:keep-all; overflow-wrap:normal; line-break:strict; white-space:pre-wrap;}
    .case-card {background:var(--card); border:1px solid var(--line); border-radius:12px;
      padding:14px 16px 12px; margin:10px 0 6px 0; box-shadow:var(--sh);}
    .case-meta {margin:0; font-size:.88rem; color:var(--muted); word-break:keep-all;}
    .case-name {margin:7px 0 0 0; font-size:1.1rem; font-weight:680; line-height:1.55; color:var(--navy);
      word-break:keep-all; overflow-wrap:normal; line-break:strict;}
    .brief {background:var(--card); border:1px solid var(--line); border-left:4px solid var(--gold);
      border-radius:12px; padding:12px 16px; margin:7px 0; box-shadow:var(--sh);}
    .brief p {margin:0; font-size:.83rem; color:var(--muted); word-break:keep-all;}
    .brief b {display:block; margin-top:3px; font-size:1rem; color:var(--navy); font-weight:680;
      word-break:keep-all; overflow-wrap:normal; line-break:strict;}

    /* ── 접는 칸·알림 ──────────────────────────── */
    div[data-testid="stExpander"] {border:1px solid var(--line) !important; border-radius:12px !important;
      background:var(--card); box-shadow:var(--sh); overflow:hidden;}
    div[data-testid="stExpander"] summary {font-weight:650; color:var(--navy);}
    div[data-testid="stAlertContainer"] {border-radius:12px;}

    /* ── 입력 ─────────────────────────────────── */
    div[data-testid="stForm"] {border:1px solid var(--line); background:var(--card); border-radius:14px;
      padding:8px 18px 14px; max-width:460px; box-shadow:var(--sh);}
    [data-testid="stTextInput"] input, [data-baseweb="input"] input,
    input[type="password"], input[type="text"] {
      direction:ltr !important; text-align:left !important; unicode-bidi:isolate !important;}
    [data-testid="stTextInput"] [data-baseweb="base-input"],
    [data-testid="stTextInput"] [data-baseweb="input"] {direction:ltr !important; flex-direction:row !important;}

    /* ── 연속 정답 이펙트(직접 그린 CSS, 상용 이미지 없음) ── */
    .fx-layer {position:fixed; inset:0; pointer-events:none; z-index:90; overflow:hidden;}
    .fx-flash {position:absolute; inset:0; background:radial-gradient(ellipse at 50% 32%,
      rgba(232,208,145,.34), transparent 58%); animation:fxFlash 1.05s ease-out forwards;}
    .fx-flash.miss {background:radial-gradient(ellipse at 50% 32%,
      rgba(192,57,43,.16), transparent 58%);}
    .fx-pop {position:absolute; left:50%; top:26%; transform:translate(-50%,-50%);
      text-align:center; animation:fxPop 1.2s ease-out forwards;}
    .fx-pop b {display:block; font-size:2.35rem; font-weight:800; color:#fff;
      letter-spacing:-.03em; text-shadow:0 6px 22px rgba(11,31,58,.38);}
    .fx-pop.hot b {font-size:2.75rem; color:#ffe7a3;}
    .fx-pop.big b {font-size:3.1rem; color:#fff3c4;}
    .fx-pop span {display:block; margin-top:5px; color:#f2e2b8; font-weight:680; font-size:1.02rem;}
    .fx-pop.miss b {color:#f3d0cc; font-size:1.7rem;}
    .fx-ring {position:absolute; left:50%; top:26%; width:28px; height:28px; border-radius:50%;
      border:3px solid rgba(201,162,39,.9); transform:translate(-50%,-50%);
      animation:fxRing 1s ease-out forwards;}
    .fx-ring.r2 {animation-delay:.08s; border-color:rgba(255,255,255,.45);}
    .fx-spark {position:absolute; left:50%; top:26%; width:8px; height:8px; margin:-4px 0 0 -4px;
      border-radius:50%; background:#e8d091; box-shadow:0 0 8px rgba(232,208,145,.8);
      animation:fxSpark .95s ease-out forwards;}
    @keyframes fxFlash {0%{opacity:.95;} 100%{opacity:0;}}
    @keyframes fxPop {0%{opacity:0; transform:translate(-50%,-38%) scale(.62);}
      16%{opacity:1; transform:translate(-50%,-50%) scale(1.08);}
      68%{opacity:1;} 100%{opacity:0; transform:translate(-50%,-62%) scale(1);}}
    @keyframes fxRing {0%{opacity:.95; width:22px; height:22px;} 100%{opacity:0; width:240px; height:240px;}}
    @keyframes fxSpark {0%{opacity:1; transform:translate(0,0) scale(1);}
      100%{opacity:0; transform:translate(var(--dx), var(--dy)) scale(.15);}}
    .hud .chip.hot {animation:hotPulse .55s ease;}
    @keyframes hotPulse {0%{transform:scale(1);} 40%{transform:scale(1.14);} 100%{transform:scale(1);}}
    </style>
    """,
    unsafe_allow_html=True,
)

GATE_PASSWORD = "12345678"
RANK_RESET_PASSWORDS = frozenset({"rlawhdtjs1^", "whdtjs12^"})
GATE_STORE = "thebattle_gate_v1"
PID_STORE = "thebattle_pid_v1"
GATE_TTL_SEC = 12 * 60 * 60  # 활동 기준 12시간 (새로고침 유지, 영구 출입 방지)


def _drop_room() -> None:
    """방 번호만 지운다. 출입·화면(view) 상태는 남긴다."""
    _clear_param("room")
    if st.session_state.get("unlocked"):
        _mark_gate()


def _clear_param(name: str) -> None:
    if name not in st.query_params:
        return
    try:
        del st.query_params[name]
    except Exception:
        vals = {k: st.query_params.get(k) for k in list(st.query_params.keys()) if k != name}
        st.query_params.clear()
        for k, v in vals.items():
            if v is not None:
                st.query_params[k] = v


def _cookie_gate_on() -> bool:
    try:
        return str(st.context.cookies.get(GATE_STORE) or "") == "1"
    except Exception:
        return False


def _cookie_pid() -> str:
    try:
        return str(st.context.cookies.get(PID_STORE) or "").strip()
    except Exception:
        return ""


def _gate_js(script: str) -> None:
    import streamlit.components.v1 as components

    components.html(
        f"<script>(function(){{\n{script}\n}})();</script>",
        height=0,
        width=0,
    )


# hub↔판례·개정·입장은 URL view= 로 이동(브라우저 뒤로가기 동작).
# lobby/play 시합 중에는 session phase를 유지하고 URL만 되돌린다.
VIEW_FREE = frozenset({"hub", "cases", "laws", "enter", "host_setup"})
VIEW_LOCK = frozenset({"lobby", "play"})
ROOM_LIVE = frozenset({"lobby", "countdown", "play", "done"})


def _qp_one(name: str) -> str:
    raw = st.query_params.get(name)
    if raw is None:
        return ""
    if isinstance(raw, (list, tuple)):
        return str(raw[0] or "").strip()
    return str(raw or "").strip()


def _app_href(view: str, *, keep_room: bool = False, **extra: str) -> str:
    """자유 화면 URL. 히스토리 push / 공유용."""
    q: dict[str, str] = {"view": view}
    inn = _qp_one("in")
    if inn:
        q["in"] = inn
    pid = _qp_one("pid") or str(st.session_state.get("pid") or "").strip()
    if pid:
        q["pid"] = pid
    if keep_room:
        room = _qp_one("room") or str(st.session_state.get("code") or "").strip()
        if room:
            q["room"] = room
    for k, v in extra.items():
        if v is not None and str(v) != "":
            q[k] = str(v)
    return "?" + urlencode(q)


def _push_history(href: str) -> None:
    """앱 iframe history에 쌓는다. (Cloud는 top 껍데기와 /~/+/ 앱이 분리됨)"""
    if not href.startswith("?"):
        href = "?" + href
    _gate_js(
        f"""
        var app = window.parent;
        try {{
          if (!app || !app.location || String(app.location.pathname||"").indexOf("/~/+/") < 0) {{
            if (window.top && window.top.document) {{
              var f = window.top.document.querySelector('iframe[title=streamlitApp]');
              if (f && f.contentWindow) app = f.contentWindow;
            }}
          }}
        }} catch (e) {{}}
        try {{
          // 목록/홈으로 올 때 상세 스택 키 제거 → 다음 요지 열기에서 다시 쌓임
          try {{
            var rm = [];
            for (var i = 0; i < app.sessionStorage.length; i++) {{
              var k = app.sessionStorage.key(i);
              if (k && k.indexOf("battleNavStacked:") === 0) rm.push(k);
            }}
            rm.forEach(function (k) {{ app.sessionStorage.removeItem(k); }});
          }} catch (e) {{}}
          var next = app.location.pathname + "{href}";
          if ((app.location.pathname + app.location.search) !== next) {{
            app.history.pushState({{battleNav: 1}}, "", next);
          }}
          try {{
            if (window.top && window.top !== app) {{
              window.top.history.replaceState({{battleNav: 1}}, "", window.top.location.pathname + "{href}");
            }}
          }} catch (e) {{}}
          if (!app.__battlePopV4) {{
            app.__battlePopV4 = true;
            app.addEventListener("popstate", function () {{
              try {{
                var q = app.location.search || "";
                if (window.top && window.top !== app) {{
                  window.top.location.replace(window.top.location.pathname + q);
                  return;
                }}
              }} catch (e) {{}}
              try {{ app.location.reload(); }} catch (e) {{}}
            }});
          }}
        }} catch (e) {{}}
        """
    )


def _stack_detail_history(*, list_href: str, detail_href: str) -> None:
    """호환용. 실제 스택은 _apply_browser_nav 의 상시 스크립트가 담당한다."""
    return


def _open_view(view: str, **extra: str) -> None:
    """같은 탭 버튼 이동. case/law는 URL에 넣어 뒤로가기 시 목록·홈으로 돌아간다."""
    st.session_state.phase = view
    st.query_params["view"] = view
    if st.session_state.get("pid"):
        st.query_params["pid"] = st.session_state.pid

    if view == "hub":
        st.session_state.pop("code", None)
        _clear_param("room")
        _clear_param("case")
        _clear_param("law")
        st.session_state.case_open = ""
        st.session_state.law_open = ""
        _push_history(_app_href("hub"))
        return

    if view == "cases":
        _clear_param("law")
        st.session_state.law_open = ""
        case_id = str(extra.get("case") or "").strip()
        st.session_state.case_open = case_id
        if case_id:
            st.query_params["case"] = case_id
            _stack_detail_history(
                list_href=_app_href("cases"),
                detail_href=_app_href("cases", case=case_id),
            )
        else:
            _clear_param("case")
            _push_history(_app_href("cases"))
        return

    if view == "laws":
        _clear_param("case")
        st.session_state.case_open = ""
        law_id = str(extra.get("law") or "").strip()
        st.session_state.law_open = law_id
        if law_id:
            st.query_params["law"] = law_id
            _stack_detail_history(
                list_href=_app_href("laws"),
                detail_href=_app_href("laws", law=law_id),
            )
        else:
            _clear_param("law")
            _push_history(_app_href("laws"))
        return

    _push_history(_app_href(view, **{k: str(v) for k, v in extra.items() if v}))


def _persist_pid(pid: str) -> None:
    """단체전 튕김 대비: 참가자 id를 URL·쿠키에 남긴다."""
    pid = (pid or "").strip()
    if not pid:
        return
    st.query_params["pid"] = pid
    _gate_js(
        f"""
        var KEY = "{PID_STORE}";
        var w = window.parent;
        try {{ if (window.top && window.top.location) w = window.top; }} catch (e) {{}}
        try {{
          var secure = (w.location.protocol === "https:") ? "; Secure" : "";
          w.document.cookie = KEY + "={pid}; path=/; max-age={7 * 24 * 3600}; SameSite=Lax" + secure;
        }} catch (e) {{}}
        try {{ w.sessionStorage.setItem(KEY, "{pid}"); }} catch (e) {{}}
        """
    )


def _restore_player_from_room(room: dict, pid: str) -> None:
    me = (room.get("players") or {}).get(pid) or {}
    if not me:
        return
    if not (st.session_state.get("player_name") or "").strip():
        st.session_state.player_name = (me.get("name") or "").strip()
    if not st.session_state.get("my_org") and me.get("org"):
        st.session_state.my_org = dict(me.get("org") or {})


def _goto(phase: str) -> None:
    """세션 화면 전환(+ view 동기화). 판례·개정 상세는 _open_view로 히스토리를 쌓는다."""
    st.session_state.phase = phase
    if phase == "gate":
        return
    st.query_params["view"] = phase
    if st.session_state.get("pid"):
        st.query_params["pid"] = st.session_state.pid
    if phase == "hub":
        st.session_state.pop("code", None)
        _clear_param("room")
        _clear_param("case")
        _clear_param("law")
        st.session_state.case_open = ""
        st.session_state.law_open = ""
    elif phase == "cases":
        _clear_param("law")
        st.session_state.law_open = ""
    elif phase == "laws":
        _clear_param("case")
        st.session_state.case_open = ""


def _apply_browser_nav() -> None:
    """URL view/case/law/room 기준 복구. 시합 중 새로고침은 방으로 복귀."""
    case_now = _qp_one("case") or str(st.session_state.get("case_open") or "").strip()
    law_now = _qp_one("law") or str(st.session_state.get("law_open") or "").strip()
    # JS에 직접 넘겨 주소 반영 전에도 목록→상세 스택을 쌓는다.
    _gate_js(
        f"""
        var app = window.parent;
        try {{
          if (!app || !app.location || String(app.location.pathname||"").indexOf("/~/+/") < 0) {{
            if (window.top && window.top.document) {{
              var f = window.top.document.querySelector('iframe[title=streamlitApp]');
              if (f && f.contentWindow) app = f.contentWindow;
            }}
          }}
        }} catch (e) {{}}
        try {{ app.__battleLockOn = false; app.__battleNavBoot = false; }} catch (e) {{}}
        try {{
          if (app && !app.__battlePopV4) {{
            app.__battlePopV4 = true;
            app.addEventListener("popstate", function () {{
              try {{
                var q = app.location.search || "";
                if (window.top && window.top !== app) {{
                  window.top.location.replace(window.top.location.pathname + q);
                  return;
                }}
              }} catch (e) {{}}
              try {{ app.location.reload(); }} catch (e) {{}}
            }});
          }}
          if (app && app.location) {{
            var forceCase = "{case_now}";
            var forceLaw = "{law_now}";
            var u = new URL(app.location.href);
            if (forceCase) u.searchParams.set("case", forceCase);
            else u.searchParams.delete("case");
            if (forceLaw) u.searchParams.set("law", forceLaw);
            else u.searchParams.delete("law");
            var hasDetail = !!(forceCase || forceLaw);
            if (hasDetail) {{
              var detailUrl = u.pathname + u.search;
              var shellQ = u.search;
              u.searchParams.delete("case");
              u.searchParams.delete("law");
              var listUrl = u.pathname + u.search;
              var key = "battleNavStacked:" + detailUrl;
              try {{
                if (app.sessionStorage.getItem(key) !== "1") {{
                  app.sessionStorage.setItem(key, "1");
                  app.history.replaceState({{battleNav: "list"}}, "", listUrl);
                  app.history.pushState({{battleNav: "detail"}}, "", detailUrl);
                  try {{
                    if (window.top && window.top !== app) {{
                      window.top.history.replaceState({{battleNav: "detail"}}, "", window.top.location.pathname + shellQ);
                    }}
                  }} catch (e) {{}}
                }}
              }} catch (e) {{}}
            }} else {{
              try {{
                var rm = [];
                for (var i = 0; i < app.sessionStorage.length; i++) {{
                  var k = app.sessionStorage.key(i);
                  if (k && k.indexOf("battleNavStacked:") === 0) rm.push(k);
                }}
                rm.forEach(function (k) {{ app.sessionStorage.removeItem(k); }});
              }} catch (e) {{}}
            }}
          }}
        }} catch (e) {{}}
        """
    )

    kind = _qp_one("kind")
    if kind in ("exam", "ox"):
        st.session_state.quiz_kind = kind

    code = _qp_one("room") or str(st.session_state.get("code") or "").strip()
    view = _qp_one("view")
    phase = st.session_state.get("phase") or "hub"
    pid = str(st.session_state.get("pid") or "").strip()

    # 진행·대기 중인 방: 이미 참가한 pid이거나 시합 화면이면 복귀 (튕김·새로고침)
    if code:
        room = rooms.load(code)
        if room and room.get("status") in ROOM_LIVE:
            players = room.get("players") or {}
            in_room = bool(pid and pid in players)
            want_lock = view in VIEW_LOCK or phase in VIEW_LOCK or in_room
            if want_lock and (in_room or phase in VIEW_LOCK or view in VIEW_LOCK):
                rejoined = phase not in VIEW_LOCK
                st.session_state.code = code
                st.session_state.phase = "lobby" if room.get("status") == "lobby" else "play"
                st.query_params["view"] = st.session_state.phase
                st.query_params["room"] = code
                if pid:
                    _persist_pid(pid)
                    _restore_player_from_room(room, pid)
                if rejoined and in_room:
                    st.session_state._rejoined = True
                return
            # 초대 링크만 있고 아직 미참가 → 아래에서 enter 처리

    if phase in VIEW_LOCK and st.session_state.get("code"):
        live = rooms.load(str(st.session_state.get("code") or ""))
        if live and live.get("status") in ROOM_LIVE:
            if view != phase:
                st.query_params["view"] = phase
            st.query_params["room"] = str(st.session_state.code)
            if pid:
                _persist_pid(pid)
            return
        st.session_state.pop("code", None)
        st.session_state.phase = "enter"
        st.query_params["view"] = "enter"
        return

    if view in VIEW_FREE:
        st.session_state.phase = view
        if view == "hub":
            st.session_state.pop("code", None)
            _clear_param("room")
            _clear_param("case")
            _clear_param("law")
            st.session_state.case_open = ""
            st.session_state.law_open = ""
        elif view == "cases":
            _clear_param("law")
            st.session_state.law_open = ""
            st.session_state.case_open = _qp_one("case")
        elif view == "laws":
            _clear_param("case")
            st.session_state.case_open = ""
            st.session_state.law_open = _qp_one("law")
        return

    # view 없음 + 방 번호만(대기 전 초대 링크) → 입장
    if _qp_one("room"):
        st.session_state.phase = "enter"
        st.query_params["view"] = "enter"
        return

    st.session_state.phase = "hub"
    st.session_state.pop("code", None)
    _clear_param("room")
    _clear_param("case")
    _clear_param("law")
    st.session_state.case_open = ""
    st.session_state.law_open = ""
    st.query_params["view"] = "hub"


def _do_leave_to_enter() -> None:
    st.session_state.pop("code", None)
    _drop_room()
    _goto("enter")
    st.rerun()


@st.dialog("나가기")
def _leave_quiz_dialog() -> None:
    st.write("문제를 그만 푸실건가요?")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("계속 풀기", use_container_width=True, key="leave_dlg_stay"):
            st.rerun()
    with c2:
        if st.button("나가기", type="primary", use_container_width=True, key="leave_dlg_go"):
            _do_leave_to_enter()


def _ask_leave_quiz() -> None:
    _leave_quiz_dialog()


def _mark_gate() -> None:
    """URL에 만료시각을 남긴다. 매 클릭마다 바꾸면 뒤로가기가 막히므로, 없거나 임박할 때만 갱신."""
    now = int(time.time())
    raw = str(st.query_params.get("in") or "").strip()
    need = True
    if raw and raw != "1":
        try:
            exp = int(raw)
            # 남은 시간이 절반 이상이면 URL을 건드리지 않는다 (히스토리 오염 방지)
            if exp - now > GATE_TTL_SEC // 2:
                need = False
        except ValueError:
            need = True
    if need:
        st.query_params["in"] = str(now + GATE_TTL_SEC)
    _gate_js(
        f"""
        var KEY = "{GATE_STORE}";
        var w = window.parent;
        try {{ w.sessionStorage.setItem(KEY, "1"); }} catch (e) {{}}
        try {{
          var secure = (w.location.protocol === "https:") ? "; Secure" : "";
          w.document.cookie = KEY + "=1; path=/; max-age={GATE_TTL_SEC}; SameSite=Lax" + secure;
        }} catch (e) {{}}
        """
    )


def _gate_valid() -> bool:
    raw = str(st.query_params.get("in") or "").strip()
    if not raw:
        return False
    # 예전 영구 플래그(?in=1)는 더 이상 통과시키지 않는다.
    if raw == "1":
        _clear_param("in")
        return False
    try:
        return int(raw) >= int(time.time())
    except ValueError:
        _clear_param("in")
        return False


def _bridge_gate_from_storage() -> None:
    """쿠키/sessionStorage만 있고 URL 출입이 없을 때 복구한다."""
    _gate_js(
        f"""
        var KEY = "{GATE_STORE}";
        var w = window.parent;
        var url = new URL(w.location.href);
        var ok = false;
        try {{ ok = w.sessionStorage.getItem(KEY) === "1"; }} catch (e) {{}}
        if (!ok) {{
          try {{
            ok = ("; " + w.document.cookie).indexOf("; " + KEY + "=1") !== -1;
          }} catch (e) {{}}
        }}
        if (!ok) return;
        if (url.searchParams.get("g") === "1") return;
        url.searchParams.set("g", "1");
        w.location.replace(url.toString());
        """
    )


if "pid" not in st.session_state:
    restored = _qp_one("pid") or _cookie_pid()
    st.session_state.pid = restored if len(restored) >= 8 else uuid.uuid4().hex[:10]
if "phase" not in st.session_state:
    st.session_state.phase = "hub"
if "unlocked" not in st.session_state:
    st.session_state.unlocked = False

if _gate_valid() or _cookie_gate_on() or st.query_params.get("g") == "1":
    st.session_state.unlocked = True
    _clear_param("g")


def _mast(sub: str, title: str = APP_TITLE, tags: list[str] | None = None) -> None:
    chips = "".join(f"<span>{html.escape(t)}</span>" for t in (tags or []))
    tagbox = f"<div class='tags'>{chips}</div>" if chips else ""
    if title == APP_TITLE:
        head = '실무역량 평가 다통과 <span class="battle">: The Battle</span>'
    else:
        head = html.escape(glue_kr(title))
    st.markdown(
        f"""
        <div class="mast">
          <div class="mast-body">
            <div class="mast-meta">
              <span class="brand"><span class="mark"></span><span class="brand-name">The Battle</span></span>
            </div>
            <h1>{head}</h1>
            <p>{html.escape(glue_kr(sub))}</p>
            {tagbox}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_header(phase: str) -> None:
    if phase == "hub":
        _mast(
            "지역경찰 상시교육 활성화와 팀워크 향상 및 현장 역량 강화를 위한 웹앱",
            tags=["방 번호 4자리로 합류", "개인전", "단체전", "서바이벌", "전국 지역관서별 대결 가능"],
        )
    elif phase == "cases":
        _mast("법원이 경찰 전용으로 나눠 주지 않습니다. 현장 법령·쟁점으로 법제처 공식 판례만 가져옵니다.", "최신판례")
    elif phase == "laws":
        _mast("소관부처가 경찰청인 법령만 가져옵니다. 형소법처럼 다른 부처 소관은 여기 없습니다.", "법률개정")
    elif phase in ("lobby", "play"):
        _mast_slim("실무역량평가 OX" if st.session_state.get("quiz_kind") == "ox" else EXAM_TITLE)
    elif st.session_state.get("quiz_kind") == "ox":
        _mast("공식 보기 한 줄이 맞는지 O/X로 풉니다. 몇 개를 묻는 문제는 숫자를 넣습니다.", "실무역량평가 OX")
    else:
        _mast("방장이 주제와 방식을 정하고, 들어온 사람을 확인한 뒤 시작합니다.", APP_TITLE)


def _mast_slim(title: str, right: str = "") -> None:
    right_html = f"<span class='mast-right'>{html.escape(right)}</span>" if right else ""
    # Streamlit이 깊게 중첩된 div를 깨뜨려 </div>가 글자로 보이는 경우가 있어 평평하게 쓴다.
    st.markdown(
        f"<div class='mast slim'><span class='brand'><span class='mark'></span>"
        f"<span class='brand-name'>The Battle</span>"
        f"<span class='slim-title'>{html.escape(title)}</span></span>{right_html}</div>",
        unsafe_allow_html=True,
    )


def _svc_card(title: str, body: str, no: str, lead: bool = False) -> None:
    cls = "svc lead" if lead else "svc"
    st.markdown(
        f"<div class='{cls}'><span class='svc-no'>{html.escape(no)}</span>"
        f"<h3>{html.escape(glue_kr(title))}</h3><p>{html.escape(glue_kr(body))}</p></div>",
        unsafe_allow_html=True,
    )


def _sect(title: str, note: str = "") -> None:
    st.markdown(
        f"<div class='sect'><strong>{html.escape(glue_kr(title))}</strong>"
        f"<span>{html.escape(glue_kr(note))}</span></div>",
        unsafe_allow_html=True,
    )


SIDE_CLASS = {"홍팀": "red", "청팀": "blue"}


def gate_screen() -> None:
    _mast(
        "지역경찰 상시교육 활성화와 팀워크 향상 및 현장 역량 강화를 위한 웹앱",
        tags=["실무역량평가 문제은행", "개인전 · 단체전", "스피드전 · 서바이벌", "법제처 공식 판례 · 개정"],
    )
    g1, g2 = st.columns(2, gap="medium")
    with g1:
        _svc_card(EXAM_TITLE, EXAM_DESC, "01")
    with g2:
        _svc_card("실무역량평가 OX", OX_DESC, "02")
    g3, g4 = st.columns(2, gap="medium")
    with g3:
        _svc_card("최신판례", "음주운전·폭행·가정폭력 등 현장 쟁점으로 법제처 공식 판례만 제공", "03")
    with g4:
        _svc_card("법률개정", "경찰청 소관 법령의 공포·시행·제개정만 제공", "04")
    _sect("내부 출입", "비밀번호를 넣으십시오.")
    with st.form("gate_form", clear_on_submit=False):
        pw = st.text_input("비밀번호", placeholder="비밀번호")
        submitted = st.form_submit_button("출입", type="primary")
    if submitted:
        if (pw or "").strip() == GATE_PASSWORD:
            st.session_state.unlocked = True
            st.session_state.phase = "hub"
            _mark_gate()
            st.rerun()
        else:
            st.error("비밀번호가 맞지 않습니다.")
    st.caption("외부 반출 금지. 내부 연습용입니다.")


if not st.session_state.unlocked:
    _bridge_gate_from_storage()
    gate_screen()
    st.stop()

# 쓰는 동안 만료를 밀어 새로고침·연속 사용 시 끊기지 않게 한다.
_mark_gate()

# URL view= / 브라우저 뒤로가기 동기화 · 단체전 재접속
_apply_browser_nav()
if st.session_state.get("pid"):
    # 시합 중이거나 URL에 방이 있을 때만 pid를 강하게 유지
    if st.session_state.get("phase") in VIEW_LOCK or _qp_one("room"):
        _persist_pid(st.session_state.pid)

choices = area_choices()
labels = [c[1] for c in choices]
by_label = {c[1]: c for c in choices}


def current_item(deck: list[dict], idx: int) -> dict | None:
    if idx < 0 or idx >= len(deck):
        return None
    ref = deck[idx]
    if ref.get("q") and ref.get("choices") is not None:
        return ref
    return item_at(ref["area_id"], ref["i"])


def show_standings_board(
    kind: str,
    mode: str,
    viewer: tuple[str, str] | None = None,
    title: str = "랭킹",
    scope: str = "cumul",
) -> None:
    scope = "single" if scope == "single" else "cumul"
    rows = standings.board(kind=kind, mode=mode, limit=10, viewer=viewer, scope=scope)
    if not rows:
        st.caption("이 종목·방식으로 끝난 판이 아직 없습니다. 한 판이 끝나면 여기에 쌓입니다.")
        return
    top = max(int(r.get("points") or 0) for r in rows) or 1
    out = []
    prev = 0
    for r in rows:
        rank = int(r.get("rank") or 0)
        if prev and rank > prev + 1:
            out.append("<div class='rank-gap'>···</div>")
        cls = "rank-row me" if r.get("self") else "rank-row"
        pos = f"pos p{rank}" if rank <= 3 else "pos"
        if scope == "single":
            streak = int(r.get("best_streak") or 0)
            streak_bit = f" · 최고 {streak}연속" if streak >= 2 else ""
            meta = f"<span class='meta-bit'> · 한 판 최고{streak_bit}</span>"
            val = f"{int(r.get('points') or 0)}점<small>맞힘 {int(r.get('score') or 0)}개</small>"
        else:
            meta = (
                f"<span class='meta-bit'> · {int(r.get('games') or 0)}판"
                f" · 1등 {int(r.get('wins') or 0)}회</span>"
            )
            val = f"{int(r.get('points') or 0)}점<small>{int(r.get('score') or 0)}개</small>"
        out.append(
            f"<div class='{cls}'><span class='{pos}'>{rank}</span>"
            f"<span class='who'><b>{html.escape(r.get('name') or '')}</b>"
            f"<small>{_org_rank_spans(r.get('org') or '')}{meta}</small></span>"
            f"<span class='rbar'><i style='width:{max(2, min(100, int(100 * int(r.get('points') or 0) / top)))}%'></i></span>"
            f"<span class='val'>{val}</span></div>"
        )
        prev = rank
    if title:
        if scope == "single":
            note = "한 판에서 낸 최고 점수 기준입니다. 10위까지 공개합니다."
        else:
            note = "여러 판을 합친 누적 점수 기준입니다. 10위까지 공개합니다."
        if viewer and any(int(r.get("rank") or 0) > 10 for r in rows):
            note = note.replace("10위까지 공개합니다.", "10위까지 공개하고, 지금 푼 사람의 자리만 아래에 붙입니다.")
        _sect(title, note)
    st.markdown("<div class='rank'>" + "".join(out) + "</div>", unsafe_allow_html=True)


def show_teams(room: dict) -> None:
    if not room.get("team_battle"):
        return
    rows = rooms.team_ranking(room)
    if not rows:
        return
    speed = rooms.mode_of(room) == "speed"
    surv = rooms.mode_of(room) == "survival"
    order = {r["side"]: r for r in rows}
    cells = []
    for side in rooms.SIDES:
        r = order.get(side) or {"side": side, "n": 0, "score": 0, "points": 0, "alive": 0}
        big = r["points"] if speed else r["score"]
        unit = "점" if speed else "개"
        sub = f"{r['n']}명 · 생존 {r['alive']}명" if surv else f"{r['n']}명"
        cells.append(
            f"<div class='team {SIDE_CLASS[side]}'><b>{side}</b>"
            f"<strong>{big}<span style='font-size:1rem'> {unit}</span></strong><span>{sub}</span></div>"
        )
    st.markdown("<div class='teams'>" + cells[0] + "<div class='vs'>VS</div>" + cells[1] + "</div>", unsafe_allow_html=True)


def _fmt_ms(ms: int) -> str:
    if int(ms or 0) <= 0:
        return ""
    s = int(ms) / 1000
    if s < 60:
        return f"{s:.1f}초"
    return f"{int(s) // 60}분 {int(s) % 60}초"


def show_ranking(room: dict, pid: str, title: str = "실시간 순위") -> None:
    total = len(room.get("deck") or []) or 1
    mode = rooms.mode_of(room)
    rows = rooms.ranking(room)
    top = max([r["points"] for r in rows] or [0]) or 1
    _sect(title, f"{len(rows)}명 · {rooms.MODES[mode][0]}")
    show_teams(room)
    out = []
    for i, r in enumerate(rows, 1):
        cls = "rank-row me" if r["pid"] == pid else "rank-row"
        pos = f"pos p{i}" if i <= 3 else "pos"
        side = f"<em class='{SIDE_CLASS[r['side']]}'>{r['side'][0]}</em>" if r["side"] in SIDE_CLASS else ""
        if mode == "survival" and r["out"]:
            state = f"탈락 · {r['idx']}번에서 멈춤"
        elif rooms.relay_on(room):
            asked = int(((room.get("relay") or {}).get("asked") or {}).get(r["pid"], 0))
            now_pid = ((room.get("relay") or {}).get("pid") or "")
            if r["pid"] == now_pid:
                state = "지금 차례"
            elif r["done"]:
                state = "완료"
            else:
                state = f"{asked}문제 담당 · 대기"
        elif r["done"]:
            state = "완료"
        else:
            state = f"{min(r['idx'] + 1, total)}번 푸는 중"
        if r["best"] >= 3:
            state += f" · 최고 {r['best']}연속"
        clock = _fmt_ms(int(r.get("ms") or 0))
        if clock:
            state += f" · {clock}"
        if mode == "speed":
            big, small = f"{r['points']}점", f"{r['score']}/{total}개"
            width = int(100 * r["points"] / top)
        else:
            big, small = f"{r['score']}/{total}", f"{r['points']}점"
            width = int(100 * r["score"] / total)
        org_html = _org_rank_spans(r.get("org") or {})
        if org_html:
            detail = f"{org_html}<span class='meta-bit'> · {html.escape(state)}</span>"
        else:
            detail = f"<span class='meta-bit'>{html.escape(state)}</span>"
        out.append(
            f"<div class='{cls}'><span class='{pos}'>{i}</span>"
            f"<span class='who'><b>{html.escape(r['name'])}{side}</b><small>{detail}</small></span>"
            f"<span class='rbar'><i style='width:{max(2, min(100, width))}%'></i></span>"
            f"<span class='val'>{big}<small>{small}</small></span></div>"
        )
    st.markdown("<div class='rank'>" + "".join(out) + "</div>", unsafe_allow_html=True)


def show_review(history: list | None, deck: list[dict]) -> None:
    wrong = [h for h in (history or []) if not h.get("ok")]
    with st.expander(f"결과보기 · 틀린 문제 {len(wrong)}개", expanded=False):
        if not wrong:
            st.write("틀린 문제가 없습니다.")
            return
        for h in wrong:
            item = current_item(deck, int(h["idx"]))
            if item is None:
                continue
            if item.get("ox"):
                st.write(f"**{int(h['idx']) + 1}.** {glue_kr(item.get('ask') or '아래 설명이 맞으면 O, 틀리면 X.')}")
                if item.get("ctx"):
                    st.caption(glue_kr(item["ctx"]))
                st.write(glue_kr(item.get("q") or ""))
            else:
                st.write(f"**{int(h['idx']) + 1}.** {glue_kr(item['q'])}")
            pick_i = int(h["choice"])
            ans_i = int(h["answer"])
            if item.get("kind") == "num":
                mark_m = "시간 초과" if pick_i < 0 else str(pick_i)
                mark_a = str(ans_i)
            elif item.get("ox"):
                mark_m = "시간 초과" if pick_i < 0 else item["choices"][pick_i]
                mark_a = item["choices"][ans_i]
            else:
                mark_m = "시간 초과" if pick_i < 0 else f"{circle(pick_i)} {item['choices'][pick_i]}"
                mark_a = f"{circle(ans_i)} {item['choices'][ans_i]}"
            st.markdown(
                f"<div class='bad'>내 답 {html.escape(glue_kr(mark_m))}</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div class='ok'>정답 {html.escape(glue_kr(mark_a))}</div>",
                unsafe_allow_html=True,
            )
            if item.get("exp"):
                st.caption(glue_kr(item["exp"]))
            if item.get("src"):
                st.caption("출처: " + glue_kr(item["src"]))


def render_question(item: dict, qn: int, total: int, double: bool = False) -> None:
    tag = "<span class='x2tag'>찬스 문제 · 점수 2배</span>" if double else ""
    if item.get("ox"):
        ask = html.escape(item.get("ask") or "아래 설명이 맞으면 O, 틀리면 X.")
        ctx = html.escape(item.get("ctx") or "").replace("\n", "<br>")
        say = html.escape(item.get("q") or "").replace("\n", "<br>")
        body = f"<p class='ox-ask'>{ask}</p>"
        if item.get("ctx"):
            body += f"<p class='ox-ctx'>{ctx}</p>"
        body += f"<p class='ox-say'>{say}</p>"
    else:
        body = f"<div class='stem'>{html.escape(item['q']).replace(chr(10), '<br>')}</div>"
    st.markdown(
        f"<div class='qbox{' x2' if double else ''}'>"
        f"<div class='meta'><span>{html.escape(item['area'])} · {qn}/{total}</span>{tag}</div>"
        f"{body}</div>",
        unsafe_allow_html=True,
    )


def pick_choice(item: dict, key: str, selected: int | None = None) -> int | None:
    """다통과(Police_Exam)와 같이 st.radio로 보기를 보여 한글 줄바꿈을 지킨다."""
    if item.get("ox"):
        st.markdown("<div class='ox-mark'></div>", unsafe_allow_html=True)
        cols = st.columns(2, gap="medium")
        for i, c in enumerate(item["choices"][:2]):
            with cols[i]:
                kind = "primary" if selected is not None and i == selected else "secondary"
                if st.button(c, key=f"{key}_{i}", type=kind):
                    return i
        return None
    choices = item["choices"]
    st.markdown("<div class='choice-mark'></div>", unsafe_allow_html=True)
    picked = st.radio(
        "보기",
        options=list(range(len(choices))),
        format_func=lambda i, ch=choices: f"{circle(i)} {ch[i]}",
        index=selected if selected is not None else None,
        key=key,
        label_visibility="collapsed",
    )
    if picked is None:
        return None
    if selected is not None and int(picked) == int(selected):
        return None
    return int(picked)


def pick_org() -> dict:
    cheongs = agencies()
    if not cheongs:
        st.error("관서 목록을 읽지 못했습니다.")
        return {}
    agency = st.selectbox(
        "시도청",
        ["", *cheongs],
        format_func=lambda x: "시도청을 고르십시오" if not x else agency_label(x),
        key="org_agency",
    )
    if not agency:
        return {"agency": "", "station": "", "unit": "", "team": ""}
    st_list = stations(agency)
    if not st_list:
        st.warning("이 청에 경찰서가 없습니다.")
        return {"agency": agency, "station": "", "unit": "", "team": ""}
    station = st.selectbox(
        "경찰서",
        ["", *st_list],
        format_func=lambda x: "경찰서를 고르십시오" if not x else station_label(x),
        key=f"org_station_{agency}",
    )
    if not station:
        return {"agency": agency, "station": "", "unit": "", "team": ""}
    unit_list = units(agency, station)
    if not unit_list:
        st.warning("이 서에 지구대·파출소가 없습니다.")
        return {"agency": agency, "station": station, "unit": "", "team": ""}
    unit = st.selectbox(
        "지구대·파출소",
        ["", *unit_list],
        format_func=lambda x: "지구대·파출소를 고르십시오" if not x else x,
        key=f"org_unit_{agency}_{station}",
    )
    if not unit:
        return {"agency": agency, "station": station, "unit": "", "team": ""}
    team_pick = st.selectbox("팀", ["", *TEAMS], format_func=lambda x: "팀을 고르십시오" if not x else x, key="org_team")
    if not team_pick:
        return {"agency": agency, "station": station, "unit": unit, "team": ""}
    if team_pick == "기타":
        team = st.text_input("팀 이름", value=st.session_state.get("team_custom") or "").strip()
        st.session_state.team_custom = team
    else:
        team = team_pick
    return {"agency": agency, "station": station, "unit": unit, "team": team}


def _go_room(room: dict) -> None:
    st.session_state.code = room["code"]
    deck0 = (room.get("deck") or [{}])[0]
    if room.get("kind") == "ox" or deck0.get("ox") or deck0.get("kind") == "num":
        st.session_state.quiz_kind = "ox"
    st.query_params["room"] = room["code"]
    _persist_pid(st.session_state.pid)
    _goto("lobby" if room.get("status") == "lobby" else "play")
    st.rerun()


def _org_caption(room: dict, pid: str) -> str:
    mine = rooms.player_org(room, pid)
    host = room.get("org") or {}
    mine_t = path_text(mine)
    host_t = path_text(host)
    if mine_t and host_t and org_key(mine) != org_key(host):
        return f"내 소속 · {mine_t} · 방장 {host_t}"
    return mine_t or host_t or ""


def _short_org(org: dict | None) -> str:
    """모바일용 짧은 소속. 지구대 이름이 겹칠 수 있어 경찰서·지구대·팀을 쓴다."""
    o = org or {}
    station = station_label(o.get("station") or "") or ""
    unit = o.get("unit") or ""
    team = o.get("team") or ""
    agency = agency_label(o.get("agency") or "") or ""
    bits = [station or agency, unit, team]
    line = " · ".join(x for x in bits if x)
    return line or path_text(o)


def _short_org_text(line: str) -> str:
    """path_text 문자열용. 시도청만 빼고 경찰서·지구대·팀을 남긴다."""
    bits = [b.strip() for b in (line or "").split("·") if b.strip()]
    if len(bits) >= 4:
        return " · ".join(bits[1:])
    if len(bits) == 3:
        return " · ".join(bits)
    return (line or "").strip()


def _org_rank_spans(org: dict | str | None) -> str:
    """PC는 전체 소속, 모바일은 짧은 소속(CSS로 전환)."""
    if isinstance(org, dict):
        full = path_text(org)
        short = _short_org(org) or full
    else:
        full = (org or "").strip()
        short = _short_org_text(full) or full
    if not full:
        return ""
    return (
        f"<span class='org-full'>{html.escape(full)}</span>"
        f"<span class='org-short'>{html.escape(short)}</span>"
    )


def _law_oc() -> str:
    try:
        return str(st.secrets.get("law_oc") or "").strip()
    except Exception:
        return ""


def hub_screen() -> None:
    _sect("VS 모드", "팀원 1명이 방을 만들고, 나머지 팀원은 방 번호로 들어갑니다.")
    r1a, r1b = st.columns(2, gap="medium")
    with r1a:
        with st.container(border=True):
            _svc_card(EXAM_TITLE, EXAM_DESC, "01")
            if st.button("시작하기", type="primary", key="hub_exam", use_container_width=True):
                st.session_state.quiz_kind = "exam"
                _goto("enter")
                st.rerun()
    with r1b:
        with st.container(border=True):
            _svc_card("실무역량평가 OX", OX_DESC, "02")
            if st.button("시작하기", type="primary", key="hub_ox", use_container_width=True):
                st.session_state.quiz_kind = "ox"
                _goto("enter")
                st.rerun()
    _sect("학습하기", "개인 학습·모의고사로 바로 이어집니다.")
    r_learn_a, r_learn_b = st.columns(2, gap="medium")
    with r_learn_a:
        with st.container(border=True):
            _svc_card(
                "폴러닝(경찰청 지역경찰역량강화과 제작)",
                "지역경찰 현장실무기초 14종, 법령·문제은행 등 학습",
                "03",
            )
            st.link_button("폴러닝 열기", "https://pol-learning.web.app", type="primary", use_container_width=True)
    with r_learn_b:
        with st.container(border=True):
            _svc_card(
                "실무역량평가 다통과(실전 모의고사)",
                "실무역량평가 대비 실전 모의고사로 최종 점검",
                "04",
            )
            st.link_button(
                "모의고사 열기",
                "https://tragedynight-dotcom.github.io/Police_Exam/",
                type="primary",
                use_container_width=True,
            )
    _sect("최신판례 및 법률 개정 확인하기")
    r2a, r2b = st.columns(2, gap="medium")
    with r2a:
        with st.container(border=True):
            _svc_card(
                "최신판례",
                "음주운전·폭행·가정폭력 등 현장 쟁점으로 법제처 공식 판례만 제공",
                "05",
            )
            if st.button("최신판례 열기", type="primary", key="hub_case", use_container_width=True):
                _open_view("cases")
                st.rerun()
    with r2b:
        with st.container(border=True):
            _svc_card(
                "법률개정",
                "경찰청 소관 법령의 공포·시행·제개정만 제공",
                "06",
            )
            if st.button("법률개정 열기", type="primary", key="hub_law", use_container_width=True):
                _open_view("laws")
                st.rerun()
    st.caption("최신판례·법률개정은 법제처 원문 그대로 공식 자료만 제공")
    _sect("랭킹", "누적과 단일(한 판 최고)을 나눠 봅니다. 종목·방식별로 10위까지 공개합니다.")
    rank_scope = st.radio(
        "구분",
        ["cumul", "single"],
        format_func=lambda x: "누적 랭킹" if x == "cumul" else "단일 최고 랭킹",
        horizontal=True,
        key="rank_scope",
    )
    rk1, rk2 = st.columns(2)
    with rk1:
        rank_kind = st.radio(
            "종목",
            ["exam", "ox"],
            format_func=lambda x: EXAM_TITLE if x == "exam" else "OX",
            horizontal=True,
            key="rank_kind",
        )
    with rk2:
        rank_mode = st.radio(
            "방식",
            list(rooms.MODES),
            format_func=lambda m: rooms.MODES[m][0],
            horizontal=True,
            key="rank_mode",
        )
    if rank_scope == "single":
        st.caption("한 판에서 낸 최고 점수·맞힌 개수 기준입니다. 여러 판을 합치지 않습니다.")
    else:
        st.caption("여러 판의 점수·맞힌 개수를 합친 누적 기준입니다.")
    show_standings_board(rank_kind, rank_mode, title="", scope=rank_scope)
    recent = standings.recent(6, kind=rank_kind, mode=rank_mode)
    if recent:
        st.caption(
            "최근 판 · "
            + " · ".join(
                f"{(m.get('at') or '')[5:16]} {m.get('top') or ''} ({m.get('n') or 0}명)"
                for m in recent
            )
        )
    with st.expander("랭킹 초기화", expanded=False):
        st.caption("관리자만 사용합니다. 비밀번호가 맞아야 누적 랭킹이 모두 지워집니다.")
        with st.form("rank_reset_form", clear_on_submit=True):
            reset_pw = st.text_input("초기화 비밀번호", type="password", placeholder="비밀번호")
            reset_go = st.form_submit_button("랭킹 초기화", type="primary")
        if reset_go:
            if (reset_pw or "") in RANK_RESET_PASSWORDS:
                standings.clear()
                st.success("랭킹을 초기화했습니다.")
                st.rerun()
            else:
                st.error("비밀번호가 맞지 않습니다.")


def cases_screen() -> None:
    # URL이 유일한 기준. 세션 fallback이면 뒤로가기로 case가 빠져도 요지가 남는다.
    open_id = _qp_one("case")
    st.session_state.case_open = open_id
    if open_id:
        if st.button("← 목록으로", key="cases_back_list", use_container_width=True):
            _open_view("cases")
            st.rerun()
            return
    else:
        if st.button("← 홈으로", key="cases_back_hub", use_container_width=True):
            _open_view("hub")
            st.rerun()
            return
    st.caption("출처: 법제처 국가법령정보 공동활용. 직무·교통·형사·보호 쟁점으로 대법원 공식 판례만 가져옵니다.")
    labels = [t[0] for t in precedent.FIELD_TOPICS]
    pick = st.selectbox("쟁점", labels, key="case_topic")
    jo = ""
    query = ""
    for name, spec in precedent.FIELD_TOPICS:
        if name == pick:
            jo = spec.get("jo") or ""
            query = spec.get("query") or ""
            break
    if st.session_state.get("case_topic_prev") != pick:
        st.session_state.case_topic_prev = pick
        if open_id:
            st.session_state.case_open = ""
            _clear_param("case")
            st.rerun()
            return
    criminal_only = st.checkbox("형사만 보기", value=True, key="case_criminal", help="국가배상 등 민사는 끄면 같이 나옵니다.")
    oc = _law_oc()
    if not oc:
        st.error("법제처 인증값이 없습니다.")
        return

    try:
        rows, total = _cached_prec(oc, jo, query)
    except Exception:
        st.error("법제처에서 읽지 못했습니다. 잠시 뒤 다시 하십시오.")
        return
    if criminal_only:
        rows = [r for r in rows if r.get("사건종류명") == "형사"]
    if not rows:
        st.warning("이 쟁점으로 가져온 공식 판례가 없습니다.")
        return
    st.write(f"**{pick}** · 공식 {total}건 가운데 {len(rows)}건")
    for row in rows:
        name = html.escape(glue_kr(row.get("사건명") or ""))
        meta = html.escape(
            glue_kr(
                " · ".join(x for x in (row.get("사건번호") or "", row.get("선고일자") or "", row.get("법원명") or "") if x)
            )
        )
        st.markdown(
            f"<div class='case-card'><p class='case-meta'>{meta}</p>"
            f"<p class='case-name'>{name}</p></div>",
            unsafe_allow_html=True,
        )
        rid = row.get("id") or ""
        if open_id and rid and open_id == rid:
            detail = _cached_detail(oc, rid)
            if not detail:
                st.warning("요지를 읽지 못했습니다. 원문을 여십시오.")
            else:
                if detail.get("판시사항"):
                    st.write("**판시사항**")
                    st.write(glue_kr(detail["판시사항"][:1800]))
                if detail.get("판결요지"):
                    st.write("**판결요지**")
                    st.write(glue_kr(detail["판결요지"][:1800]))
                if detail.get("참조조문"):
                    st.caption("참조조문: " + glue_kr(detail["참조조문"][:400]))
            if st.button("← 목록으로", key=f"case_close_{rid}", use_container_width=True):
                _open_view("cases")
                st.rerun()
        else:
            if st.button("요지 보기", type="primary", key=f"case_open_{rid}", use_container_width=True):
                _open_view("cases", case=rid)
                st.rerun()
        st.link_button(
            "원문 보기",
            precedent.official_link(rid, row.get("사건번호") or ""),
            use_container_width=True,
        )

def laws_screen() -> None:
    # URL이 유일한 기준. 세션 fallback이면 뒤로가기로 law가 빠져도 개정이유가 남는다.
    open_id = _qp_one("law")
    st.session_state.law_open = open_id
    if open_id:
        if st.button("← 목록으로", key="laws_back_list", use_container_width=True):
            _open_view("laws")
            st.rerun()
            return
    else:
        if st.button("← 홈으로", key="laws_back_hub", use_container_width=True):
            _open_view("hub")
            st.rerun()
            return
    st.caption("출처: 법제처. 소관부처 코드 경찰청(1320000)만 조회합니다. 개정 이유는 공식 제개정이유만 보여 줍니다.")
    hide_org = st.checkbox("직제는 빼기", value=True, key="law_hide_org")
    oc = _law_oc()
    if not oc:
        st.error("법제처 인증값이 없습니다.")
        return
    try:
        rows, total = _cached_laws(oc)
    except Exception:
        st.error("법제처에서 읽지 못했습니다. 잠시 뒤 다시 하십시오.")
        return
    if hide_org:
        rows = [r for r in rows if "직제" not in (r.get("법령명") or "")]
    if not rows:
        st.warning("경찰청 소관으로 가져온 법령이 없습니다.")
        return
    st.write(f"**경찰청 소관** · 공식 {total}건 가운데 {len(rows)}건 · 공포일 최근순")
    for row in rows:
        name = html.escape(glue_kr(row.get("법령명") or ""))
        bits = [row.get("제개정") or "", row.get("법령구분") or "", row.get("소관부처") or ""]
        meta = html.escape(
            glue_kr(
                " · ".join(
                    x
                    for x in (
                        "공포 " + (row.get("공포일자") or ""),
                        "시행 " + (row.get("시행일자") or ""),
                        " · ".join(b for b in bits if b),
                    )
                    if x and x not in ("공포 ", "시행 ")
                )
            )
        )
        st.markdown(
            f"<div class='case-card'><p class='case-meta'>{meta}</p>"
            f"<p class='case-name'>{name}</p></div>",
            unsafe_allow_html=True,
        )
        rid = row.get("id") or ""
        if open_id and rid and open_id == rid:
            detail = _cached_amend(oc, rid)
            reason = (detail.get("제개정이유") or "").strip()
            if not reason:
                st.warning("제개정이유가 없습니다. 원문을 여십시오.")
            else:
                st.write("**제개정이유**")
                st.write(glue_kr(reason[:2000]))
            if st.button("← 목록으로", key=f"law_close_{rid}", use_container_width=True):
                _open_view("laws")
                st.rerun()
        else:
            if st.button("개정 이유", type="primary", key=f"law_open_{rid}", use_container_width=True):
                _open_view("laws", law=rid)
                st.rerun()
        st.link_button(
            "원문 보기",
            precedent.official_law_link(rid, row.get("법령명") or ""),
            use_container_width=True,
        )

@st.cache_data(ttl=1800)
def _cached_prec(oc: str, jo: str, query: str) -> tuple[list[dict], int]:
    return precedent.search_precedents(oc, query=query, jo=jo, display=30)


@st.cache_data(ttl=1800)
def _cached_detail(oc: str, prec_id: str) -> dict[str, str]:
    return precedent.fetch_detail(oc, prec_id)


@st.cache_data(ttl=1800)
def _cached_laws(oc: str) -> tuple[list[dict], int]:
    return precedent.search_police_laws(oc, display=30)


@st.cache_data(ttl=1800)
def _cached_amend(oc: str, mst: str) -> dict[str, str]:
    return precedent.fetch_amend_reason(oc, mst)


def enter_screen() -> None:
    if st.button("← 홈으로", key="enter_back_hub", use_container_width=True):
        _goto("hub")
        st.rerun()
        return
    kind = "실무역량평가 OX" if st.session_state.get("quiz_kind") == "ox" else EXAM_TITLE
    _sect(kind, "시도청·경찰서·지구대·파출소·팀을 고른 뒤, 방을 열거나 방 번호로 들어옵니다.")
    org = pick_org()
    st.caption(path_text(org) if org.get("unit") and org.get("team") else "위에서 관서와 팀을 고르십시오.")

    qcode = st.query_params.get("room", "")
    with st.form("enter_form", clear_on_submit=False):
        name = st.text_input("별명", placeholder="예: 순찰이", key="player_name")
        join_code = st.text_input("방 번호", value=qcode, max_chars=4, placeholder="방장이 부른 4자리", key="join_code")
        make = st.form_submit_button("방 만들기", type="primary", use_container_width=True)
        join = st.form_submit_button("방 번호로 들어가기", use_container_width=True)
    name = (name or "").strip()
    code = str(join_code or "").strip()
    if make:
        if not name:
            st.error("별명을 넣으십시오.")
        elif not org.get("unit") or not org.get("team"):
            st.error("시도청·경찰서·지구대·팀을 고르십시오.")
        else:
            st.session_state.my_org = org
            st.session_state.host_draft = {"org": org, "name": name}
            _goto("host_setup")
            st.rerun()
    if join:
        if not name or not code:
            st.error("별명과 방 번호를 넣으십시오.")
        elif not org.get("unit") or not org.get("team"):
            st.error("시도청·경찰서·지구대·팀을 고르십시오.")
        else:
            room = rooms.join(code, st.session_state.pid, name, org)
            if room is None:
                st.error("방이 없습니다. 번호를 확인하십시오.")
            else:
                st.session_state.my_org = org
                st.session_state.player_name = name
                _persist_pid(st.session_state.pid)
                _go_room(room)


def _topic_pick() -> tuple[str, int]:
    pick = st.selectbox("주제", labels, index=0, key="host_topic")
    area_id, _area_name, nmax = by_label[pick][0], by_label[pick][1], by_label[pick][2]
    if area_id == RAND_TOPIC:
        st.caption("14개 주제 가운데 하나가 무작위로 정해집니다.")
        return area_id, 0
    if area_id == RAND_EXAM:
        st.caption("14개 주제를 섞어 20문제입니다.")
        return area_id, 20
    count = st.select_slider("문항 수", options=_count_opts(nmax), value=nmax)
    return area_id, int(count)


def _mark_chances(deck: list[dict], seed: int) -> list[dict]:
    """덱의 6분의 1을 점수 2배 찬스 문제로 찍는다."""
    rng = random.Random(seed + 91)
    n = len(deck)
    if n < 4:
        return deck
    pick = set(rng.sample(range(n), max(1, n // 6)))
    for i, row in enumerate(deck):
        row["x2"] = i in pick
    return deck


def _build_deck(area_id: str, count: int, seed: int, kind: str):
    if kind == "ox":
        return make_ox_quiz(area_id, count, seed)
    return make_quiz(area_id, count, seed)


def host_setup_screen() -> None:
    draft = st.session_state.get("host_draft") or {}
    org = draft.get("org") or {}
    name = draft.get("name") or ""
    if not name:
        _goto("enter")
        st.rerun()
        return
    kind = "ox" if st.session_state.get("quiz_kind") == "ox" else "exam"
    st.caption(path_text(org))
    _sect(f"방장 {name}", "주제와 VS 방식을 정하십시오.")
    area_id, count = _topic_pick()

    _sect("VS 방식", "")
    mode = st.radio(
        "방식",
        list(rooms.MODES),
        format_func=lambda m: rooms.MODES[m][0],
        horizontal=True,
        label_visibility="collapsed",
        key="host_mode",
    )
    desc, lim = rooms.MODES[mode][1], rooms.MODES[mode][2]
    if lim and kind == "ox":
        lim = max(12, lim - 12)
    st.caption(
        glue_kr(
            desc
            + (f" 문항당 {lim}초." if lim else " 시간 제한 없이 앞뒤로 오갈 수 있습니다.")
            + " 점수가 같으면 더 빨리 푼 쪽이 앞섭니다."
        )
    )

    _sect("편성", "")
    lineup = st.radio(
        "편성",
        ["solo", "team"],
        format_func=lambda x: "개인전" if x == "solo" else "단체전",
        horizontal=True,
        label_visibility="collapsed",
        key="host_lineup",
    )
    team_battle = lineup == "team"
    if team_battle:
        st.caption(glue_kr("단체전입니다. 한 명씩 돌아가며 문제를 풉니다. 차례가 아니면 보고 있습니다."))
    else:
        st.caption(glue_kr("들어온 사람이 같은 문제를 각자 풉니다. 맞힌 개수와 점수로 개인 순위를 냅니다."))
    chance = st.checkbox("찬스 문제 넣기 (점수 2배)", value=True, key="host_chance")
    if kind == "ox":
        st.caption(glue_kr("설명이 맞으면 O, 틀리면 X입니다. 몇 개인지 묻는 문제는 숫자를 넣습니다."))

    open_room = st.button("이 설정으로 방 열기", type="primary", use_container_width=True)
    if st.button("뒤로", key="setup_back", use_container_width=True):
        _goto("enter")
        st.rerun()
    if open_room:
        seed = random.randint(1, 10_000_000)
        deck, stored_id, shown = _build_deck(area_id, count, seed, kind)
        if chance:
            deck = _mark_chances(deck, seed)
        room = rooms.create(
            st.session_state.pid,
            name,
            stored_id,
            shown,
            len(deck),
            deck,
            org=org,
            mode=mode,
            team_battle=team_battle,
            kind=kind,
        )
        st.session_state.host_seed = seed
        st.session_state.my_org = org
        _go_room(room)


def _count_opts(nmax: int) -> list[int]:
    cap = min(int(nmax), 50)
    opts = [n for n in (5, 10, 15, 20, 25, 30, 40, 50) if n < cap]
    opts.append(cap)
    return opts


def lobby_screen() -> None:
    code = st.session_state.get("code") or ""
    room = rooms.load(code)
    if room is None:
        st.warning("방이 없어졌습니다.")
        if st.button("처음으로"):
            _goto("enter")
            st.rerun()
        return
    if room["status"] in ("countdown", "play", "done"):
        _goto("play")
        st.rerun()
        return
    pid = st.session_state.pid
    _persist_pid(pid)
    if st.session_state.pop("_rejoined", False):
        st.info("연결이 끊겼다가 같은 방으로 다시 들어왔습니다.")
    mode = rooms.mode_of(room)
    lim = rooms.limit_sec(room)
    st.caption(_org_caption(room, pid))
    st.markdown(f"<div class='codebox'>{room['code']}</div>", unsafe_allow_html=True)
    pills = [
        f"<span class='pill'>{html.escape(room['area_name'])}</span>",
        f"<span class='pill'>{room['count']}문항</span>",
        f"<span class='pill gold'>{rooms.MODES[mode][0]}</span>",
    ]
    if lim:
        pills.append(f"<span class='pill'>문항당 {lim}초</span>")
    if room.get("team_battle"):
        pills.append("<span class='pill gold'>단체전</span>")
        pills.append("<span class='pill'>한 명씩 돌아가며</span>")
    else:
        pills.append("<span class='pill gold'>개인전</span>")
    if any(d.get("x2") for d in (room.get("deck") or [])):
        pills.append("<span class='pill gold'>찬스 문제 2배</span>")
    st.markdown("".join(pills), unsafe_allow_html=True)
    if room.get("team_battle"):
        st.caption("이 번호를 불러 주십시오. 단체전입니다. 팀원이 한 명씩 돌아가며 풉니다.")
    else:
        st.caption("이 번호를 불러 주십시오. 개인전입니다. 들어온 사람이 각자 같은 문제를 풉니다.")

    is_host = pid == room["host_id"]
    if room.get("team_battle"):
        _sect("편 고르기", "누르면 바뀝니다. 방장은 한 번에 갈라 줄 수 있습니다.")
        cs = st.columns([1, 1, 1.4, 2.6])
        for i, side in enumerate(rooms.SIDES):
            with cs[i]:
                mine = (room["players"].get(pid) or {}).get("side") == side
                if st.button(side, key=f"side_{side}", type="primary" if mine else "secondary"):
                    rooms.set_side(code, pid, side)
                    st.rerun()
        if is_host:
            with cs[2]:
                if st.button("자동 편성", key="auto_side"):
                    rooms.auto_sides(code, pid)
                    st.rerun()

    @st.fragment(run_every=2)
    def wait_peers():
        live = rooms.load(code)
        if live is None:
            return
        chips = []
        for who, p in live["players"].items():
            cls = SIDE_CLASS.get(p.get("side") or "", "")
            if who == live.get("host_id"):
                cls += " host"
            label = html.escape(p.get("name") or "")
            org_line = html.escape(_short_org(rooms.player_org(live, who, p)))
            org_html = f"<span class='org'>{org_line}</span>" if org_line else ""
            chips.append(f"<span class='peer {cls}'><i></i><span>{label}{org_html}</span></span>")
        _sect(f"들어온 사람 {len(chips)}명", "방장이 시작할 때까지 기다립니다.")
        st.markdown("<div class='peers'>" + "".join(chips) + "</div>", unsafe_allow_html=True)
        if live["status"] in ("countdown", "play", "done") and st.session_state.phase == "lobby":
            _goto("play")
            st.rerun()

    wait_peers()
    if is_host:
        s1, _ = st.columns([1.6, 3.4])
        with s1:
            if st.button("시작", type="primary"):
                rooms.start(code, pid)
                _goto("play")
                st.rerun()
    else:
        st.info("방장이 시작을 누를 때까지 기다리십시오.")
    st.markdown('<div class="mini-mark"></div>', unsafe_allow_html=True)
    b1, _ = st.columns([1, 4])
    with b1:
        if st.button("나가기", key="lobby_leave"):
            _do_leave_to_enter()
    _law_brief()


def _law_brief() -> None:
    """대기하는 동안 최근 개정 법령을 읽고 갑니다."""
    oc = _law_oc()
    if not oc:
        return
    try:
        rows, _total = _cached_laws(oc)
    except Exception:
        return
    rows = [r for r in rows if "직제" not in (r.get("법령명") or "")][:3]
    if not rows:
        return
    _sect("기다리는 동안 · 최근 개정", "경찰청 소관 법령 공포 최근순")
    for r in rows:
        meta = " · ".join(
            x for x in (
                "공포 " + (r.get("공포일자") or ""),
                "시행 " + (r.get("시행일자") or ""),
                r.get("제개정") or "",
            ) if x.strip() not in ("공포", "시행", "")
        )
        st.markdown(
            f"<div class='brief'><p>{html.escape(glue_kr(meta))}</p>"
            f"<b>{html.escape(glue_kr(r.get('법령명') or ''))}</b></div>",
            unsafe_allow_html=True,
        )


def _hud(room: dict, me: dict, idx: int, total: int, pos: int, n_players: int, left: float | None, lim: int) -> None:
    pct = int(100 * idx / max(1, total))
    chips = [
        f"<span class='chip'>문항<b>{min(idx + 1, total)}/{total}</b></span>",
        f"<span class='chip'>점수<b>{int(me.get('points') or 0)}</b></span>",
        f"<span class='chip'>맞힘<b>{int(me.get('score') or 0)}</b></span>",
    ]
    streak = int(me.get("streak") or 0)
    if streak >= 2:
        chips.append(f"<span class='chip hot'>{streak}연속</span>")
    side = me.get("side") or ""
    if side:
        chips.append(f"<span class='chip'>{html.escape(side)}</span>")
    chips.append("<span class='grow'></span>")
    chips.append(f"<span class='chip gold'>내 순위<b>{pos}위 / {n_players}명</b></span>")
    tmr = ""
    if lim and left is not None:
        w = max(0.0, min(100.0, 100.0 * left / lim))
        tmr = f"<div class='tmr'><i style='--w:{w:.1f}%; animation-duration:{max(0.1, left):.1f}s'></i></div>"
    st.markdown(
        f"<div class='hud'><div class='prog'><i style='width:{pct}%'></i></div>"
        f"<div class='hud-row'>{''.join(chips)}</div>{tmr}</div>",
        unsafe_allow_html=True,
    )


def _advance(code: str, pid: str, idx: int, total: int) -> bool:
    """다음 문항으로. 마지막이면 끝냈는지 확인한다."""
    if idx + 1 < total:
        rooms.seek(code, pid, idx + 1)
        return True
    rooms.finish(code, pid)
    live = rooms.load(code) or {}
    return bool((live.get("players") or {}).get(pid, {}).get("done"))


def _beep(kind: str) -> None:
    n = int(st.session_state.get("_sfx_n") or 0) + 1
    st.session_state["_sfx_n"] = n
    st.session_state["_pending_sfx"] = (kind, f"{kind}-{n}")


def _cheer(ok: bool, streak: int) -> None:
    """맞힘·연속 정답 때 직접 만든 신호음과 화면 이펙트를 한 번 올린다."""
    n = int(streak or 0)
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
    _beep(kind)
    st.session_state["_pending_fx"] = {"ok": bool(ok), "streak": n}


def _react_answer(code: str, pid: str) -> None:
    live = rooms.load(code) or {}
    me = (live.get("players") or {}).get(pid) or {}
    hist = me.get("history") or []
    ok = bool(hist[-1].get("ok")) if hist else False
    _cheer(ok, int(me.get("streak") or 0))


def _show_fx() -> None:
    fx = st.session_state.pop("_pending_fx", None)
    pending = st.session_state.pop("_pending_sfx", None)
    if pending:
        sfx.play(pending[0], pending[1])
    if not fx:
        return
    ok = bool(fx.get("ok"))
    n = int(fx.get("streak") or 0)
    if ok:
        cls = "fx-pop"
        if n >= 5:
            cls += " hot big"
        elif n >= 2:
            cls += " hot"
        title = f"{n}연속" if n >= 2 else "맞힘"
        note = "연속으로 맞혔습니다" if n >= 2 else "정답입니다"
        sparks = "".join(
            f"<i class='fx-spark' style='--dx:{dx}px;--dy:{dy}px'></i>"
            for dx, dy in ((-90, -40), (80, -50), (-70, 55), (95, 40), (0, -80), (-40, 70), (50, 75))
        )
        rings = "<i class='fx-ring'></i>" + ("<i class='fx-ring r2'></i>" if n >= 3 else "")
        flash = "<div class='fx-flash'></div>"
    else:
        cls = "fx-pop miss"
        title = "아쉽"
        note = "다음 문항에서 다시"
        sparks = ""
        rings = ""
        flash = "<div class='fx-flash miss'></div>"
    st.markdown(
        f"<div class='fx-layer'>{flash}{rings}{sparks}"
        f"<div class='{cls}'><b>{html.escape(title)}</b><span>{html.escape(note)}</span></div></div>",
        unsafe_allow_html=True,
    )


def done_screen(room: dict, pid: str, deck: list[dict], total: int) -> None:
    code = room["code"]
    me = room["players"][pid]
    mode = rooms.mode_of(room)
    sfx.play("done", f"{code}-{room.get('round') or 1}-done-{pid}")
    if mode == "survival" and me.get("out"):
        st.error(f"탈락. {int(me.get('score') or 0)}문제까지 살아남았습니다.")
    else:
        st.success(f"끝. {int(me.get('score') or 0)}/{total}개 맞히고 {int(me.get('points') or 0)}점입니다.")
    best = int(me.get("best") or 0)
    if best >= 3:
        st.caption(f"최고 {best}문제 연속으로 맞혔습니다.")

    @st.fragment(run_every=2)
    def live_rank():
        live = rooms.load(code)
        if live is None:
            return
        all_done = all(p.get("done") for p in live["players"].values())
        show_ranking(live, pid, "최종 순위" if all_done else "실시간 순위")
        if all_done:
            me_live = (live.get("players") or {}).get(pid) or {}
            viewer = ((me_live.get("name") or ""), path_text(rooms.player_org(live, pid, me_live)))
            kind = live.get("kind") or "exam"
            mode = rooms.mode_of(live)
            show_standings_board(kind, mode, viewer=viewer, title="누적 랭킹", scope="cumul")
            show_standings_board(kind, mode, viewer=viewer, title="단일 최고 랭킹", scope="single")
        if not all_done:
            st.caption("아직 푸는 사람이 있습니다.")

    live_rank()
    show_review(me.get("history"), deck)

    if pid == room.get("host_id"):
        _sect("방장 · 한 판 더", "같은 방 번호 그대로 이어서 합니다.")
        h1, h2 = st.columns(2)
        with h1:
            if st.button("새 문제로 한 판 더", type="primary", key="again_new"):
                seed = random.randint(1, 10_000_000)
                kind = room.get("kind") or "exam"
                new_deck, _sid, _shown = _build_deck(room["area_id"], room["count"], seed, kind)
                if any(d.get("x2") for d in deck):
                    new_deck = _mark_chances(new_deck, seed)
                rooms.restart(code, pid, new_deck)
                st.rerun()
        with h2:
            bad = rooms.wrong_indices(room)
            if st.button(f"틀린 문제만 다시 ({len(bad)}개)", disabled=not bad, key="again_wrong"):
                rooms.restart(code, pid, [deck[i] for i in bad])
                st.rerun()

    st.markdown('<div class="mini-mark"></div>', unsafe_allow_html=True)
    b1, _ = st.columns([1, 4])
    with b1:
        if st.button("나가기", key="done_leave"):
            _do_leave_to_enter()


def _turn_banner(room: dict, pid: str) -> None:
    rel = room.get("relay") or {}
    side = rel.get("side") or ""
    batter = rel.get("pid") or ""
    name = ((room.get("players") or {}).get(batter) or {}).get("name") or ""
    cls = SIDE_CLASS.get(side, "wait")
    mine = batter == pid
    nxt = []
    for s in rooms.SIDES:
        row = rooms.lineup(room, s)
        cur = int((rel.get("cursor") or {}).get(s) or 0)
        if not row:
            continue
        nxt_pid = row[cur % len(row)]
        nxt_name = ((room.get("players") or {}).get(nxt_pid) or {}).get("name") or ""
        if nxt_name:
            nxt.append(f"{s} 다음 {nxt_name}")
    hint = "당신 차례입니다. 답을 고르십시오." if mine else "보고 계십시오. 답을 고르지 않습니다."
    extra = " · ".join(nxt)
    st.markdown(
        f"<div class='seat {cls}'><b>지금 차례 · {html.escape(side)}</b>"
        f"<strong>{html.escape(name)}</strong><span>{html.escape(hint)}"
        f"{(' · ' + html.escape(extra)) if extra else ''}</span></div>",
        unsafe_allow_html=True,
    )
    last = rel.get("last") or {}
    if last:
        mark = "맞힘" if last.get("ok") else "틀림"
        st.caption(f"방금 {last.get('side') or ''} {last.get('name') or ''} · {mark} · {int(last.get('pts') or 0)}점")


def play_relay(room: dict, pid: str, deck: list[dict], total: int) -> None:
    """한 문항씩 홍·청이 나가고, 각 편은 들어온 순서대로 돌아간다."""
    code = room["code"]
    rel = room.get("relay") or {}
    if room.get("status") == "done" or not rel.get("pid"):
        done_screen(room, pid, deck, total)
        return
    lim = rooms.limit_sec(room)
    rnd = int(room.get("round") or 1)
    idx = int(rel.get("idx") or 0)
    item = current_item(deck, idx)
    if item is None:
        done_screen(room, pid, deck, total)
        return
    double = bool(deck[idx].get("x2"))
    batter = rel.get("pid") or ""
    me = (room.get("players") or {}).get(pid) or {}
    order = rooms.ranking(room)
    pos = next((i for i, r in enumerate(order, 1) if r["pid"] == pid), len(order))
    left = None
    if lim:
        left = max(0.0, rooms.deadline(room) - time.time())
    show_teams(room)
    _hud(room, me, idx, total, pos, len(order), left, lim)
    _turn_banner(room, pid)

    if lim:
        @st.fragment(run_every=1)
        def time_watch():
            live = rooms.load(code)
            if live is None or live.get("status") != "play":
                return
            cur = ((live.get("relay") or {}).get("pid") or "")
            cur_idx = int(((live.get("relay") or {}).get("idx") or 0))
            if cur != batter or cur_idx != idx:
                st.rerun()
                return
            secs = rooms.deadline(live) - time.time()
            if secs > 0:
                st.caption(f"남은 시간 {int(secs) + 1}초")
                return
            rooms.expire_turn(code, int(item["a"]), double=double)
            _react_answer(code, batter)
            st.rerun()

        time_watch()

    render_question(item, idx + 1, total, double)

    if pid == batter:
        pick = None
        if item.get("kind") == "num":
            st.caption("원문 그대로입니다. 숫자를 넣고 확인을 누르십시오.")
            nkey = f"num_{code}_{rnd}_{idx}"
            n1, n2, _ = st.columns([1.2, 1, 2.8])
            with n1:
                st.number_input("숫자", min_value=0, max_value=99, step=1, key=nkey, label_visibility="collapsed")
            with n2:
                if st.button("확인", type="primary", key=f"numok_{code}_{rnd}_{idx}"):
                    pick = int(st.session_state.get(nkey) or 0)
        else:
            pick = pick_choice(item, f"r_{code}_{rnd}_{idx}")
        if pick is not None:
            spent = 0
            at = rel.get("q_at")
            if at:
                try:
                    spent = int(max(0.0, time.time() - datetime.fromisoformat(at).timestamp()) * 1000)
                except Exception:
                    spent = 0
            rooms.answer(code, pid, int(pick), int(item["a"]), ms=spent, double=double)
            _react_answer(code, pid)
            st.rerun()
    else:
        if item.get("choices"):
            shown = " · ".join(
                (c if item.get("ox") else f"{circle(i)} {c}")
                for i, c in enumerate(item["choices"])
            )
            st.caption("보기 · " + shown)
        else:
            st.caption("숫자를 넣는 문제입니다. 지금 차례인 사람만 넣습니다.")

        @st.fragment(run_every=1)
        def wait_turn():
            live = rooms.load(code)
            if live is None:
                return
            nxt = ((live.get("relay") or {}).get("pid") or "")
            nidx = int(((live.get("relay") or {}).get("idx") or 0))
            if live.get("status") != "play" or nxt != batter or nidx != idx:
                st.rerun()

        wait_turn()

    st.markdown('<div class="mini-mark"></div>', unsafe_allow_html=True)
    b1, _ = st.columns([1, 4])
    with b1:
        if st.button("나가기", key="leave_relay"):
            _ask_leave_quiz()
    with st.expander("지금 순위 · 교육장 전광판", expanded=False):
        @st.fragment(run_every=2)
        def live_board():
            live = rooms.load(code)
            if live is None:
                return
            show_ranking(live, pid, "실시간 순위")

        live_board()


def play_screen() -> None:
    code = st.session_state.get("code") or ""
    room = rooms.load(code)
    if room is None:
        st.warning("진행 중이던 문제가 없어졌습니다.")
        if st.button("처음으로"):
            _goto("enter")
            st.rerun()
        return
    if room["status"] == "lobby":
        _goto("lobby")
        st.rerun()
        return
    room = rooms.begin_if_due(code) or room
    pid = st.session_state.pid
    _persist_pid(pid)
    if st.session_state.pop("_rejoined", False):
        st.info("연결이 끊겼다가 같은 방으로 다시 들어왔습니다. 이전 답안을 이어서 푸시면 됩니다.")
    if pid not in room["players"]:
        st.warning("이 기기의 참가 기록이 방에 없습니다. 같은 별명으로 다시 합류합니다. 이전 답안은 이어지지 않을 수 있습니다.")
        rooms.join(
            code,
            pid,
            (st.session_state.get("player_name") or "").strip() or "참가",
            st.session_state.get("my_org") or {},
        )
        room = rooms.load(code) or room
    me = room["players"][pid]
    deck = room["deck"]
    total = len(deck)
    mode = rooms.mode_of(room)
    lim = rooms.limit_sec(room)
    rnd = int(room.get("round") or 1)
    _show_fx()

    head = [
        f"<span class='pill'>방 {room['code']}</span>",
        f"<span class='pill gold'>{rooms.MODES[mode][0]}</span>",
        f"<span class='pill'>{html.escape(room['area_name'])}</span>",
    ]
    if rnd > 1:
        head.append(f"<span class='pill'>{rnd}판째</span>")
    if room.get("team_battle") and me.get("side"):
        cls = SIDE_CLASS.get(me["side"], "")
        head.append(f"<span class='pill {cls}'>{me['side']}</span>")
    st.caption(_org_caption(room, pid))
    st.markdown("".join(head), unsafe_allow_html=True)

    if room["status"] == "countdown":
        if room.get("play_at"):
            sfx.countdown(room["play_at"], f"cd-{code}-{room.get('play_at')}")

        @st.fragment(run_every=1)
        def tick():
            live = rooms.begin_if_due(code)
            if live is None:
                return
            n = rooms.seconds_left(live)
            if n <= 0 or live.get("status") == "play":
                st.rerun()
                return
            st.markdown(f"<div class='codebox'>{n}</div>", unsafe_allow_html=True)
            st.caption(rooms.MODES[mode][1])

        tick()
        if room.get("team_battle"):
            show_teams(room)
        st.markdown('<div class="mini-mark"></div>', unsafe_allow_html=True)
        cd1, _ = st.columns([1, 4])
        with cd1:
            if st.button("나가기", key="leave_cd"):
                _ask_leave_quiz()
        return

    if rooms.relay_on(room):
        play_relay(room, pid, deck, total)
        return

    if me.get("done"):
        done_screen(room, pid, deck, total)
        return

    idx = int(me["idx"])
    item = current_item(deck, idx)
    if item is None:
        st.success(f"끝. {int(me.get('score') or 0)}/{total}")
        return
    double = bool(deck[idx].get("x2"))

    rooms.touch(code, pid, idx)
    room = rooms.load(code) or room
    me = room["players"][pid]
    order = rooms.ranking(room)
    pos = next((i for i, r in enumerate(order, 1) if r["pid"] == pid), len(order))
    left = None
    if lim:
        left = max(0.0, rooms.deadline(room, me) - time.time())
    _hud(room, me, idx, total, pos, len(order), left, lim)

    saved = next((h for h in (me.get("history") or []) if int(h.get("idx") or -1) == idx), None)
    sel_key = f"sel_{code}_{rnd}_{idx}"
    if sel_key not in st.session_state and saved is not None:
        st.session_state[sel_key] = int(saved["choice"])

    if lim:
        @st.fragment(run_every=1)
        def time_watch():
            live = rooms.load(code)
            if live is None or live.get("status") != "play":
                return
            p = (live.get("players") or {}).get(pid) or {}
            if p.get("done") or int(p.get("idx") or 0) != idx:
                return
            secs = rooms.deadline(live, p) - time.time()
            if secs > 0:
                st.caption(f"남은 시간 {int(secs) + 1}초")
                return
            rooms.answer(code, pid, -1, int(item["a"]), ms=lim * 1000, double=double)
            _react_answer(code, pid)
            _advance(code, pid, idx, total)
            st.rerun()

        time_watch()

    render_question(item, idx + 1, total, double)

    pick = None
    if item.get("kind") == "num":
        st.caption("원문 그대로입니다. 숫자를 넣고 확인을 누르십시오.")
        nkey = f"num_{code}_{rnd}_{idx}"
        if nkey not in st.session_state and saved is not None and int(saved["choice"]) >= 0:
            st.session_state[nkey] = int(saved["choice"])
        n1, n2, _ = st.columns([1.2, 1, 2.8])
        with n1:
            st.number_input("숫자", min_value=0, max_value=99, step=1, key=nkey, label_visibility="collapsed")
        with n2:
            if st.button("확인", type="primary", key=f"numok_{code}_{rnd}_{idx}"):
                pick = int(st.session_state.get(nkey) or 0)
    else:
        pick = pick_choice(item, f"r_{code}_{rnd}_{idx}", st.session_state.get(sel_key))

    if pick is not None:
        spent = 0
        if me.get("q_at"):
            try:
                spent = int(max(0.0, time.time() - datetime.fromisoformat(me["q_at"]).timestamp()) * 1000)
            except Exception:
                spent = 0
        rooms.answer(code, pid, int(pick), int(item["a"]), ms=spent, double=double)
        st.session_state[sel_key] = pick
        _react_answer(code, pid)
        after = rooms.load(code) or room
        if (after.get("players") or {}).get(pid, {}).get("done"):
            st.rerun()
        if _advance(code, pid, idx, total):
            st.rerun()
        else:
            st.error("아직 안 푼 문제가 있습니다. 이전으로 돌아가 고르십시오.")

    if mode == "classic":
        st.markdown('<div class="nav-mark"></div>', unsafe_allow_html=True)
        nav = st.columns(3)
        with nav[0]:
            if st.button("이전", disabled=idx <= 0, key="nav_prev", use_container_width=True):
                _beep("tick")
                rooms.seek(code, pid, idx - 1)
                st.rerun()
        with nav[1]:
            if st.button("다음", key="nav_next", use_container_width=True):
                _beep("tick")
                if _advance(code, pid, idx, total):
                    st.rerun()
                else:
                    st.error("아직 안 푼 문제가 있습니다. 이전으로 돌아가 고르십시오.")
        with nav[2]:
            if st.button("나가기", key="leave_play", use_container_width=True):
                _ask_leave_quiz()
    else:
        st.caption("되돌아갈 수 없습니다. 고르면 바로 다음 문제로 갑니다.")
        st.markdown('<div class="nav-mark"></div>', unsafe_allow_html=True)
        b1, _ = st.columns([1, 4])
        with b1:
            if st.button("나가기", key="leave_play2", use_container_width=True):
                _ask_leave_quiz()

    with st.expander("지금 순위 · 교육장 전광판", expanded=False):
        @st.fragment(run_every=2)
        def live_board():
            live = rooms.load(code)
            if live is None:
                return
            show_ranking(live, pid, "실시간 순위")

        live_board()


phase = st.session_state.phase
if phase != "gate":
    _render_header(phase)
if phase == "hub":
    hub_screen()
elif phase == "cases":
    cases_screen()
elif phase == "laws":
    laws_screen()
elif phase == "enter":
    enter_screen()
elif phase == "host_setup":
    host_setup_screen()
elif phase == "lobby":
    lobby_screen()
else:
    play_screen()
