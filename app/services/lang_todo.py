import openai
import os
import json
import re
import datetime
import calendar
from typing import List, Dict, Any
from app.services.lang_role import assign_roles

openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def parse_relative_schedule(schedule_str: str, meeting_date: str) -> str:
    """
    상대적 일정 표현(오늘, 내일, 이번 주 금요일 등)이 포함되어있는 문자열을 meeting_date 기준 실제 날짜(YYYY.MM.DD(요일))로 변환
    변환 불가시 원본 반환
    """
    if not meeting_date:
        return schedule_str
    try:
        # meeting_date는 'YYYY-MM-DD' 또는 'YYYY.MM.DD' 등으로 들어올 수 있음
        date_match = re.match(r"(\d{4})[.-](\d{1,2})[.-](\d{1,2})", meeting_date)
        if not date_match:
            return schedule_str
        year, month, day = map(int, date_match.groups())
        base_date = datetime.date(year, month, day)
        weekday_map = {0: '월', 1: '화', 2: '수', 3: '목', 4: '금', 5: '토', 6: '일'}
        # 오늘/내일/모레
        if schedule_str in ["오늘", "오늘 중"]:
            target = base_date
        elif schedule_str == "내일":
            target = base_date + datetime.timedelta(days=1)
        elif schedule_str == "모레":
            target = base_date + datetime.timedelta(days=2)
        # 이번 주 요일
        elif schedule_str.startswith("이번 주 "):
            day_name = schedule_str.replace("이번 주 ", "").replace("요일", "")
            day_map = {"월":0, "화":1, "수":2, "목":3, "금":4, "토":5, "일":6}
            if day_name in day_map:
                base_weekday = base_date.weekday()
                target_weekday = day_map[day_name]
                days_ahead = (target_weekday - base_weekday + 7) % 7
                if days_ahead == 0:
                    days_ahead = 7  # 다음 주로 넘기지 않고 이번 주
                target = base_date + datetime.timedelta(days=days_ahead)
            else:
                return schedule_str
        # 다음 주 요일
        elif schedule_str.startswith("다음 주 "):
            day_name = schedule_str.replace("다음 주 ", "").replace("요일", "")
            day_map = {"월":0, "화":1, "수":2, "목":3, "금":4, "토":5, "일":6}
            if day_name in day_map:
                base_weekday = base_date.weekday()
                target_weekday = day_map[day_name]
                days_ahead = (target_weekday - base_weekday + 7) % 7 + 7
                target = base_date + datetime.timedelta(days=days_ahead)
            else:
                return schedule_str
        # 'YYYY-MM-DD' 등 날짜 문자열이 이미 들어온 경우
        elif re.match(r"\d{4}[.-]\d{1,2}[.-]\d{1,2}", schedule_str):
            date_match2 = re.match(r"(\d{4})[.-](\d{1,2})[.-](\d{1,2})", schedule_str)
            y, m, d = map(int, date_match2.groups())
            target = datetime.date(y, m, d)
        else:
            return schedule_str
        # 날짜 포맷: YYYY.MM.DD(요일)
        weekday = weekday_map[target.weekday()]
        return f"{target.year}.{target.month:02d}.{target.day:02d}({weekday})"
    except Exception:
        return schedule_str

