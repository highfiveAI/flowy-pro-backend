import openai
import os
import asyncio
import re
import json
from app.services.lang_summary import lang_summary
from app.services.lang_feedback import feedback_agent
from app.services.lang_role import assign_roles
from app.services.lang_todo import extract_todos
from typing import List, Dict, Any
from app.crud.crud_meeting import insert_summary_log, insert_task_assign_log, insert_feedback_log, get_feedback_type_map, insert_prompt_log
from sqlalchemy.orm import Session


openai_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def gpt_score_sentence_async(subject, prev_sent, target_sent, next_sent):
    """
    GPT API를 비동기로 사용해 대상 문장을 0~3단계로 평가 (openai 1.x 최신버전 대응)
    """
    prompt = (
        f'회의 주제: "{subject}"\n'
        f'앞 문장: "{prev_sent}"\n'
        f'대상 문장: "{target_sent}"\n'
        f'다음 문장: "{next_sent}"\n'
        "\n위 정보를 참고하여 대상 문장이 회의 주제와 얼마나 관련 있는지 0~3점으로 평가해줘.\n"
        "0: 전혀 관련 없음\n"
        "1: 약간 관련 있음 (빙빙 돌다 회의로 연결 가능)\n"
        "2: 관련 있음\n"
        "3: 핵심 관련\n"
        "아래와 같은 JSON 형식으로만 답변해줘:\n"
        '{\n  "score": (0~3 숫자),\n  "reason": "간단한 이유"\n}'
    )
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4-turbo",        #gpt-3.5-turbo는 성능이 많이 떨어짐.
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=256,
        )
        content = response.choices[0].message.content.strip()
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            return json.loads(match.group())
        else:
            return {"score": None, "reason": "파싱 실패: " + content}
    except Exception as e:
        return {"score": None, "reason": f"API 오류: {e}"}

def deduplicate_sentences(sentences):
    deduped = []
    prev = None
    for s in sentences:
        if s != prev:
            deduped.append(s)
        prev = s
    return deduped

def gpt_split_sentences(text: str) -> list:
    """
    GPT API를 사용해 입력 텍스트를 문장 단위로 분리하여 리스트로 반환
    """
    prompt = (
        "다음 한국어 텍스트를 문장 단위로 분리해서 각 문장을 한 줄씩 줄바꿈으로만 나열해줘. "
        "파이썬 리스트, 코드블록 없이, 그냥 문장만 한 줄씩 써줘. "
        "각 문장은 온점, 물음표, 느낌표 등으로 끝나야 해.\n"
        "텍스트:\n" + text
    )
    openai.api_key = os.getenv("OPENAI_API_KEY")
    try:
        response = openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1024,
        )
        content = response.choices[0].message.content.strip()
        # 줄바꿈으로만 분리, 불필요한 문자 제거 없이 문장만 리스트로 반환
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        return lines
    except Exception as e:
        print(f"[gpt_split_sentences] 오류: {e}", flush=True)
        return [text]


