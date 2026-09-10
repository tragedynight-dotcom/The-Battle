from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime

CITIES = {
    "광주 동구": (35.1462, 126.9231),
    "광주 서구": (35.1520, 126.8900),
    "광주 남구": (35.1330, 126.9025),
    "광주 북구": (35.1741, 126.9120),
    "광주 광산구": (35.1394, 126.7937),
    "목포시": (34.8118, 126.3922),
    "여수시": (34.7604, 127.6622),
    "순천시": (34.9507, 127.4872),
    "서울 중구": (37.5641, 126.9979),
    "부산 중구": (35.1066, 129.0323),
    "대전 서구": (36.3552, 127.3838),
    "대구 중구": (35.8694, 128.6060),
    "인천 남동구": (37.4475, 126.7314),
}

CASES = {
    "폭행·시비": {
        "keys": ["폭행", "시비", "싸움", "상해", "때렸", "맞았", "주먹", "흉기"],
        "check": [
            "부상자 유무·응급조치·112 추가 요청 여부 확인",
            "쌍방·일방 여부, 최초 가해 경위 분리 청취",
            "현장 증거(CCTV, 목격자, 흉기, 혈흔) 확보·보존",
            "피해자 의사(처벌 불원/합의 진행) 확인",
            "관할 지구대·파출소에 인계 또는 지원 출동 요청",
        ],
        "law": "형법 제260조 폭행, 제257조 상해 / 필요 시 특수폭행",
    },
    "절도": {
        "keys": ["절도", "도난", "훔", "분실", "소매치기", "자전거", "가방"],
        "check": [
            "피해품·시간·장소·범행 수법 특정",
            "인근 CCTV·카드 사용 여부 확인",
            "현행범·도주 방향이 있으면 차단선 먼저",
            "장물 거래 가능성(중고 앱, 전당포) 고지",
            "피해품 특정 가능한 사진·일련번호 확보",
        ],
        "law": "형법 제329조 절도",
    },
    "교통사고": {
        "keys": ["교통", "사고", "추돌", "접촉", "보행자", "신호", "음주운전"],
        "check": [
            "사상자 유무·구급 요청, 2차 사고 방지(안전삼각대)",
            "음주·무면허 의심 시 먼저 분리",
            "차량 위치 원상 보존, 블랙박스·목격자 확보",
            "보험 접수·실황조사 필요 여부 판단",
            "어린이·노인 피해자면 보호구역 여부 확인",
        ],
        "law": "도로교통법, 특정범죄가중처벌법(도주·음주)",
    },
    "주취·소란": {
        "keys": ["주취", "취한", "소란", "행패", "기물", "점포", "편의점"],
        "check": [
            "위해 가능성(자해·타해)부터 제압·분리",
            "업주·손님 피해 및 기물 파손 여부",
            "보호자 연락, 해산·인계·현행범 여부 판단",
            "반복 출동 이력·주취자 응급의료 필요 여부",
            "인계 후 순찰 공백 구간 한 바퀴 더",
        ],
        "law": "경범죄처벌법 주취소란, 재물손괴, 폭행 해당 시 형법",
    },
    "실종·가출": {
        "keys": ["실종", "가출", "없어졌", "안 들어", "치매", "어린이"],
        "check": [
            "최종 목격 시간·복장·건강상태·이동수단 확인",
            "아동·치매 어르신이면 즉시 광역 전파·CCTV",
            "휴대폰 위치·교통카드·카드 사용 협조 여부",
            "인근 역·터미널·하천·공사현장 우선 수색",
            "가정폭력·학대 정황이 있으면 분리 보호",
        ],
        "law": "실종아동등 보호법, 필요 시 아동학대 관련 규정",
    },
    "다중운집·행사": {
        "keys": ["행사", "축제", "집회", "인파", "콘서트", "불꽃", "경기"],
        "check": [
            "출입로·병목·하차 지점 먼저 보고 고정 배치",
            "기상(비·폭염·한파)에 따른 밀집 위험 재평가",
            "응급·소방 동선이 막히지 않게 유지",
            "취객·시비 발생 시 군중과 분리해 처리",
            "종료 후 역·정류장 잔여 인파 한 타임 더",
        ],
        "law": "다중운집 인파사고 예방 매뉴얼, 집회 및 시위에 관한 법률",
    },
    "보이스피싱": {
        "keys": ["피싱", "사기", "검찰", "대출", "계좌", "원격", "악성앱"],
        "check": [
            "송금·원격제어 진행 중이면 즉시 중단·계좌지급정지",
            "상대 번호, 앱, 대화 내용, 이체 내역 보존",
            "피해자 연령·피해액·잔액 회수 가능성 확인",
            "추가 인출 방지를 위해 가족·은행 연락",
            "사이버팀·금융대응센터 연계 필요 여부",
        ],
        "law": "전기통신금융사기 피해 방지 및 피해금 환급에 관한 법률",
    },
}


def classify(text: str) -> str:
    text = text or ""
    scores = {name: sum(1 for k in spec["keys"] if k in text) for name, spec in CASES.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] else "기타"


