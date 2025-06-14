from langchain.agents import Tool, initialize_agent
from langchain.agents.agent_types import AgentType
from langchain_community.chat_models import ChatOpenAI
from app.services.lang_search import run_langchain_search
from app.services.docs_service.docs_recommend import run_doc_recommendation
from app.core.config import settings

openai_api_key = settings.OPENAI_API_KEY

# LLM 초기화
llm = ChatOpenAI(temperature=0)

# 하위 검색 에이전트 import


# 검색 도구로 등록할 함수
def smart_search(query: str) -> str:
    return run_langchain_search(query)

def doc_recommendation(query: str) -> str:
    return run_doc_recommendation(query)

# 검색 도구 정의
search_tool = Tool(
    name="Web Search",
    func=smart_search,
    description="Use this tool to search for document templates like resumes, reports, or proposals."
)

doc_recommendation_tool = Tool(
    name="Document Recommendation",
    func=doc_recommendation,
    description="Use this tool to recommend documents for the meeting."
)

# 상위 판단 함수: 외부 문서 양식이 필요한지 여부를 LLM이 결정
def should_use_search_tool(meeting_text: str) -> bool:
    system_prompt = """
당신은 회의 분석 AI입니다. 아래 회의 내용을 읽고, 이 회의에서 문서 양식(예: 이력서 양식, 보고서 양식, 제안서 양식 등)을 외부에서 검색해야 할 필요가 있는지 판단하세요.

다음 중 하나라도 포함된다면 'Yes'라고 답하세요:
- 어떤 문서 양식을 찾으라는 지시가 있다
- 양식이 필요하다는 언급이 있다
- 문서 작성을 위해 참고 자료가 필요하다는 내용이 있다

단순히 회의 요약이나 업무 분배는 제외합니다.

'Yes' 또는 'No'만 출력하세요.
"""
    prompt = system_prompt + f"\n\n회의 내용:\n{meeting_text}"
    response = llm.predict(prompt)
    return "yes" in response.lower()

# 내부 문서가 필요한지 판단하는 함수 추가
def should_use_internal_doc_tool(meeting_text: str) -> bool:
    system_prompt = """
당신은 회의 분석 AI입니다. 아래 회의 내용을 읽고, 이 회의에서 분담된 역할이나 업무에 따라 내부 문서 양식이나 템플릿이 필요한지 판단하세요.

다음 중 하나라도 포함된다면 'Yes'라고 답하세요:
- 특정 팀원에게 업무가 분담되어 내부 문서가 필요한 경우
- 내부 프로세스나 절차에 따른 문서 작성이 필요한 경우
- 회사 내부 양식이나 템플릿을 사용해야 하는 업무가 있는 경우
- 부서 간 협업을 위한 내부 문서가 필요한 경우
- 내부 보고서나 결재 문서가 필요한 경우

단순한 외부 참고 자료 검색은 제외합니다.

'Yes' 또는 'No'만 출력하세요.
"""
    prompt = system_prompt + f"\n\n회의 내용:\n{meeting_text}"
    response = llm.predict(prompt)
    return "yes" in response.lower()

# 내부 문서 서칭을 위한 키워드 추출 함수
def extract_internal_doc_keywords(meeting_text: str) -> str:
    extract_prompt = f"""
다음 회의 내용에서 내부 문서 검색을 위한 키워드를 추출하세요.

회의에서 분담된 역할과 업무를 분석하여:
1. 필요한 내부 문서 유형 (예: 결재서류, 업무보고서, 프로젝트 계획서 등)
2. 관련 부서나 팀
3. 업무 성격

을 고려한 검색 키워드를 생성하세요.

회의 내용:
{meeting_text}

키워드만 간단히 출력하세요 (예: "마케팅 전략 보고서 템플릿"):
"""
    return llm.predict(extract_prompt)

# 상위 에이전트 함수 (내부/외부 문서 통합)
def super_agent_for_meeting(meeting_text: str) -> str:
    print("[상위 에이전트] 회의 텍스트 분석 중...")
    
    results = []
    
    # 1. 외부 문서 양식 검색 판단 및 실행
    if should_use_search_tool(meeting_text):
        print("[상위 에이전트] 외부 문서 양식 검색 필요 판단됨.")
       
        # 검색 키워드 추출 프롬프트
        extract_prompt = f"""
    너는 웹 검색 결과를 기반으로 회의에서 필요한 자료를 찾는 LLM 에이전트야.

    다음 회의 내용을 바탕으로, 문서나 가이드가 필요한 경우에는:
    1. 필요한 키워드를 생성하고,
    2. 해당 키워드로 웹 검색 결과(Observation)를 분석해서,
    3. Final Answer에는 반드시 실제 URL을 **하나 이상 포함된 문장**으로 작성해야 해.

    **중요 규칙:**
    - Final Answer에는 `https://`로 시작하는 실제 링크(URL)를 반드시 넣어야 해. 없는 경우 오류로 간주함.
    - `https://example.com/...` 과 같은 예시 URL을 넣으면 안 됨.
    - 일반적인 설명, 요약, 의도 파악 말고, 실제 링크만 포함해.
    - 예외 없이 Observation에서 나온 실제 링크만 사용해야 함.



    회의 내용:
    {meeting_text}

    너의 응답은 다음 형식을 따라야 해:
    - 검색 키워드: ...
    - Final Answer: [링크 포함된 설명 문장]
"""

        keyword = llm.predict(extract_prompt)
        print(f"[상위 에이전트] 외부 검색 키워드: {keyword}")

        # 실제 외부 검색 수행
        external_result = smart_search(keyword)
        results.append(f"**외부 문서 양식:**\n{external_result}")
    else:
        print("[상위 에이전트] 외부 문서 양식 검색 불필요.")
    
    # 2. 내부 문서 양식 검색 판단 및 실행
    if should_use_internal_doc_tool(meeting_text):
        print("[상위 에이전트] 내부 문서 양식 검색 필요 판단됨.")
        
        # 내부 문서 검색 키워드 추출
        internal_keywords = extract_internal_doc_keywords(meeting_text)
        print(f"[상위 에이전트] 내부 검색 키워드: {internal_keywords}")
        
        # 실제 내부 문서 검색 수행
        internal_result = doc_recommendation(internal_keywords)
        results.append(f"**내부 문서 양식:**\n{internal_result}")
    else:
        print("[상위 에이전트] 내부 문서 양식 검색 불필요.")
    
    # 3. 결과 통합 및 반환
    if results:
        final_result = "\n\n".join(results)
        return final_result
    else:
        return "이 회의에서는 문서 양식을 검색할 필요가 없습니다."

# 테스트용 실행 코드
if __name__ == "__main__":
    sample_meeting = """
이번 주 금요일까지 마케팅 전략 보고서를 작성해야 합니다. 이전 팀에서 사용했던 보고서 양식이 괜찮아 보였어요.
혹시 참고할 만한 보고서 템플릿이 있으면 공유 부탁드립니다.
김철수님은 시장 분석 부분을, 이영희님은 경쟁사 분석을 담당해주시고, 
박지민님은 내부 승인을 위한 결재 문서도 준비해주세요.
"""
    result = super_agent_for_meeting(sample_meeting)
    print("\n[최종 응답]")
    print(result)