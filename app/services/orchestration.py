from langchain.agents import Tool, initialize_agent
from langchain.agents.agent_types import AgentType
from langchain_community.chat_models import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from app.services.lang_search import run_langchain_search
from app.services.docs_service.docs_recommend import run_doc_recommendation
from app.core.config import settings
import re
from app.services.docs_service.draft_log_crud import insert_draft_log
import asyncio
import json
import os # <-- os 모듈 추가 (환경 변수 사용을 위해)

# ==============================================================================
# 1. LLM 초기화 및 환경 변수 설정
# ==============================================================================

# Google API Key 설정 (환경 변수 또는 settings.py에서 가져옴)
# `os.getenv`를 사용하여 환경 변수를 우선적으로 확인합니다.
google_api_key = os.getenv("GOOGLE_API_KEY", settings.GOOGLE_API_KEY)
if not google_api_key:
    raise ValueError("GOOGLE_API_KEY is not set in environment variables or settings.")

# # Gemini Pro 모델 초기화
# # Note: 이제 llm 변수가 ChatGoogleGenerativeAI 인스턴스입니다.
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0, google_api_key=google_api_key)

# openai_api_key = settings.OPENAI_API_KEY
# llm = ChatOpenAI(temperature=0)

# 검색 도구 실행 함수 - 현재 미사용으로 주석 처리
# async def smart_search(query: str) -> str:
#     return run_langchain_search(query)

# 검색 도구 Tool 정의 - 현재 미사용으로 주석 처리
#search_tool = Tool(
#     name="Web Search",
#     func=smart_search,
#     description="Use this tool to search for document templates like resumes, reports, or proposals."
# )

# 상위 판단 함수: 외부 문서 양식이 필요한지 여부를 LLM이 결정 - 현재 미사용으로 주석 처리
# async def should_use_search_tool(meeting_text: str) -> bool:
#     system_prompt = """
# 당신은 회의 분석 AI입니다. 아래 회의 내용을 읽고, 이 회의에서 문서 양식(예: 이력서 양식, 보고서 양식, 제안서 양식 등)을 외부에서 검색해야 할 필요가 있는지 판단하세요.
#
# 다음 중 하나라도 포함된다면 'Yes'라고 답하세요:
# - 어떤 문서 양식을 찾으라는 지시가 있다
# - 양식이 필요하다는 언급이 있다
# - 문서 작성을 위해 참고 자료가 필요하다는 내용이 있다
#
# 단순히 회의 요약이나 업무 분배는 제외합니다.
#
# 'Yes' 또는 'No'만 출력하세요.
# """
#     prompt = system_prompt + f"\n\n회의 내용:\n{meeting_text}"
#     response = llm.invoke(prompt).content # <-- .predict() 대신 .invoke().content 사용
#     return "yes" in response.lower()

# 외부 문서 서칭 상위 에이전트 - 현재 미사용으로 주석 처리
# async def super_agent_for_meeting(meeting_text: str, db=None, meeting_id=None) -> str:
#     print("[상위 에이전트] 회의 텍스트 분석 중...")
#     results = []
#
#     # 1. 외부 문서 양식 검색 판단 및 실행 - 미사용으로 주석 처리
#     if should_use_search_tool(meeting_text):
#         print("[상위 에이전트] 외부 문서 양식 검색 필요 판단됨.")
#
#         # 검색 키워드 추출 프롬프트
#         extract_prompt = f"""
#     너는 웹 검색 결과를 기반으로 회의에서 필요한 자료를 찾는 LLM 에이전트야.
#
#     다음 회의 내용을 바탕으로, 문서나 가이드가 필요한 경우에는:
#     1. 필요한 키워드를 생성하고,
#     2. 해당 키워드로 웹 검색 결과(Observation)를 분석해서,
#     3. Final Answer에는 반드시 실제 URL을 **하나 이상 포함된 문장**으로 작성해야 해.
#
#     **중요 규칙:**
#     - Final Answer에는 `https://`로 시작하는 실제 링크(URL)를 반드시 넣어야 해. 없는 경우 오류로 간주함.
#     - `https://example.com/...` 과 같은 예시 URL을 넣으면 안 됨.
#     - 일반적인 설명, 요약, 의도 파악 말고, 실제 링크만 포함해.
#     - 예외 없이 Observation에서 나온 실제 링크만 사용해야 함.
#
#
#
#     회의 내용:
#     {meeting_text}
#
#     너의 응답은 다음 형식을 따라야 해:
#     - 검색 키워드: ...
#     - Final Answer: [링크 포함된 설명 문장]
# """
#
#         keyword = llm.invoke(extract_prompt).content # <-- .predict() 대신 .invoke().content 사용
#         print(f"[상위 에이전트] 외부 검색 키워드: {keyword}")
#
#         # 실제 외부 검색 수행
#         external_result = smart_search(keyword)
#         results.append(f"**외부 문서 양식:**\n{external_result}")
#     else:
#         print("[상위 에이전트] 외부 문서 양식 검색 불필요.")


