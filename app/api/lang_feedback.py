import statistics
from collections import Counter

def feedback_agent(subject, chunks, tag_result):
    # print(f"[lang_feedback] feedback_agent 호출됨: subject={subject}, chunks={chunks}, tag_result={tag_result}", flush=True)

    # 1️⃣ 점수별 비율 계산
    scores = [s.get("score", 0) for s in tag_result if isinstance(s, dict)]
    total = len(scores)
    score_counter = Counter(scores)
    percent = lambda n: round((score_counter.get(n, 0) / total) * 100, 1) if total else 0
    percent_3 = percent(3)
    percent_2 = percent(2)
    percent_1 = percent(1)
    percent_0 = percent(0)
    percent_23 = percent_2 + percent_3

    # 2️⃣ 잡담 구간 피드백 (구간 위치는 예시로 index로 표시)
    chit_chat_indices = [i for i, s in enumerate(scores) if s in [0, 1]]
    chit_chat_ranges = []
    if chit_chat_indices:
        start = chit_chat_indices[0]
        prev = start
        for idx in chit_chat_indices[1:]:
            if idx == prev + 1:
                prev = idx
            else:
                chit_chat_ranges.append((start, prev))
                start = idx
                prev = idx
        chit_chat_ranges.append((start, prev))
    chit_chat_feedback = []
    for start, end in chit_chat_ranges:
        chit_chat_feedback.append(f"문장 {start+1}~{end+1} 구간에서 관련 없는 대화가 많았습니다.")
    if not chit_chat_feedback:
        chit_chat_feedback = ["잡담 구간이 뚜렷하게 나타나지 않았습니다."]

    # 3️⃣ 개선 가이드
    guide = []
    if percent_0 > 10:
        guide.append("잡담 비율이 높으니 회의 시작 시 목표 및 아젠다 리마인드 → 흐름 유도 권장")
    if percent_1 > 20:
        guide.append("1점 발언이 많으니 발언 시 핵심 결론 → 배경 설명 순으로 말하도록 유도")
    if percent_2 > 30 and percent_3 < 20:
        guide.append("2점이 많고 3점이 적으니 명확한 결정/액션 아이템 도출 부족 → 회의 말미에 명시적 정리 필요")
    if not guide:
        guide.append("회의 집중도가 높고, 개선점이 많지 않습니다. 좋은 회의였습니다!")

    # 4️⃣ 총평
    summary = (
        f"이번 회의에서 핵심 관련 발언(3점)은 {percent_3}%, 관련 발언(2점)은 {percent_2}%로,\n"
        f"총 {percent_23}%가 회의 주제에 집중된 내용으로 진행되었습니다.\n"
        f"반면 전혀 관련 없는 잡담(0점)은 {percent_0}% 포함되어 있었습니다."
    )

    feedback = {
        "총평": summary,
        "잡담 구간 피드백": chit_chat_feedback,
        "개선 가이드": guide
    }

    print("[lang_feedback] 피드백 결과:", feedback, flush=True)
    return {
        "feedback": feedback,
        "tag_result": tag_result
    } 