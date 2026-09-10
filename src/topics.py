from __future__ import annotations

from datetime import date

# 달력에 한 주제를 고정하지 않는다.
# 팀장이 주제를 고민하지 않게, 현장 애로·이번 달·최근 교육으로 고른다.

CATEGORIES = [
    "가정·피해자",
    "체포·압수",
    "교통",
    "사기·사이버",
    "외국인·수배",
    "정신·보호",
    "생활질서",
]

TOPICS = [
    {"id": "dv", "cat": "가정·피해자", "title": "가정폭력 초동·긴급임시조치", "talk": "처벌 불원인데 아이가 있다. 무엇을 남기는가.", "law": "가정폭력범죄의 처벌 등에 관한 특례법", "prec": "가정폭력 긴급임시조치"},
    {"id": "dating", "cat": "가정·피해자", "title": "교제폭력과 가정폭력 구분", "talk": "헤어진 연인이 찾아온다. 어느 법으로 받는가.", "law": "스토킹범죄의 처벌 등에 관한 법률", "prec": "교제폭력"},
    {"id": "stalk", "cat": "가정·피해자", "title": "스토킹 응급조치·긴급응급조치", "talk": "부재중 전화만 있다. 스토킹으로 볼 것인가.", "law": "스토킹범죄의 처벌 등에 관한 법률", "prec": "스토킹 긴급응급조치"},
    {"id": "child", "cat": "가정·피해자", "title": "아동학대와 보호자", "talk": "부부 싸움 현장에 초등학생이 있다.", "law": "아동학대범죄의 처벌 등에 관한 특례법", "prec": "아동학대 임시조치"},
    {"id": "sex", "cat": "가정·피해자", "title": "성폭력 초동·2차 피해", "talk": "상담만 원한다고 한다. 일반 신고로 넘길 것인가.", "law": "성폭력범죄의 처벌 등에 관한 특례법", "prec": "성폭력 카메라등이용촬영"},
    {"id": "elder", "cat": "가정·피해자", "title": "노인학대 현장", "talk": "자식이 돌본다고 하는데 노인이 겁에 질려 있다. 누구 말을 남기는가.", "law": "노인복지법", "prec": "노인학대"},
    {"id": "arrest", "cat": "체포·압수", "title": "현행범과 긴급체포", "talk": "폭행 직후 도망간다. 긴급체포가 되는가.", "law": "형사소송법 제200조의3", "prec": "긴급체포 현행범"},
    {"id": "seize", "cat": "체포·압수", "title": "임의제출·영장 없는 압수", "talk": "공원에서 체포한 뒤 집을 수색했다.", "law": "형사소송법 제216조", "prec": "임의제출 압수"},
    {"id": "search", "cat": "체포·압수", "title": "불심검문과 임의동행", "talk": "거절하는데 차에 태웠다. 남는 기록은 무엇인가.", "law": "경찰관직무집행법 제3조", "prec": "불심검문 임의동행"},
    {"id": "dui", "cat": "교통", "title": "음주측정 거부", "talk": "화를 내며 불대를 밀었다. 바로 거부인가.", "law": "도로교통법 제148조의2", "prec": "음주측정거부"},
    {"id": "pm", "cat": "교통", "title": "개인형 이동장치", "talk": "12살이 킥보드로 보도를 달렸다.", "law": "도로교통법 개인형 이동장치", "prec": "개인형 이동장치"},
    {"id": "hitrun", "cat": "교통", "title": "사고 후 미조치", "talk": "접촉 후 10미터 앞에서 섰다. 도주인가.", "law": "도로교통법 제54조", "prec": "교통사고 미조치"},
    {"id": "bike", "cat": "교통", "title": "자전거·PM 음주", "talk": "자전거 음주와 킥보드 음주를 같이 볼 것인가.", "law": "도로교통법 제44조", "prec": "자전거 음주운전"},
    {"id": "phish", "cat": "사기·사이버", "title": "보이스피싱 지급정지", "talk": "인출자가 이유를 또렷이 말한다. 바로 종결인가.", "law": "전기통신금융사기 피해 방지 및 피해금 환급에 관한 특별법", "prec": "전기통신금융사기 지급정지"},
    {"id": "cam", "cat": "사기·사이버", "title": "카메라등이용촬영", "talk": "화장실 앞 CCTV를 개인 폰으로 찍었다.", "law": "성폭력범죄의 처벌 등에 관한 특례법 제14조", "prec": "카메라등이용촬영"},
    {"id": "bodycam", "cat": "사기·사이버", "title": "몸캠피싱·메신저 피싱", "talk": "지인 사칭과 영상 협박을 같은 죄로 볼 것인가.", "law": "형법 제350조", "prec": "몸캠피싱"},
    {"id": "wanted", "cat": "외국인·수배", "title": "지명수배자 발견", "talk": "영장 사본만 있다. 체포 후 무엇을 제시하는가.", "law": "경찰수사규칙 제45조", "prec": "지명수배"},
    {"id": "visa", "cat": "외국인·수배", "title": "불법체류자 인계", "talk": "경증 주취 불법체류자를 바로 인계하는가.", "law": "출입국관리법 제101조", "prec": "출입국관리법 인계"},
    {"id": "mental", "cat": "정신·보호", "title": "정신응급 입원", "talk": "가족이 입원을 거부한다. 경찰이 의뢰할 때는.", "law": "정신건강증진 및 정신질환자 복지서비스 지원에 관한 법률 제50조", "prec": "정신질환자 응급입원"},
    {"id": "protect", "cat": "정신·보호", "title": "경직법 보호조치", "talk": "길에 누워 있다. 보호인가, 주취소란인가.", "law": "경찰관직무집행법 제4조", "prec": "경찰관직무집행법 보호조치"},
    {"id": "suicide", "cat": "정신·보호", "title": "자살 우려 신고", "talk": "다리 위에 있다. 강제 이동의 근거는.", "law": "경찰관직무집행법 제4조", "prec": "자살 위험 경찰 조치"},
    {"id": "misd", "cat": "생활질서", "title": "경범죄·즉심", "talk": "우편함 전단지. 무단부착 즉심인가.", "law": "경범죄 처벌법", "prec": "즉결심판"},
    {"id": "noise", "cat": "생활질서", "title": "층간소음·주거 분쟁", "talk": "위층이 안 연다. 현장 출입의 근거는.", "law": "경범죄 처벌법", "prec": "주거침입 층간소음"},
    {"id": "lost", "cat": "생활질서", "title": "분실물·유실물", "talk": "지갑을 주웠다. 습득 신고 절차는.", "law": "유실물법", "prec": "유실물법"},
    {"id": "animal", "cat": "생활질서", "title": "동물 사고·맹견", "talk": "목줄 없는 개가 물었다. 누구를 입건하는가.", "law": "동물보호법", "prec": "동물보호법 맹견"},
    {"id": "school", "cat": "가정·피해자", "title": "학교폭력 초동", "talk": "하교길에 맞았다. 학교와 수사 중 무엇을 먼저 하는가.", "law": "학교폭력 예방 및 대책에 관한 법률", "prec": "학교폭력"},
]