# 문서 필요성 판단 Tool
async def analyze_meeting_for_documents(meeting_text: str) -> str:
    result = await should_use_internal_doc_tool(meeting_text)
    return "Yes" if result else "No"

# 회의 내용에서 키워드 추출 Tool
async def extract_keywords_from_meeting(meeting_text: str) -> str:
    keywords = await extract_internal_doc_keywords(meeting_text)
    return "\n".join(keywords)

# 내부 문서 추천 Tool
async def doc_recommendation(query: str) -> dict:
    return await run_doc_recommendation(query)


# Tool 인스턴스 생성
meeting_analysis_tool = Tool(
    name="Meeting Analysis",
    func=analyze_meeting_for_documents,
    description="Analyze meeting content to determine if internal documents are needed. Returns 'Yes' or 'No'.",
    coroutine=analyze_meeting_for_documents
)

keyword_extraction_tool = Tool(
    name="Keyword Extraction",
    func=extract_keywords_from_meeting,
    description="Extract internal document keywords from meeting content. Returns keywords separated by newlines.",
    coroutine=extract_keywords_from_meeting
)

doc_recommendation_tool = Tool(
    name="Document Recommendation",
    func=doc_recommendation,
    description="Use this tool to recommend documents for the meeting based on keywords extracted from meeting content.",
    coroutine=doc_recommendation
)


async def should_use_internal_doc_tool(meeting_text: str) -> bool:
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
    response = llm.invoke(prompt).content # <-- .predict() 대신 .invoke().content 사용
    return "yes" in response.lower()

async def extract_internal_doc_keywords(meeting_text: str) -> list[str]:
    extract_prompt = f"""
다음 회의 내용에서 내부 문서 검색을 위한 **문서 양식 키워드**를 2개 추출하세요.

회의에서 분담된 역할과 업무를 분석하여
필요한 내부 문서 유형 (예: 결재서류, 업무보고서, 프로젝트 계획서, 회의록 등)을 검색 키워드로 2개 생성하세요.
예를 들어, 키워드는 "회의록 작성 문서", "회의록 양식 문서", "기획서 작성 문서", "기획서 양식 문서", "공지 문서" 등이 될 수 있습니다.

회의 내용:
{meeting_text}

키워드만 한 줄에 하나씩 출력하세요:
"""
    keywords_text = llm.invoke(extract_prompt).content # <-- .predict() 대신 .invoke().content 사용
    keywords = [kw.strip() for kw in keywords_text.splitlines() if kw.strip()]
    print("추출된 키워드 : ", keywords)
    return keywords




# Agent 초기화
tools = [meeting_analysis_tool, keyword_extraction_tool, doc_recommendation_tool]

agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True,
)

def create_agent_prompt(meeting_text: str) -> str:
    """
    Agent가 전체 프로세스를 수행하도록 하는 통합 프롬프트 생성
    """
    return f"""
당신은 회의 내용을 분석하여 필요한 내부 문서를 추천하는 전문 에이전트입니다.
다음 단계를 순서대로 수행해주세요:

**1단계: 내부 문서 필요성 판단**
- Meeting Analysis 도구를 사용하여 회의 내용을 분석하고 내부 문서가 필요한지 판단하세요.
- 결과가 'No'라면 "이 회의에서는 문서 양식을 검색할 필요가 없습니다."라고 답하고 종료하세요.

**2단계: 키워드 추출 (1단계에서 'Yes'인 경우만)**
- Keyword Extraction 도구를 사용하여 회의 내용에서 내부 문서 검색용 키워드를 추출하세요.
- 추출된 키워드들을 확인하고 중복을 제거하세요.

**3단계: 문서 추천 (각 키워드별로)**
- 2단계에서 추출된 각 키워드에 대해 Document Recommendation 도구를 사용하여 문서를 추천받으세요.
- 각 키워드별로 별도의 Document Recommendation 호출을 수행하세요.

**최종 결과 형식:**
각 키워드별로 다음과 같은 형식으로 결과를 정리해주세요:

키워드: [키워드명]
[Document Recommendation 도구가 반환한 JSON 결과를 그대로 복사하여 붙여넣기]


**중요 지침:**
- 반드시 위의 1-2-3 단계를 순서대로 수행하세요.
- Document Recommendation 도구의 결과는 절대 수정하지 마세요. 받은 JSON을 그대로 출력하세요.
- download_url 필드의 실제 URL을 임의로 변경하거나 축약하지 마세요.
- 도구의 결과를 "요약"하거나 "정리"하지 마세요. 원본 그대로 출력하세요.
- JSON 형식을 유지하고, 모든 필드(title, download_url, similarity_score, relevance_reason)를 그대로 보존하세요.

**예시 출력 형식:**
키워드: 예시키워드
{{
"documents": [
{{
"title": "문서제목.docx",
"download_url": "https://실제URL주소",
"similarity_score": 0.85,
"relevance_reason": "실제 이유 설명"
}}
]
}}


**분석할 회의 내용:**
{meeting_text}
"""

