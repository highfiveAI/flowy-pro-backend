# import openai
import os
import asyncio
import re
import json
from app.services.lang_summary import lang_summary
from app.services.lang_feedback import feedback_agent
from app.services.lang_role import assign_roles
from app.services.lang_todo import extract_todos
from app.services.lang_previewmeeting import lang_previewmeeting
from typing import List, Dict, Any
from app.crud.crud_meeting import insert_summary_log, insert_task_assign_log, insert_feedback_log, get_feedback_type_map
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.notify_email_service import send_meeting_email
from openai import AsyncOpenAI
from app.services.calendar_service.calendar_crud import insert_calendar_from_task

openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
        print(f"[gpt_score_sentence_async] 오류: {e}", flush=True)
        return {"score": None, "reason": f"API 오류: {e}"}

def deduplicate_sentences(sentences):
    deduped = []
    prev = None
    for s in sentences:
        if s != prev:
            deduped.append(s)
        prev = s
    return deduped

async def gpt_split_sentences(text: str) -> list:
    """
    GPT API를 사용해 입력 텍스트를 문장 단위로 분리하여 리스트로 반환
    """
    prompt = (
        "다음 한국어 텍스트를 문장 단위로 분리해서 각 문장을 한 줄씩 줄바꿈으로만 나열해줘. "
        "파이썬 리스트, 코드블록 없이, 그냥 문장만 한 줄씩 써줘. "
        "각 문장은 온점, 물음표, 느낌표 등으로 끝나야 해.\n"
        "텍스트:\n" + text
    )
    try:
        response = await openai_client.chat.completions.create(
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

async def tag_chunks_async(project_name: str, subject: str, chunks: list, attendees_list: List[Dict[str, Any]] = None, agenda: str = None, meeting_date: str = None, db: AsyncSession = None, meeting_id: str = None, meeting_duration_minutes: float = None) -> dict:
    print(f"[tag_chunks] 전달받은 subject: {subject}", flush=True)
    print(f"[tag_chunks] 전달받은 attendees_list: {attendees_list}", flush=True)
    print(f"[tag_chunks] 전달받은 agenda: {agenda}", flush=True)
    print(f"[tag_chunks] 전달받은 meeting_date: {meeting_date}", flush=True)
    print(f"[tag_chunks] 전달받은 chunks: {chunks}", flush=True)
    chunk_sentences = []
    for idx, chunk in enumerate(chunks):
        print(f"  청크 {idx+1}: {chunk}", flush=True)
        try:
            sentences = await gpt_split_sentences(chunk)
            if idx == 0:
                used_sentences = sentences
            else:
                used_sentences = sentences[2:] if len(sentences) > 2 else []
            print(f"    -> 분리된 문장(적용): {used_sentences}", flush=True)
            chunk_sentences.append(used_sentences)
        except Exception as e:
            print(f"[tag_chunks] 문장 분리 오류: {e}", flush=True)
            chunk_sentences.append([chunk])

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
        try:
            results = await asyncio.gather(*tasks)
            for k, score_result in enumerate(results):
                idx = i + k
                sentence_scores.append({
                    "index": idx,
                    "sentence": all_sentences[idx],
                    "score": score_result.get("score"),
                    "reason": score_result.get("reason")
                })
        except Exception as e:
            print(f"[tag_chunks] 문장 평가 오류: {e}", flush=True)
        i += batch_size

    print("[tag_chunks] 문장별 평가 결과:", flush=True)
    for s in sentence_scores:
        print(f"  [{s['index']+1}] 점수: {s['score']} / 이유: {s['reason']} / 문장: {s['sentence']}", flush=True)

    try:
        # lang_summary 호출
        summary_result = await lang_summary(subject, chunks, sentence_scores, attendees_list, agenda, meeting_date) if attendees_list is not None else await lang_summary(subject, chunks, sentence_scores, None, agenda, meeting_date)
        
        # lang_previewmeeting 호출 (예정된 회의 추출)
        if db is not None and meeting_id is not None:
            try:
                print(f"[tagging.py] === 예정된 회의 처리 시작 ===", flush=True)
                print(f"[tagging.py] meeting_id: {meeting_id}", flush=True)
                
                # meeting_id로 project_id 조회
                from app.models.meeting import Meeting
                from sqlalchemy import select
                
                stmt = select(Meeting).where(Meeting.meeting_id == meeting_id)
                result = await db.execute(stmt)
                meeting_record = result.scalar_one_or_none()
                
                if meeting_record:
                    project_id = str(meeting_record.project_id)
                    print(f"[tagging.py] 조회된 project_id: {project_id}", flush=True)
                    
                    # lang_previewmeeting 호출
                    print(f"[tagging.py] lang_previewmeeting 호출 중...", flush=True)
                    preview_meeting_data = await lang_previewmeeting(
                        summary_data=summary_result.get("agent_output", {}) if isinstance(summary_result, dict) else {},
                        subject=subject,
                        attendees_list=attendees_list,
                        project_id=project_id,
                        meeting_date=meeting_date
                    )
                    
                    print(f"[tagging.py] lang_previewmeeting 결과: {preview_meeting_data}", flush=True)
                    
                    # 예정된 회의가 있으면 Meeting 테이블에 insert
                    if preview_meeting_data:
                        print(f"[tagging.py] === DB INSERT 시작 ===", flush=True)
                        
                        # meeting_id를 String으로 변환하여 parent_meeting_id에 저장
                        parent_meeting_id_str = str(meeting_id)
                        print(f"[tagging.py] 원본 meeting_id: {meeting_id} (type: {type(meeting_id)})", flush=True)
                        print(f"[tagging.py] parent_meeting_id로 저장할 값: {parent_meeting_id_str}", flush=True)
                        
                        new_meeting = Meeting(
                            project_id=preview_meeting_data["project_id"],
                            meeting_title=preview_meeting_data["meeting_title"],
                            meeting_date=preview_meeting_data["meeting_date"],
                            meeting_audio_path=preview_meeting_data["meeting_audio_path"],
                            parent_meeting_id=parent_meeting_id_str  # 원본회의 ID를 String으로 변환하여 저장
                        )
                        print(f"[tagging.py] 생성된 Meeting 객체:", flush=True)
                        print(f"  - project_id: {new_meeting.project_id}", flush=True)
                        print(f"  - meeting_title: {new_meeting.meeting_title}", flush=True)
                        print(f"  - meeting_date: {new_meeting.meeting_date}", flush=True)
                        print(f"  - meeting_audio_path: {new_meeting.meeting_audio_path}", flush=True)
                        print(f"  - parent_meeting_id: {new_meeting.parent_meeting_id}", flush=True)
                        
                        db.add(new_meeting)
                        await db.commit()
                        await db.refresh(new_meeting)
                        
                        print(f"[tagging.py] === Meeting INSERT 완료 ===", flush=True)
                        print(f"[tagging.py] 새로 생성된 meeting_id: {new_meeting.meeting_id}", flush=True)
                        
                        # MeetingUser 테이블에 참석자들 insert
                        if attendees_list:
                            print(f"[tagging.py] === MeetingUser INSERT 시작 ===", flush=True)
                            from app.models.meeting_user import MeetingUser
                            
                            # role_id 정의
                            HOST_ROLE_ID = "20ea65e2-d3b7-4adb-a8ce-9e67a2f21999"  # is_host True
                            MEMBER_ROLE_ID = "a55afc22-b4c1-48a4-9513-c66ff6ed3965"  # is_host False
                            
                            for attendee in attendees_list:
                                user_id = attendee.get('id')
                                is_host = attendee.get('is_host', False)
                                role_id = HOST_ROLE_ID if is_host else MEMBER_ROLE_ID
                                
                                print(f"[tagging.py] 참석자 추가: {attendee.get('name')} (user_id: {user_id}, is_host: {is_host})", flush=True)
                                
                                meeting_user = MeetingUser(
                                    user_id=user_id,
                                    meeting_id=new_meeting.meeting_id,
                                    role_id=role_id
                                )
                                db.add(meeting_user)
                            
                            await db.commit()
                            print(f"[tagging.py] === MeetingUser INSERT 완료 ===", flush=True)
                            print(f"[tagging.py] 총 {len(attendees_list)}명의 참석자 등록 완료", flush=True)
                        
                        print(f"[tagging.py] 예정된 회의 등록 완료: {preview_meeting_data['meeting_title']}", flush=True)
                    else:
                        print("[tagging.py] 예정된 회의 언급 없음", flush=True)
                else:
                    print(f"[tagging.py] project_id를 찾을 수 없음: meeting_id={meeting_id}", flush=True)
            except Exception as e:
                print(f"[tagging.py] 예정된 회의 처리 오류: {e}", flush=True)
        
        # lang_feedback 호출
        feedback_result = await feedback_agent(subject, chunks, sentence_scores, attendees_list, agenda, meeting_date, meeting_duration_minutes) if attendees_list is not None else await feedback_agent(subject, chunks, sentence_scores, None, agenda, meeting_date, meeting_duration_minutes)
        
        # 할 일 추출 agent 호출
        todos_result = await extract_todos(subject, chunks, attendees_list, sentence_scores, agenda, meeting_date)
        assigned_roles = todos_result.get("assigned_roles")
    except Exception as e:
        print(f"[tag_chunks] 에이전트 호출 오류: {e}", flush=True)
        summary_result = "에이전트 호출 중 오류가 발생했습니다."
        feedback_result = {"오류": "에이전트 호출 중 오류가 발생했습니다."}
        assigned_roles = {}
    
    # DB 저장 (db가 있을 때만)
    if db is not None:
        # print(f"[tagging.py] insert_summary_log 호출: summary_result={summary_result}", flush=True)
        await insert_summary_log(db, summary_result["summary"] if isinstance(summary_result, dict) and "summary" in summary_result else summary_result, meeting_id)
        
        # print(f"[tagging.py] insert_task_assign_log 호출: assigned_roles={assigned_roles}", flush=True)
        task_assign_log = await insert_task_assign_log(db, assigned_roles or {}, meeting_id)
        if hasattr(task_assign_log, '__dict__'):
            print(f"[tagging.py] insert_task_assign_log 결과: {task_assign_log.__dict__}", flush=True)
        else:
            print(f"[tagging.py] insert_task_assign_log 결과: {task_assign_log}", flush=True)
        print(f"[tagging.py] updated_task_assign_contents: {getattr(task_assign_log, 'updated_task_assign_contents', None)}", flush=True)
        
        # 캘린더 insert
        calendar_log = await insert_calendar_from_task(db, task_assign_log)
        print(f"[tagging.py] insert_calendar_from_task 결과: {calendar_log}", flush=True)

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
        # 모든 피드백 저장이 끝난 후 이메일 전송 (회의장에게만)
        host = None
        if attendees_list:
            for person in attendees_list:
                if person.get("is_host") == True:
                    host = {
                        "name": person.get("name"),
                        "email": person.get("email"),
                        "role": person.get("role", "host")
                    }
                    break
        if host is not None:
            meeting_info = {
                "info_n": [host],
                "dt": meeting_date,
                "subj": subject,
                "meeting_id": meeting_id
            }
            await send_meeting_email(meeting_info)
        else:
            print("회의장(Host) 정보가 없습니다.")

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