def topic_by_id(tid: str) -> dict | None:
    for t in TOPICS:
        if t["id"] == tid:
            return t
    return None


# 팀장이 고르는 것은 주제가 아니라, 이번 달 현장에서 반복된 일이다.
ISSUES = [
    {"id": "drunk", "label": "주취·보호 출동이 많다", "topics": ["protect", "mental", "suicide"]},
    {"id": "family", "label": "가정·교제 출동이 반복된다", "topics": ["dv", "dating", "stalk", "child"]},
    {"id": "school", "label": "학교·아동 관련 신고가 있다", "topics": ["school", "child"]},
    {"id": "pm", "label": "킥보드·PM 민원이 늘었다", "topics": ["pm", "bike"]},
    {"id": "dui", "label": "음주운전·측정거부가 있다", "topics": ["dui", "bike"]},
    {"id": "crash", "label": "교통사고 미조치·도주 다툼이 있다", "topics": ["hitrun"]},
    {"id": "phish", "label": "보이스피싱·메신저 피싱이 들어온다", "topics": ["phish", "bodycam"]},
    {"id": "cam", "label": "촬영·몸캠 민원이 있다", "topics": ["cam", "bodycam"]},
    {"id": "foreign", "label": "외국인 신고·인계가 어렵다", "topics": ["visa"]},
    {"id": "wanted", "label": "수배자 발견이 있었다", "topics": ["wanted", "arrest"]},
    {"id": "arrest", "label": "체포·압수 절차가 조마다 다르다", "topics": ["arrest", "seize", "search"]},
    {"id": "mental", "label": "정신응급·자살우려가 있다", "topics": ["mental", "suicide", "protect"]},
    {"id": "noise", "label": "층간소음·생활 분쟁이 반복된다", "topics": ["noise", "misd"]},
    {"id": "lost", "label": "분실물·습득 민원이 많다", "topics": ["lost"]},
    {"id": "animal", "label": "개 물림·동물 사고가 있다", "topics": ["animal"]},
    {"id": "elder", "label": "노인 학대·방임이 의심된다", "topics": ["elder", "protect"]},
]