async def super_agent_for_meeting(meeting_text: str, db=None, meeting_id=None) -> str:
    """
    Agent가 전체 프로세스를 수행하도록 리팩토링된 메인 함수
    
    Args:
        meeting_text: 분석할 회의 내용
        db: 데이터베이스 연결 객체 (선택적)
        meeting_id: 회의 ID (선택적, DB 저장용)
    
    Returns:
        Agent가 수행한 전체 프로세스 결과
    """
    print("[LangChain Agent] 회의 텍스트 분석 시작...")
    
    try:
        # Agent용 통합 프롬프트 생성
        agent_prompt = create_agent_prompt(meeting_text)
        
        # Agent 실행 - 전체 프로세스를 Agent가 자율적으로 수행
        print("[LangChain Agent] Agent 실행 중 (내부 문서 필요성 판단 → 키워드 추출 → 문서 추천)...")
        agent_result = await agent.ainvoke({"input": agent_prompt})
        
        # Agent 결과 추출
        if isinstance(agent_result, dict) and 'output' in agent_result:
            final_result = agent_result['output']
        else:
            final_result = str(agent_result)
        
        print("[LangChain Agent] Agent 실행 완료")
        
        # DB 저장 처리 (기존 로직 유지)
        if db is not None and meeting_id is not None:
            await save_results_to_db(final_result, meeting_text, db, meeting_id)
        
        return final_result
        
    except Exception as e:
        print(f"[Agent 실행 오류] {e}")
        # 오류 발생 시 fallback으로 기존 방식 사용
        return await fallback_processing(meeting_text, db, meeting_id)