def extract_todos(subject: str, chunks: List[str], attendees_list: List[Dict[str, Any]], sentence_scores: List[Dict[str, Any]], agenda: str = None, meeting_date: str = None) -> Dict[str, Any]:
    """
    회의 내용에서 할 일을 추출하는 함수
    
    Args:
        subject (str): 회의 주제
        chunks (List[str]): 회의 내용 청크 리스트
        attendees_list (List[Dict[str, Any]]): 참석자 리스트 (이름/직무/이메일 포함)
        sentence_scores (List[Dict[str, Any]]): 문장별 점수와 평가 정보
        agenda (str, optional): 회의 안건
        meeting_date (str, optional): 회의 일시
        
    Returns:
        Dict[str, Any]: 추출된 할 일 목록과 역할분배 결과 등
    """
    relevant_sentences = [
        score["sentence"] for score in sentence_scores 
        if score["score"] is not None and score["score"] >= 2
    ]

    prompt = f'''
너는 회의 대화록에서 "정말 해야 하는 업무 (Action)"만 정확하게 추출하는 역할을 한다.

[목적]
이 프롬프트의 목적은 회의록에서 "실제 실행해야 하는 Action"만 추출하는 것이다.  
회의에서 논의된 문제점, 아이디어, 이슈 정리는 Action이 아니다 (이미 요약 Agent에서 처리된다).

[회의 정보]
- 회의 주제: {subject}
- 회의 안건: {agenda if agenda else "안건 없음"}

[주요 규칙]
1️⃣ "문제점/이슈/아이디어 정리"는 Action이 아니다 → 추출 금지
2️⃣ "누가 무엇을 하겠다 / 확인하겠다 / 수정하겠다 / 검토하겠다" 와 같이 *구체적인 수행 의지가 자연스럽게 드러난 경우* Action 으로 추출한다.
3️⃣ "수행 의지"란, 말한 사람이 그 업무를 실제로 **수행할 의도가 있는 것으로 자연스럽게 해석되는 경우**를 포함한다.
    - "제가 하겠습니다", "해보겠습니다", "정리할게요", "올리겠습니다", "공유하겠습니다" 등도 포함한다.
    - 단순히 "필요합니다", "고려해야 합니다" 등은 여전히 수행 의지가 없으므로 Action 아님.
4️⃣ Action은 "명확한 업무 단위"로 작성한다. (예: "오류 확인", "오류 수정", "매뉴얼 작성", "자료 준비", "회의 일정 확인")
5️⃣ "담당자 지정"은 하지 않는다. → 역할분배 Agent가 따로 담당한다.
6️⃣ 중복 Action은 한 번만 추출한다.

[Action 일정 추론 규칙]
- 각 Action별로 "언제까지 해야 하는지"의 예상 일정을 회의 맥락에서 최대한 추론하여 "schedule"에 반드시 입력한다.
- 회의에서 일정이 명확히 언급되지 않은 경우 "미정" 또는 "언급 없음" 등으로 표기한다.
**중요**
- 일정, 날짜, 기간 등 시간 관련 표현이 '오늘', '이번주 내', '내일', '다음주' 등 상대적 표현으로 등장하면 반드시 회의날짜(meeting_date)를 기준으로 실제 날짜로 변환해서 명확하게 표기해.
    - 예시: 오늘 → {meeting_date}
    - 날짜 계산이 애매하면 반드시 회의 날짜({meeting_date}) 기준으로 표기해.

[강화된 예외 규칙]  
- **"수정이 필요합니다", "해결해야 할 것 같습니다", "고려해봐야 합니다", "논의가 필요합니다", "문제가 있습니다"** → Action 아님 (단순 의견/제안/필요성 언급 → 수행 의지 없음 → Action 금지)
- "회의에서 실제로 실행 책임이 확정되지 않은 것"은 Action으로 추출 금지
- **이 문장에서 "수행하고자 하는 의지가 명확하게 보이는지" 반드시 판단하라. → 명확한 수행 의지가 없는 경우 Action으로 추출하지 않는다.**
- Action으로 추출할지 말지는 "수행 의지 여부"를 가장 우선 기준으로 삼는다.

[참고 사항]
- 회의 주제와 (안건이 있는 경우) 회의 안건을 참고하여, 해당 회의 맥락에서 실제 실행해야 하는 Action만 정확하게 추출하라.

[빈 경우 출력 규칙]
- 만약 회의 대화록에서 "구체적인 실행 업무 (Action)"가 전혀 발견되지 않는 경우, 아래 형식으로 출력한다:

{{
  "todos": [],
  "summary": "이번 회의에서는 구체적인 실행 업무가 아직 논의되지 않았습니다.",
  "total_count": 0
}}

- 빈 경우에도 반드시 위 형식 그대로 출력할 것.

[출력 형식]
{{
  "todos": [
    {{
      "action": "",    // 명확한 업무 단위
      "context": "",   // 해당 Action이 나온 회의 원문 문장
      "schedule": ""   // 해당 Action의 예상 일정 (예: "2025-06-10(화)" 일정 언급 없으면 "미정" 또는 "언급 없음" 등으로 표기)
    }},
    ...
  ],
  "summary": "",      // 이번 회의에서 발생한 할일을 간단하게 요약
  "total_count": 0    // 총 할일 개수
}}

[중요]
- Action은 "실제 해야 하는 업무"만 추출한다.
- 반드시 "수행하고자 하는 의지가 보이는 발언"인 경우만 Action으로 추출한다.
- 담당자 배정은 하지 않는다. (speaker 정보도 포함하지 않는다)
- 이후 역할분배 Agent가 담당자를 배정할 것이므로, "Action + context" 만 정확하게 추출하는 것이 가장 중요하다.

지금부터 아래 대화록을 분석하여 위 기준으로 Action만 추출해줘:

<<< 회의 대화록 텍스트 >>>
{chr(10).join(relevant_sentences)}
'''

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1200,
        )
        
        content = response.choices[0].message.content.strip()
        if not content:
            # 빈 응답일 때
            output = {
                "todos": [],
                "summary": "이번 회의에서는 구체적인 실행 업무가 아직 논의되지 않았습니다.",
                "total_count": 0
            }
            print("[lang_todo] extract_todos 결과:", flush=True)
            print(json.dumps(output, ensure_ascii=False, indent=2), flush=True)
            if not output["todos"]:
                print("[lang_todo] [경고] 추출된 Action이 없습니다. (todos가 빈 리스트)", flush=True)
            else:
                print(f"[lang_todo] 추출된 Action 개수: {len(output['todos'])}", flush=True)
            return output

        # 코드블록 제거 및 JSON만 추출
        if content.startswith("```json"):
            content = content.removeprefix("```json").removesuffix("```").strip()
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            content = match.group()
            result = json.loads(content)
        else:
            # JSON이 없을 때
            result = {
                "todos": [],
                "summary": "이번 회의에서는 구체적인 실행 업무가 아직 논의되지 않았습니다.",
                "total_count": 0
            }
        output = {
            "todos": result.get("todos", []),
            "summary": result.get("summary", "이번 회의에서는 구체적인 실행 업무가 아직 논의되지 않았습니다."),
            "total_count": result.get("total_count", len(result.get("todos", [])))
        }
        # schedule 변환 적용
        if meeting_date and output["todos"]:
            for todo in output["todos"]:
                if "schedule" in todo and todo["schedule"]:
                    todo["schedule"] = parse_relative_schedule(todo["schedule"], meeting_date)
        print("[lang_todo] extract_todos 결과:", flush=True)
        print(json.dumps(output, ensure_ascii=False, indent=2), flush=True)
        if not output["todos"]:
            print("[lang_todo] [경고] 추출된 Action이 없습니다. (todos가 빈 리스트)", flush=True)
        else:
            print(f"[lang_todo] 추출된 Action 개수: {len(output['todos'])}", flush=True)
        # full_meeting_sentences 생성 (청크 경계 표시)
        full_meeting_sentences = []
        for idx, chunk in enumerate(chunks):
            full_meeting_sentences.append(f"=== 청크 {idx+1} 시작 ===")
            sentences = [s.strip() for s in chunk.split('\n') if s.strip()]
            full_meeting_sentences.extend(sentences)

        # 역할분배 agent 호출 (chunks 대신 full_meeting_sentences 전달)
        # 단 한 번만 호출되도록 보장
        assigned_roles = assign_roles(subject, full_meeting_sentences, attendees_list, output, agenda, meeting_date)
        return {
            "todos_result": output,
            "assigned_roles": assigned_roles,
            "agenda": agenda,
            "meeting_date": meeting_date
        }
        
    except Exception as e:
        print(f"[extract_todos] 오류: {e}", flush=True)
        return {
            "todos": [],
            "summary": "할 일 추출 중 오류가 발생했습니다.",
            "total_count": 0,
            "error": str(e),
            "agenda": agenda,
            "meeting_date": meeting_date
        } 