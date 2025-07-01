from langchain_openai import ChatOpenAI
import datetime
import re, json
from typing import Optional, Dict, Any

async def lang_previewmeeting(
    summary_data: Dict[str, Any], 
    subject: str, 
    attendees_list: Optional[list] = None, 
    project_id: Optional[str] = None,
    meeting_date: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    요약 데이터에서 다음 회의/미팅에 대한 언급을 추출하여 Meeting 테이블 형태로 반환
    
    Args:
        summary_data (dict): lang_summary에서 생성된 요약 데이터
        subject (str): 원본 회의 주제
        attendees_list (list, optional): 참석자 목록
        project_id (str, optional): 프로젝트 ID
        meeting_date (str, optional): 현재 회의 날짜 (YYYY-MM-DD 형식)
    
    Returns:
        dict: Meeting 테이블에 insert할 데이터 또는 None (다음 회의가 없는 경우)
    """
    
    llm = ChatOpenAI(model="gpt-4", temperature=0)
    
    # meeting_date를 기반으로 날짜 계산
    if meeting_date:
        try:
            meeting_date_only = meeting_date.split()[0]
            meeting_date_obj = datetime.datetime.strptime(meeting_date_only, '%Y-%m-%d').date()
            today_str = meeting_date_obj.strftime('%Y.%m.%d(%a)')
        except Exception as e:
            print(f"[lang_previewmeeting] 날짜 파싱 오류: {e}", flush=True)
            today = datetime.date.today()
            today_str = today.strftime('%Y.%m.%d(%a)')
    else:
        today = datetime.date.today()
        today_str = today.strftime('%Y.%m.%d(%a)')
    
    # 요약 데이터를 문자열로 변환
    summary_text = json.dumps(summary_data, ensure_ascii=False, indent=2)
    
    print(f"[lang_previewmeeting] === 시작 ===", flush=True)
    print(f"[lang_previewmeeting] 입력 subject: {subject}", flush=True)
    print(f"[lang_previewmeeting] 입력 project_id: {project_id}", flush=True)
    print(f"[lang_previewmeeting] 입력 meeting_date: {meeting_date}", flush=True)
    print(f"[lang_previewmeeting] 요약 데이터: {summary_text}", flush=True)
    
    # 사전 필터링: 회의 관련 키워드가 없으면 LLM 호출 생략
    meeting_keywords = [
        # 직접적 회의 용어
        "회의", "미팅", "meeting", "리뷰", "검토", "승인",
        
        # lang_summary 결과에 자주 나오는 패턴
        "일정:", "예정", "계획",
        
        # 날짜 관련 (lang_summary가 변환한 형태)
        "오전", "오후", "시", "AM", "PM",
        "(mon)", "(tue)", "(wed)", "(thu)", "(fri)", "(sat)", "(sun)",
        "(월)", "(화)", "(수)", "(목)", "(금)", "(토)", "(일)"
    ]
    
    summary_text_lower = summary_text.lower()
    has_meeting_keyword = any(keyword in summary_text_lower for keyword in meeting_keywords)
    
    # 발견된 키워드 출력
    found_keywords = [keyword for keyword in meeting_keywords if keyword in summary_text_lower]
    print(f"[lang_previewmeeting] 발견된 키워드: {found_keywords}", flush=True)
    
    if not has_meeting_keyword:
        print("[lang_previewmeeting] 회의 관련 키워드 없음, LLM 호출 생략", flush=True)
        return None
    
    print("[lang_previewmeeting] 회의 관련 키워드 발견, LLM 호출 진행", flush=True)
    
    prompt = f"""
    너는 회의록에서 다음 회의/미팅 정보를 추출하는 전문가야.

    현재 회의 날짜: {today_str}
    현재 회의 주제: {subject}

    아래는 회의 요약 데이터야:
    {summary_text}

    **임무:**
    위 요약 데이터에서 **다음 회의, 다음 미팅, 후속 회의, 리뷰 미팅** 등에 대한 명확한 언급이 있는지 확인하고, 
    있다면 해당 정보를 추출해줘.

    **추출 규칙:**
    1. **명확한 회의 언급만** 추출 (단순 작업 일정이나 데드라인 제외)
    2. 날짜가 명시된 회의 우선 추출
    3. 상대적 날짜("다음 주", "내일" 등)는 현재 회의 날짜({today_str}) 기준으로 실제 날짜로 변환
    4. 애매한 표현은 제외하고 구체적인 회의 언급만 추출

    **결과 형식:**
    다음 회의 언급이 **명확히** 있으면:
    ```json
    {{
        "has_next_meeting": true,
        "meeting_date": "YYYY-MM-DD HH:MM:SS",
        "meeting_agenda": "추출된 회의 안건/목적 (최대 1000자)",
        "extracted_content": "원본 요약에서 추출된 해당 문장"
    }}
    ```

    다음 회의 언급이 없거나 애매하면:
    ```json
    {{
        "has_next_meeting": false
    }}
    ```

    **중요:** 
    - meeting_date는 반드시 "YYYY-MM-DD HH:MM:SS" 형식으로 변환해줘
    - 시간이 명시되지 않으면 "09:00:00"으로 기본 설정
    - 날짜 변환이 불가능하면 has_next_meeting을 false로 설정
    """
    
    response = await llm.ainvoke(prompt)
    agent_output = str(response.content)
    
    # JSON 파싱 시도
    try:
        content = agent_output.strip()
        if content.startswith("```json"):
            content = content.removeprefix("```json").removesuffix("```").strip()
        
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            content = match.group()
            result_json = json.loads(content)
        else:
            result_json = {"has_next_meeting": False}
            
    except Exception as e:
        print(f"[lang_previewmeeting] JSON 파싱 오류: {e}", flush=True)
        result_json = {"has_next_meeting": False}
    
    print(f"[lang_previewmeeting] === LLM 응답 ===", flush=True)
    print(f"[lang_previewmeeting] agent_output: {agent_output}", flush=True)
    print(f"[lang_previewmeeting] 파싱된 result: {result_json}", flush=True)
    
    # 다음 회의가 없으면 None 반환
    if not result_json.get("has_next_meeting", False):
        print("[lang_previewmeeting] 다음 회의 없음, None 반환", flush=True)
        return None
    
    print("[lang_previewmeeting] 다음 회의 발견! 데이터 구성 시작", flush=True)
    
    # Meeting 테이블에 맞는 형태로 데이터 구성
    try:
        # 날짜 파싱 시도
        try:
            meeting_date_str = result_json.get("meeting_date", "")
            if isinstance(meeting_date_str, str) and meeting_date_str:
                meeting_datetime = datetime.datetime.strptime(
                    meeting_date_str, 
                    "%Y-%m-%d %H:%M:%S"
                )
            else:
                raise ValueError("Invalid date format")
        except:
            # 날짜 파싱 실패시 '미정'으로 설정 (임시로 현재 날짜 + 7일)
            meeting_datetime = datetime.datetime.now() + datetime.timedelta(days=7)
            print(f"[lang_previewmeeting] 날짜 파싱 실패, 미정으로 설정: {meeting_datetime}", flush=True)
        
        meeting_data = {
            "project_id": project_id,
            "meeting_title": f"{subject}_후속미팅",
            "meeting_date": meeting_datetime,
            "meeting_audio_path": "app/none"
        }
        
        print(f"[lang_previewmeeting] === 최종 결과 ===", flush=True)
        print(f"[lang_previewmeeting] 생성된 meeting_data:", flush=True)
        print(f"  - project_id: {meeting_data['project_id']}", flush=True)
        print(f"  - meeting_title: {meeting_data['meeting_title']}", flush=True)
        print(f"  - meeting_date: {meeting_data['meeting_date']}", flush=True)
        print(f"  - meeting_audio_path: {meeting_data['meeting_audio_path']}", flush=True)
        
        return meeting_data
        
    except Exception as e:
        print(f"[lang_previewmeeting] 데이터 구성 오류: {e}", flush=True)
        return None 