async def save_results_to_db(agent_result: str, meeting_text: str, db, meeting_id: str):
    """
    Agent 결과를 DB에 저장하는 함수 (문제 해결된 버전)
    
    Args:
        agent_result: Agent가 반환한 전체 결과
        meeting_text: 원본 회의 내용
        db: 데이터베이스 연결 객체
        meeting_id: 회의 ID
    """
    print("[DB 저장] Agent 결과를 DB에 저장 중...")
    print(f"[DEBUG] Agent 결과 길이: {len(agent_result)} 문자")
    print(f"[DEBUG] Meeting ID: {meeting_id}")
    
    # 중복 방지를 위한 세트 (title, link 조합으로 중복 체크)
    saved_documents = set()
    
    try:
        # Agent 결과 파싱 개선
        print("[DEBUG] Agent 결과 파싱 시작...")
        
        # 키워드별 섹션을 더 정확하게 파싱
        sections = []
        lines = agent_result.split('\n')
        current_section = ""
        current_keyword = ""
        
        for line in lines:
            # 키워드 라인 감지 (다양한 패턴 고려)
            if line.strip().startswith('키워드:') or 'keyword:' in line.lower():
                # 이전 섹션 저장
                if current_keyword and current_section:
                    sections.append((current_keyword, current_section))
                
                # 새 키워드 시작
                current_keyword = line.replace('키워드:', '').replace('keyword:', '').strip()
                current_section = ""
                print(f"[DEBUG] 키워드 발견: {current_keyword}")
            else:
                current_section += line + '\n'
        
        # 마지막 섹션 추가
        if current_keyword and current_section:
            sections.append((current_keyword, current_section))
        
        print(f"[DEBUG] 총 {len(sections)}개 섹션 파싱됨")
        
        # 섹션이 없으면 전체 텍스트에서 문서 정보 추출 시도
        if not sections:
            print("[DEBUG] 섹션 파싱 실패, 전체 텍스트에서 문서 추출 시도...")
            documents = extract_document_info_from_output(agent_result)
            if documents:
                sections = [("일반", agent_result)]
                print(f"[DEBUG] 전체 텍스트에서 {len(documents)}개 문서 발견")
        
        # 각 섹션 처리
        saved_count = 0
        for i, (keyword, section_content) in enumerate(sections):
            print(f"[DEBUG] 섹션 {i+1}/{len(sections)} 처리 중: 키워드='{keyword}'")
            
            try:
                # 문서 정보 추출
                documents = extract_document_info_from_output(section_content)
                print(f"[DEBUG] 키워드 '{keyword}'에서 {len(documents)}개 문서 추출됨")
                
                if documents:
                    for j, doc in enumerate(documents):
                        print(f"[DEBUG] 문서 {j+1}/{len(documents)} 처리 중...")
                        
                        title = doc.get("title", "").strip()
                        link = doc.get("download_url", "").strip()
                        similarity_score = doc.get("similarity_score", 0)
                        relevance_reason = doc.get("relevance_reason", "").strip()
                        
                        print(f"[DEBUG] 문서 정보: title='{title}', link='{link}', score={similarity_score}")
                        
                        # 중복 체크 - title과 link 조합으로 체크
                        doc_key = (title, link)
                        if doc_key in saved_documents:
                            print(f"[중복 스킵] 이미 저장된 문서: title='{title}', link='{link}'")
                            continue
                        
                        if title:
                            try:
                                # DB 저장 시도
                                print(f"[DEBUG] DB 저장 시도: meeting_id={meeting_id}, keyword={keyword}")
                                
                                # ref_interdoc_id 결정 로직 개선
                                # 1. download_url이 있으면 그것을 사용
                                # 2. download_url이 없으면 title을 사용하되, 구분을 위해 prefix 추가
                                if link and link.startswith(('http://', 'https://')):
                                    ref_interdoc_id = link
                                    print(f"[DEBUG] URL을 ref_interdoc_id로 사용: {ref_interdoc_id}")
                                else:
                                    ref_interdoc_id = f"internal_doc:{title}"
                                    print(f"[DEBUG] 파일명을 ref_interdoc_id로 사용: {ref_interdoc_id}")
                                
                                await insert_draft_log(
                                    db=db,
                                    meeting_id=meeting_id,
                                    draft_ref_reason=keyword or "문서 추천",
                                    ref_interdoc_id=ref_interdoc_id,
                                    draft_title=title
                                )
                                
                                # 중복 방지를 위해 저장된 문서 기록
                                saved_documents.add(doc_key)
                                saved_count += 1
                                print(f"[저장 완료 {saved_count}] 키워드={keyword}, title={title}, ref_id={ref_interdoc_id}")
                                
                            except Exception as db_error:
                                print(f"[DB 저장 오류] 키워드={keyword}, title={title}, 오류={db_error}")
                                print(f"[DB 저장 오류 상세] 오류 타입: {type(db_error).__name__}")
                                # DB 오류가 발생해도 다음 문서 계속 처리
                                continue
                        else:
                            print(f"[저장 스킵] 키워드={keyword}, title 없음 (빈 문자열)")
                else:
                    print(f"[저장 스킵] 키워드={keyword}, 문서 정보 추출 실패")
                    print(f"[DEBUG] 섹션 내용 (처음 200자): {section_content[:200]}...")
                    
            except Exception as section_error:
                print(f"[섹션 처리 오류] 키워드={keyword}, 오류={section_error}")
                print(f"[섹션 처리 오류 상세] 오류 타입: {type(section_error).__name__}")
                continue
        
        print(f"[DB 저장 완료] 총 {saved_count}개 문서 저장됨 (중복 제거됨)")
        print(f"[DEBUG] 저장된 문서 목록: {saved_documents}")
        
        if saved_count == 0:
            print("[경고] 저장된 문서가 없습니다.")
            print(f"[DEBUG] 원본 Agent 결과:")
            print("=" * 50)
            print(agent_result)
            print("=" * 50)
                
    except Exception as e:
        print(f"[DB 저장 전체 오류] {e}")
        print(f"[DB 저장 전체 오류 상세] 오류 타입: {type(e).__name__}")
        import traceback
        print(f"[DB 저장 전체 오류 스택트레이스]:")
        print(traceback.format_exc())
        
        # 롤백 시도
        try:
            if hasattr(db, 'rollback'):
                await db.rollback()
                print("[DB 롤백 완료]")
        except Exception as rollback_error:
            print(f"[DB 롤백 오류] {rollback_error}")