# 고정 월별 주제가 아니다. 같은 달이라도 현장·최근 교육에 따라 바뀐다.
SEASON = {
    1: (["dv", "protect", "elder"], "한파·연초에는 가정·보호 출동이 겹치기 쉽습니다."),
    2: (["dating", "dv", "phish"], "명절 전후 가정·교제와 명절 사기가 겹치기 쉽습니다."),
    3: (["school", "child", "pm"], "개학과 함께 학교·아동·킥보드 민원이 늘기 쉽습니다."),
    4: (["pm", "hitrun", "school"], "나들이·개학 직후 교통·학교 현장이 늘기 쉽습니다."),
    5: (["child", "sex", "elder"], "가정의 달에는 아동·성폭력·노인 초동이 교육 가치가 큽니다."),
    6: (["dui", "hitrun", "protect"], "장마·유흥 시즌에는 음주·사고·보호가 겹치기 쉽습니다."),
    7: (["protect", "suicide", "pm"], "폭염·휴가철에는 보호·자살우려·PM이 겹치기 쉽습니다."),
    8: (["protect", "pm", "phish", "suicide"], "폭염 보호와 휴가철 PM·사기가 겹치는 달입니다."),
    9: (["school", "phish", "dv"], "개학·추석 무렵 학교폭력과 명절 사기·가정이 겹치기 쉽습니다."),
    10: (["dui", "arrest", "misd"], "축제·단풍철에는 음주·체포·생활질서가 겹치기 쉽습니다."),
    11: (["protect", "wanted", "arrest"], "한파 시작과 수배·체포 절차를 다시 맞출 달입니다."),
    12: (["dui", "phish", "misd"], "연말 음주·사기·즉심이 몰리는 달입니다."),
}

RUN = [
    "5분 이번 달 우리 조에서 비슷한 출동 한 줄만 말하게 하십시오.",
    "10분 법령정보센터 원문만 같이 엽니다. 요약을 대신 말하지 마십시오.",
    "15분 아래 토의만 돌립니다. 정답을 알려 주지 마십시오.",
    "10분 우리 조 현장 순서를 한 줄로 합의하고 끝냅니다.",
]


def recommend(
    issue_labels: list[str],
    used_ids: set[str],
    used_cats: list[str],
    month: int | None = None,
    n: int = 3,
) -> list[dict]:
    """주제 목록을 섞지 않는다. 현장·계절·최근 교육으로 순위를 매긴다."""
    month = month or date.today().month
    season_ids, season_why = SEASON.get(month, ([], ""))
    picked_issues = [i for i in ISSUES if i["label"] in issue_labels]
    hit_ids: set[str] = set()
    for iss in picked_issues:
        hit_ids.update(iss["topics"])

    ranked: list[dict] = []
    for t in TOPICS:
        reasons: list[str] = []
        score = 0
        if t["id"] in used_ids:
            continue
        matched = [i["label"] for i in picked_issues if t["id"] in i["topics"]]
        if matched:
            score += 8 * len(matched)
            reasons.append("이번 달 현장에서 " + " / ".join(matched) + ".")
        if t["id"] in season_ids:
            score += 3
            if season_why:
                reasons.append(season_why)
        if t["cat"] not in used_cats:
            score += 5
            reasons.append("최근 교육이 " + t["cat"] + " 쪽이 아니라서 이번 달에 넣습니다.")
        else:
            score -= 3
        if not reasons:
            reasons.append("최근 실시 목록에 없는 주제입니다.")
        ranked.append({"topic": t, "score": score, "reasons": reasons})

    ranked.sort(key=lambda r: r["score"], reverse=True)
    # 1순위와 다른 카테고리를 앞에 두어 단조로운 반복을 막는다.
    out: list[dict] = []
    seen: set[str] = set()
    for row in ranked:
        cat = row["topic"]["cat"]
        if cat in seen:
            continue
        out.append(row)
        seen.add(cat)
        if len(out) >= n:
            break
    if len(out) < n:
        for row in ranked:
            if row not in out:
                out.append(row)
            if len(out) >= n:
                break
    return out


def issue_labels() -> list[str]:
    return [i["label"] for i in ISSUES]
