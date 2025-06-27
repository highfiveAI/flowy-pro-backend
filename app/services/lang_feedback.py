import statistics
from collections import Counter
from langchain_openai import ChatOpenAI
import re

# 다양한 안건 입력을 비동기로 분리하는 함수
def _sync_split_agenda(agenda: str):
    items = re.split(r'[\n\r]+', agenda)
    result = []
    for item in items:
        sub_items = re.split(
            r'(?:^|[\s])(?:'
            r'\d+[.)．:]\s*|'
            r'[a-zA-Z][.)．:]\s*|'
            r'[가-힣ㄱ-ㅎ][.)．:]\s*'
            r')', item)
        for sub in sub_items:
            for s in sub.split(','):
                s = s.strip()
                if s:
                    result.append(s)
    return [r for r in result if r]

async def split_agenda(agenda: str):
    # 실제로는 동기 함수지만, 향후 확장성 위해 async로 래핑
    return _sync_split_agenda(agenda)

async def feedback_agent(subject, chunks, tag_result, attendees_list=None, agenda=None, meeting_date=None, meeting_duration_minutes=None):
    print(f"[lang_feedback] meeting_duration_minutes: {meeting_duration_minutes}", flush=True)
    score_char_count = {0: 0, 1: 0, 2: 0, 3: 0}
    total_chars = 0
    for s in tag_result:
        if isinstance(s, dict):
            score = s.get("score", 0)
            sent = s.get("sentence", "")
            score_char_count[score] += len(sent)
            total_chars += len(sent)
    percent = lambda n: round((score_char_count.get(n, 0) / total_chars) * 100, 1) if total_chars else 0
    percent_3 = percent(3)
    percent_2 = percent(2)
    percent_1 = percent(1)
    percent_0 = percent(0)
    percent_23 = percent_2 + percent_3

    scores = [s.get("score", 0) for s in tag_result if isinstance(s, dict)]
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
    small_talk = []
    if meeting_duration_minutes is not None and len(scores) > 0:
        min_per_sentence = meeting_duration_minutes / len(scores)
        small_talk_ranges = []
        for start, end in chit_chat_ranges:
            start_min = round(start * min_per_sentence, 1)
            end_min = round((end + 1) * min_per_sentence, 1)
            end_min = min(end_min, meeting_duration_minutes)
            s, e = sorted([start_min, end_min])
            small_talk_ranges.append((s, e))
        # 병합 함수
        def merge_ranges(ranges):
            if not ranges:
                return []
            ranges = sorted(ranges)
            merged = [ranges[0]]
            for current in ranges[1:]:
                prev = merged[-1]
                if current[0] <= prev[1]:
                    merged[-1] = (prev[0], max(prev[1], current[1]))
                else:
                    merged.append(current)
            return merged
        merged_ranges = merge_ranges(small_talk_ranges)
        n = len(merged_ranges)
        if n == 0:
            small_talk = ["잡담 구간이 뚜렷하게 나타나지 않았습니다."]
        elif n <= 3:
            # 1번: 모두 구체적으로
            small_talk = [
                ", ".join([f"{round(s,1)}분~{round(e,1)}분" for s, e in merged_ranges]) + " 구간에서 관련 없는 대화가 많았습니다."
            ]
        elif n <= 6:
            # 2번: 대표 2개만 + 등
            details = ", ".join([f"{round(s,1)}~{round(e,1)}분" for s, e in merged_ranges[:2]])
            small_talk = [f"총 {n}개의 잡담 구간({details} 등)에서 관련 없는 대화가 많았습니다."]
        else:
            # 3번: 대표 3개만 + 외 N개
            details = ", ".join([f"{round(s,1)}~{round(e,1)}분" for s, e in merged_ranges[:3]])
            small_talk = [f"총 {n}개의 잡담 구간({details} 외 {n-3}개)에서 관련 없는 대화가 많았습니다."]
    else:
        for start, end in chit_chat_ranges:
            start_min = start + 1
            end_min = end + 1
            small_talk.append(f"{start_min}분~{end_min}분 구간에서 관련 없는 대화가 많았습니다.")
    if not small_talk:
        small_talk = ["잡담 구간이 뚜렷하게 나타나지 않았습니다."]

    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    attendees_list_str = "참석자 정보 없음"
    if attendees_list and isinstance(attendees_list, list):
        attendees_list_str = "\n".join([
            f"- 이름: {a.get('name', '')}, 이메일: {a.get('email', '')}, 직무: {a.get('role', '')}"
            for a in attendees_list
        ])

    feedback_prompt = f"""
    너는 회의 피드백 전문가야.
    아래는 회의록 태깅 결과(문장별 점수와 이유)와 점수별 글자수 비율이야.

    - 회의 주제: {subject}
    - 회의 안건: {agenda if agenda else "안건 없음"}
    - 회의 일시: {meeting_date if meeting_date else "일시 정보 없음 (참고용 정보)"}
    - 참석자 목록:
    {attendees_list_str}

    - 점수별 글자수 비율: 3점 {percent_3}%, 2점 {percent_2}%, 1점 {percent_1}%, 0점 {percent_0}%
    - 태깅 결과:
    {[(s.get('score'), s.get('sentence'), s.get('reason')) for s in tag_result if isinstance(s, dict)]}

    주의 사항:
    - 회의 시작 전 **인사말**과 마무리 인사말은 예의적 발언으로 간주하고 스몰톡으로 판단하지 마.
    - 예의적 인사말 예시: "안녕하세요", "수고하셨습니다", "감사합니다" 등은 자연스러운 회의 흐름이다.

    회의 주제와 안건을 고려해 회의 전반을 분석하고 개선 가이드를 2~3줄 제시해줘.
    """

    guide_response = await llm.ainvoke(feedback_prompt)
    guide = [guide_response.content.strip()]

    missing_agenda_issues = None
    if agenda:
        if isinstance(agenda, str):
            agenda_items = await split_agenda(agenda)
        else:
            agenda_items = agenda
        discussed = []
        not_discussed = []
        meeting_text = '\n'.join(chunks) if isinstance(chunks, list) else str(chunks)
        for item in agenda_items:
            if item and item in meeting_text:
                discussed.append(item)
            else:
                not_discussed.append(item)
        if not_discussed:
            missing_agenda_issues = f"논의되지 않은 안건: {', '.join(not_discussed)}"
        else:
            missing_agenda_issues = "모든 안건이 논의되었습니다."

    sentence_counter = Counter([s.get('sentence', '') for s in tag_result if isinstance(s, dict)])
    duplicated = [(sent, cnt) for sent, cnt in sentence_counter.items() if cnt > 1 and sent.strip()]
    duplicated_info = []
    for sent, cnt in duplicated:
        idxs = [i for i, s in enumerate(tag_result) if isinstance(s, dict) and s.get('sentence', '') == sent]
        if idxs:
            start_min = idxs[0] + 1
            end_min = idxs[-1] + 1
            duplicated_info.append(f"'{sent[:20]}...' 내용이 {cnt}회({start_min}~{end_min}분) 반복")
    if percent_3 + percent_2 >= 70 and not duplicated_info:
        meeting_time_analysis = "회의 시간이 매우 효율적으로 사용되었습니다. 중복된 발언이 거의 없었습니다."
    elif percent_0 >= 20:
        meeting_time_analysis = f"회의 중 {percent_0}%가 잡담 등 비효율적으로 사용되었습니다."
    elif duplicated_info:
        meeting_time_analysis = "중복된 발언이 발견됨: " + '; '.join(duplicated_info)
    else:
        meeting_time_analysis = "회의 시간이 비교적 효율적으로 사용되었습니다."

    overall = (
        f"이번 회의에서 핵심 관련 발언(3점)은 {percent_3}%, 관련 발언(2점)은 {percent_2}%로,\n"
        f"총 {percent_23}%가 회의 주제에 집중된 내용으로 진행되었습니다.\n"
        f"반면 전혀 관련 없는 잡담(0점)은 {percent_0}% 포함되어 있었습니다."
    )

    feedback = {
        "총평": overall,
        "잡담 구간 피드백": small_talk,
        "누락된 논의 발생": missing_agenda_issues,
        "회의 시간 분석": meeting_time_analysis,
        "개선 가이드": guide
    }

    print("[lang_feedback] 피드백 결과:", feedback, flush=True)
    return {
        "feedback": feedback,
        "overall": overall,
        "score0": percent_0,
        "score1": percent_1,
        "score2": percent_2,
        "score3": percent_3,
        "small_talk": small_talk,
        "missing_agenda_issues": missing_agenda_issues,
        "meeting_time_analysis": meeting_time_analysis,
        "guide": guide
    }