# extract_document_info_from_output 함수도 개선하여 실제 JSON 구조를 더 잘 파싱
def extract_document_info_from_output(output):
    """
    Agent 출력에서 문서 정보를 추출하는 개선된 함수
    """
    print(f"[DEBUG extract_function] 입력 타입: {type(output)}")
    print(f"[DEBUG extract_function] 입력 길이: {len(str(output))}")
    
    documents = []
    try:
        if isinstance(output, dict):
            documents = output.get("documents", [])
            print(f"[DEBUG extract_function] dict에서 {len(documents)}개 문서 추출")
            
        elif isinstance(output, str):
            # 1. JSON 블록 찾기 (```json ... ``` 형태)
            json_pattern = r'```json\s*(\{.*?\})\s*```'
            json_match = re.search(json_pattern, output, re.DOTALL | re.IGNORECASE)
            
            if json_match:
                print("[DEBUG extract_function] JSON 블록 발견")
                try:
                    parsed = json.loads(json_match.group(1))
                    documents = parsed.get("documents", [])
                    print(f"[DEBUG extract_function] JSON 블록에서 {len(documents)}개 문서 추출")
                except json.JSONDecodeError as je:
                    print(f"[DEBUG extract_function] JSON 블록 파싱 실패: {je}")
            
            # 2. JSON 블록이 없으면 일반 JSON 찾기
            if not documents:
                # 더 유연한 JSON 패턴 - documents 배열이 포함된 JSON 찾기
                json_pattern2 = r'\{\s*"documents"\s*:\s*\[.*?\]\s*\}'
                json_matches = re.findall(json_pattern2, output, re.DOTALL)
                
                for match in json_matches:
                    try:
                        parsed = json.loads(match)
                        found_docs = parsed.get("documents", [])
                        documents.extend(found_docs)
                        print(f"[DEBUG extract_function] 일반 JSON에서 {len(found_docs)}개 문서 추가")
                    except json.JSONDecodeError:
                        continue
            
            # 3. 개별 문서 객체 찾기 (documents 배열 없이 개별 객체로 나열된 경우)
            if not documents:
                print("[DEBUG extract_function] 개별 문서 객체 검색 시작")
                # title, download_url 등이 포함된 JSON 객체 찾기
                doc_pattern = r'\{\s*"title"\s*:\s*"[^"]+"\s*,.*?\}'
                doc_matches = re.findall(doc_pattern, output, re.DOTALL)
                
                for match in doc_matches:
                    try:
                        parsed = json.loads(match)
                        if "title" in parsed:
                            documents.append(parsed)
                            print(f"[DEBUG extract_function] 개별 문서 객체 추출: {parsed.get('title')}")
                    except json.JSONDecodeError:
                        continue
            
            # 4. JSON이 없으면 파일명 패턴으로 찾기
            if not documents:
                print("[DEBUG extract_function] JSON 없음, 파일명 패턴 검색 시작")
                
                # 다양한 파일명 패턴 시도
                patterns = [
                    r'"([^"]+\.(pptx|docx|xlsx|pdf|hwp))"',  # 따옴표로 둘러싸인 파일명
                    r'([a-zA-Z가-힣0-9_\-\.]+\.(pptx|docx|xlsx|pdf|hwp))',  # 일반 파일명
                    r'title[:\s]*"?([^"\n]+\.(pptx|docx|xlsx|pdf|hwp))"?'  # title: 뒤의 파일명
                ]
                
                for pattern in patterns:
                    file_matches = re.findall(pattern, output, re.IGNORECASE)
                    if file_matches:
                        for file_match in file_matches:
                            if isinstance(file_match, tuple):
                                title = file_match[0]
                            else:
                                title = file_match
                            
                            # 중복 제거
                            if not any(doc["title"] == title for doc in documents):
                                documents.append({
                                    "title": title,
                                    "download_url": "",
                                    "similarity_score": 0.0,
                                    "relevance_reason": f"파일명 패턴에서 추출 (패턴: {pattern})"
                                })
                                print(f"[DEBUG extract_function] 파일명 패턴에서 추출: {title}")
                        break  # 첫 번째 패턴에서 찾으면 다음 패턴은 시도하지 않음

        # download_url, similarity_score, relevance_reason 기본값 설정
        for doc in documents:
            if doc.get("download_url") is None:
                doc["download_url"] = ""
            if doc.get("similarity_score") is None:
                doc["similarity_score"] = 0.0
            if doc.get("relevance_reason") is None:
                doc["relevance_reason"] = "문서 추천"
                
        print(f"[DEBUG extract_function] 최종 추출된 문서 수: {len(documents)}")
        for i, doc in enumerate(documents):
            print(f"[DEBUG extract_function] 문서 {i+1}: {doc}")
        
    except Exception as e:
        print(f"[DEBUG extract_function] 문서 정보 추출 오류: {e}")
        print(f"[DEBUG extract_function] 오류 타입: {type(e).__name__}")
        import traceback
        print(f"[DEBUG extract_function] 스택트레이스:")
        print(traceback.format_exc())

    return documents