async def tag_chunks_async(project_name: str, subject: str, chunks: list, attendees_list: List[Dict[str, Any]] = None, agenda: str = None, meeting_date: str = None, db: Session = None, meeting_id: str = None) -> dict:
    print(f"[tag_chunks] 전달받은 subject: {subject}", flush=True)
    print(f"[tag_chunks] 전달받은 attendees_list: {attendees_list}", flush=True)
    print(f"[tag_chunks] 전달받은 agenda: {agenda}", flush=True)
    print(f"[tag_chunks] 전달받은 meeting_date: {meeting_date}", flush=True)
    print(f"[tag_chunks] 전달받은 chunks:", flush=True)
    chunk_sentences = []
    for idx, chunk in enumerate(chunks):
        print(f"  청크 {idx+1}: {chunk}", flush=True)
        sentences = gpt_split_sentences(chunk)
        if idx == 0:
            used_sentences = sentences
        else:
            used_sentences = sentences[2:] if len(sentences) > 2 else []
        print(f"    -> 분리된 문장(적용): {used_sentences}", flush=True)
        chunk_sentences.append(used_sentences)
    all_sentences = [sent for chunk in chunk_sentences for sent in chunk]
    print(f"[tag_chunks] 전체 문장 리스트 (합쳐진):", flush=True)
    for idx, sent in enumerate(all_sentences):
        print(f"  [{idx+1}] {sent}", flush=True)
    deduped_sentences = deduplicate_sentences(all_sentences)

    # 문장별 0~3단계 평가 (7개씩 비동기 병렬)
    sentence_scores = []
    batch_size = 7
    i = 0
    while i < len(all_sentences):
        tasks = []
        for j in range(i, min(i + batch_size, len(all_sentences))):
            prev_sent = all_sentences[j-1] if j > 0 else ""
            next_sent = all_sentences[j+1] if j < len(all_sentences)-1 else ""
            tasks.append(gpt_score_sentence_async(subject, prev_sent, all_sentences[j], next_sent))
        results = await asyncio.gather(*tasks)
        for k, score_result in enumerate(results):
            idx = i + k
            sentence_scores.append({
                "index": idx,
                "sentence": all_sentences[idx],
                "score": score_result.get("score"),
                "reason": score_result.get("reason")
            })
        i += batch_size

    print("[tag_chunks] 문장별 평가 결과:", flush=True)
    for s in sentence_scores:
        print(f"  [{s['index']+1}] 점수: {s['score']} / 이유: {s['reason']} / 문장: {s['sentence']}", flush=True)


    # lang_summary 호출
    summary_result = lang_summary(subject, chunks, sentence_scores, attendees_list, agenda, meeting_date) if attendees_list is not None else lang_summary(subject, chunks, sentence_scores, None, agenda, meeting_date)
    # print("[tagging.py] lang_summary result:", summary_result, flush=True) 
    # lang_feedback 호출
    feedback_result = feedback_agent(subject, chunks, sentence_scores, attendees_list, agenda, meeting_date) if attendees_list is not None else feedback_agent(subject, chunks, sentence_scores, None, agenda, meeting_date)
    # print("[tagging.py] lang_feedback result:", feedback_result, flush=True)
    # 할 일 추출 agent 호출
    todos_result = extract_todos(subject, chunks, attendees_list, sentence_scores, agenda, meeting_date)
    assigned_roles = todos_result.get("assigned_roles")
    
    # DB 저장 (db가 있을 때만)
    if db is not None:
        # print(f"[tagging.py] insert_summary_log 호출: summary_result={summary_result}", flush=True)
        await insert_summary_log(db, summary_result["summary"] if isinstance(summary_result, dict) and "summary" in summary_result else summary_result, meeting_id)
        # print(f"[tagging.py] insert_task_assign_log 호출: assigned_roles={assigned_roles}", flush=True)
        await insert_task_assign_log(db, assigned_roles or {}, meeting_id)
        # 피드백 유형 매핑 및 저장
        feedback_type_map = await get_feedback_type_map(db)
        if isinstance(feedback_result, dict):
            for feedbacktype_name, feedback_detail in feedback_result.items():
                feedbacktype_id = feedback_type_map.get(feedbacktype_name, '')
                if feedbacktype_id:
                    await insert_feedback_log(db, feedback_detail, feedbacktype_id, meeting_id)
                else:
                    print(f"Unknown feedbacktype_name: {feedbacktype_name}", flush=True)
        else:
            await insert_feedback_log(db, feedback_result, '', meeting_id)

    # # 프롬프트 로그 저장용 에이전트 유형 매핑 함수 및 insert 함수
    # def get_agent_type_map():
    #     return {
    #         '요약': 'summary',
    #         '검색': 'search',
    #         '문서': 'docs',  # 필요시 추가
    #     }

    # async def insert_prompt_log_with_mapping(db, meeting_id: str, agent_type_name: str, prompt_output: str, prompt_input_date, prompt_output_date):
    #     agent_type_map = get_agent_type_map()
    #     agent_type = agent_type_map.get(agent_type_name)
    #     if agent_type is None:
    #         raise ValueError(f"지원하지 않는 에이전트 유형: {agent_type_name}")
    #     return await insert_prompt_log(db, meeting_id, agent_type, prompt_output, prompt_input_date, prompt_output_date)

    # 프롬프트 로그 저장
    return {
        "project_name": project_name,
        "subject": subject,
        "attendees_list": attendees_list,
        "chunks": chunks,
        "chunk_sentences": chunk_sentences,
        "all_sentences": all_sentences,
        "deduped_sentences": deduped_sentences,
        "sentence_scores": sentence_scores,
        "summary": summary_result,      # <- 요약 agent 결과
        "feedback": feedback_result,    # <- 피드백 agent 결과
        "assigned_roles": assigned_roles,
        "agenda": agenda,
        "meeting_date": meeting_date
    } 