def mask_pii(text: str) -> str:
    out = text or ""
    out = re.sub(r"\d{6}-?\d{7}", lambda m: m.group()[:6] + "-*******", out)
    out = re.sub(r"01[016789]-?\d{3,4}-?\d{4}", lambda m: re.sub(r"\d", "*", m.group()[:-4]) + m.group()[-4:], out)
    out = re.sub(r"\d{2,3}-\d{2,3}-\d{6}", "***-**-******", out)
    out = re.sub(r"[가-힣]{2,4}(?=(경찰관|순경|경사|경위)?\s*(씨|님)?)", lambda m: m.group()[0] + "○" * (len(m.group()) - 1), out)
    return out


def fetch_weather(lat: float, lon: float) -> dict:
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,precipitation,weather_code,wind_speed_10m"
        "&timezone=Asia%2FSeoul"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "patrol-briefing/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        cur = data.get("current", {})
        code = int(cur.get("weather_code") or 0)
        label = _weather_label(code, float(cur.get("precipitation") or 0))
        return {
            "ok": True,
            "label": label,
            "temp": cur.get("temperature_2m"),
            "rain": cur.get("precipitation"),
            "wind": cur.get("wind_speed_10m"),
            "time": cur.get("time"),
        }
    except Exception:
        return {"ok": False, "label": "날씨 수신 실패(수동 입력)", "temp": None, "rain": None, "wind": None, "time": None}


def _weather_label(code: int, rain: float) -> str:
    if rain and rain >= 0.5:
        return "비"
    if code in {45, 48}:
        return "안개"
    if code in {51, 53, 55, 61, 63, 65, 80, 81, 82}:
        return "비"
    if code in {71, 73, 75, 77, 85, 86}:
        return "눈"
    if code in {95, 96, 99}:
        return "뇌우"
    if code in {1, 2, 3}:
        return "흐림"
    return "맑음"


def briefing(city: str, cars: int, memo: str, weather: dict, now: datetime) -> str:
    case = classify(memo) if memo.strip() else "다중운집·행사" if any(k in memo for k in ["행사", "축제"]) else ""
    weather_line = weather["label"]
    if weather.get("temp") is not None:
        weather_line += f", {weather['temp']}℃"
    if weather.get("rain"):
        weather_line += f", 강수 {weather['rain']}mm"
    tips = []
    if weather["label"] in {"비", "눈", "뇌우"}:
        tips.append("우천·노면 미끄럼, 이면도로·횡단보도 체류가 늘 수 있어 번화가·역 앞을 우선한다.")
    if weather["label"] == "맑음" and weather.get("temp") and weather["temp"] >= 33:
        tips.append("폭염이므로 그늘 없는 고정근무를 짧게 나누고 수분·휴식 교대를 넣는다.")
    if case:
        tips.append(f"인수인계 메모 기준으로 오늘 유의 유형은 ‘{case}’이다.")
    if cars <= 2:
        tips.append("차가 적으니 전 구간 순회보다 거점 2~3곳을 반복한다.")
    else:
        tips.append("차량을 겹치지 않게 동·서 또는 번화가·주거로 나눠 공백을 줄인다.")
    memo_block = memo.strip() or "(인수인계 메모 없음)"
    return f"""【오늘 근무 브리핑】
일시: {now:%Y-%m-%d %H:%M} ({'주말' if now.weekday() >= 5 else '평일'})
대상: {city} / 가용 순찰차 {cars}대
날씨: {weather_line}  ※ 실시간 기상(Open-Meteo), 2024 통계 아님

1. 오늘 인수인계
{memo_block}

2. 오늘 이렇게
{chr(10).join(f'- {t}' for t in tips)}

3. 근무 후 남길 것
- 출동·지원 건, 인계 시각, 특이사항 3줄
- 개인정보(이름·전화·주민번호)는 일지 공유 전 마스킹
"""


def draft_log(kind: str, city: str, unit: str, writer: str, memo: str, now: datetime) -> str:
    case = classify(memo)
    spec = CASES.get(case, {"check": ["현장 보존", "관계자 분리 청취", "관할 인계"], "law": "관련 법령 확인"})
    masked = mask_pii(memo.strip() or "내용 없음")
    if kind == "순찰일지":
        return f"""【순찰일지 초안】
작성일시: {now:%Y-%m-%d %H:%M}
작성: {mask_pii(writer) or "○○"}
근무지: {city} / {unit or "광역예방순찰"}

1. 순찰 개요
{masked}

2. 조치
- 위 내용을 근거로 거점 순찰 및 필요 시 초동 지원
- {spec['check'][0]}

3. 결과
- (직접 보완) 인계 시각, 지원 여부, 특이사항

※ 초안입니다. 사실관계 확인 후 결재용으로 수정하십시오.
"""
    return f"""【발생보고 초안】
작성일시: {now:%Y-%m-%d %H:%M}
작성: {mask_pii(writer) or "○○"}
발생지: {city} / {unit or "관할 미상"}
유형: {case}
관련: {spec['law']}

1. 인지 경위
{masked}

2. 초동조치
{chr(10).join(f'- {x}' for x in spec['check'])}

3. 현 상태 / 인계
- (직접 보완) 피해자·피의자 신분, 증거 목록, 인계 부서

※ 개인정보는 아래 마스킹본을 공유용으로 쓰십시오.
"""


def other_case() -> dict:
    return {
        "check": [
            "위해 여부부터 확인하고 현장 보존",
            "관계자를 분리해 경위를 짧게 정리",
            "관할 지구대·파출소 또는 기능부서 인계",
            "증거·목격자 연락처는 별지 보관",
        ],
        "law": "사안에 따라 형법·경범죄처벌법 등",
    }