# Agent 출력에서 실제 다운로드 URL을 추출하는 함수 추가
def extract_download_urls_from_output(output):
    """
    Agent 출력에서 실제 다운로드 URL을 추출하는 함수
    """
    urls = []
    try:
        # HTTP/HTTPS URL 패턴 찾기
        url_pattern = r'https?://[^\s\'"<>)}\]]+(?:\.[^\s\'"<>)}\]]+)*'
        found_urls = re.findall(url_pattern, output)
        
        for url in found_urls:
            # 파일 확장자가 있는 URL만 필터링
            if any(ext in url.lower() for ext in ['.docx', '.pptx', '.xlsx', '.pdf', '.hwp']):
                urls.append(url)
                print(f"[DEBUG] 다운로드 URL 발견: {url}")
    
    except Exception as e:
        print(f"[DEBUG] URL 추출 오류: {e}")
    
    return urls

async def fallback_processing(meeting_text: str, db=None, meeting_id=None) -> str:
    """
    Agent 실행 실패 시 사용하는 fallback 함수 (기존 방식)
    
    Args:
        meeting_text: 분석할 회의 내용
        db: 데이터베이스 연결 객체
        meeting_id: 회의 ID
    
    Returns:
        기존 방식으로 처리된 결과
    """
    print("[Fallback] 기존 방식으로 처리 중...")
    results = []

    # 1단계: 내부 문서 필요성 판단
    if await should_use_internal_doc_tool(meeting_text):
        print("[Fallback] 내부 문서 양식 검색 필요 판단됨.")
        
        # 2단계: 키워드 추출
        internal_keywords = await extract_internal_doc_keywords(meeting_text)
        internal_keywords = list(set(internal_keywords))  # 중복 제거

        # 3단계: 각 키워드별 문서 추천
        for keyword in internal_keywords:
            print(f"[Fallback] 키워드 처리 중: {keyword}")
            try:
                # 문서 추천 실행
                internal_result = await doc_recommendation(keyword)
                
                # 결과 포맷팅
                results.append(f"**키워드: {keyword}**\n{internal_result}")

                # DB 저장
                if db is not None and meeting_id is not None:
                    documents = extract_document_info_from_output(internal_result)
                    if documents:
                        doc = documents[0]
                        title = doc.get("title", "")
                        link = doc.get("download_url", "")
                        
                        if title:
                            await insert_draft_log(
                                db=db,
                                meeting_id=meeting_id,
                                draft_ref_reason=keyword,
                                ref_interdoc_id=link or title,
                                draft_title=title
                            )
                            print(f"[Fallback 저장 완료] title={title}, link={link}")
            except Exception as e:
                print(f"[Fallback 키워드 처리 오류] 키워드={keyword}, 오류={e}")
                continue
    else:
        print("[Fallback] 내부 문서 양식 검색 불필요.")

    return "\n\n".join(results) if results else "이 회의에서는 문서 양식을 검색할 필요가 없습니다."

# 테스트용 실행 코드
if __name__ == "__main__":
    # 비동기 함수 실행을 위해 asyncio.run() 사용
    async def main():
        sample_meeting = """
이번 주 금요일까지 마케팅 전략 보고서를 작성해야 합니다. 이전 팀에서 사용했던 보고서 양식이 괜찮아 보였어요.
혹시 참고할 만한 보고서 템플릿이 있으면 공유 부탁드립니다.
김철수님은 시장 분석 부분을, 이영희님은 경쟁사 분석을 담당해주시고, 
박지민님은 내부 승인을 위한 결재 문서도 준비해주세요.
"""
        result = await super_agent_for_meeting(sample_meeting)
        print("\n[최종 응답]")
        print(result)

    # 비동기 메인 함수 실행
    asyncio.run(main())