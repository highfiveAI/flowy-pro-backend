import statistics
from collections import Counter
from langchain_openai import ChatOpenAI
import re

def feedback_agent(subject, chunks, tag_result, attendees_list=None, agenda=None, meeting_date=None):
    # print(f"[lang_feedback] feedback_agent 호출됨: subject={subject}, chunks={chunks}, tag_result={tag_result}", flush=True)

    # 1️⃣ 점수별 글자수 비율 계산
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

    # 2️⃣ 잡담 구간 피드백 (구간 위치는 분 단위로 표시)
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
    for start, end in chit_chat_ranges:
        start_min = start + 1
        end_min = end + 1
        small_talk.append(f"{start_min}분~{end_min}분 구간에서 관련 없는 대화가 많았습니다.")
    if not small_talk:
        small_talk = ["잡담 구간이 뚜렷하게 나타나지 않았습니다."]

    # 3️⃣ 개선 가이드: agent가 직접 판단하도록 LLM 프롬프트로 생성
    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    # 참석자 정보 프롬프트용 문자열 생성
    attendees_list_str = "참석자 정보 없음"
    if attendees_list and isinstance(attendees_list, list):
        attendees_list_str = "\n".join([
            f"- 이름: {a.get('name', '')}, 이메일: {a.get('email', '')}, 직무: {a.get('role', '')}"
            for a in attendees_list
        ])

    # 피드백용 프롬프트
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
    - 회의 시작 전 **인사말**(예: "안녕하세요", "좋은 아침입니다", "오늘도 수고 많으십니다") 및 회의 종료 시 **마무리 인사말**(예: "수고하셨습니다", "고생 많으셨어요", "좋은 하루 보내세요")는 회의 주제와 직접 관련이 없더라도 피드백시 이부분이 0점이어도 피드백에서 불필요한 내용이라고 판단하지 마세요.
    - 이런 인사말은 **회의 예절상 필수적인 대화**로 간주하여 **별도로 취급**하며, **'예의적 발언'으로 별도 표시**해도 됩니다.
    - 예의적 인사말 예시: "안녕하세요", "좋은 아침이에요", "수고하셨습니다", "고맙습니다", "고생 많으셨습니다", "편한 오후 되세요", "감사합니다"
    - 이러한 문장은 **불필요한 대화(스몰톡)**이나 **산만한 발언**으로 판단하지 말고, 회의 흐름상 자연스러운 관용적 발언으로 인식하세요.

    회의 주제와 (안건이 있다면) 회의 안건을 참고하여 회의 전반적인 진행 상태를 분석해.
    회의 전체 내용을 전반적으로 고려해서, 개선 가이드를 2~3줄로 제안해줘.
    (예: 잡담이 많으면 집중 유도, 1점이 많으면 결론 강조, 2점이 많고 3점이 적으면 액션 아이템 도출 등)
    반드시 자연스러운 한국어 문장으로, 구체적이고 실질적인 개선 팁을 제시해.

    """
    guide_response = llm.invoke(feedback_prompt).content.strip()
    guide = [guide_response]

    # 누락된 논의 발생 (agenda가 있을 때만)
    missing_agenda_issues = None
    if agenda:
        # agenda가 문자열이면 리스트로 변환
        if isinstance(agenda, str):
            agenda_items = [a.strip() for a in agenda.split(',') if a.strip()]
        else:
            agenda_items = agenda
        discussed = []
        not_discussed = []
        # chunks(회의 내용)에서 각 안건이 언급되었는지 단순 포함 여부로 판단
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

    # 회의 시간 분석 (점수 비율 + 중복 발언)
    # 중복 발언: 같은 문장이 여러 번 등장하는 경우(간단하게 처리)
    sentence_counter = Counter([s.get('sentence', '') for s in tag_result if isinstance(s, dict)])
    duplicated = [(sent, cnt) for sent, cnt in sentence_counter.items() if cnt > 1 and sent.strip()]
    duplicated_info = []
    for sent, cnt in duplicated:
        # 몇 분 구간에서 반복됐는지 추정 (index 기반)
        idxs = [i for i, s in enumerate(tag_result) if isinstance(s, dict) and s.get('sentence', '') == sent]
        if idxs:
            start_min = idxs[0] + 1
            end_min = idxs[-1] + 1
            duplicated_info.append(f"'{sent[:20]}...' 내용이 {cnt}회({start_min}~{end_min}분) 반복")
    # 효율성 평가
    if percent_3 + percent_2 >= 70 and not duplicated_info:
        meeting_time_analysis = "회의 시간이 매우 효율적으로 사용되었습니다. 중복된 발언이 거의 없었습니다."
    elif percent_0 >= 20:
        meeting_time_analysis = f"회의 중 {percent_0}%가 잡담 등 비효율적으로 사용되었습니다."
    elif duplicated_info:
        meeting_time_analysis = "중복된 발언이 발견됨: " + '; '.join(duplicated_info)
    else:
        meeting_time_analysis = "회의 시간이 비교적 효율적으로 사용되었습니다."

    # 4️⃣ 총평
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
