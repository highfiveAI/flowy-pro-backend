from app.api.mcp_utils import MCPContextManager
from app.models.tagging import tag_chunks_async

mcp_manager = MCPContextManager()

def create_user_context(user_id, initial_data=None):
    return mcp_manager.create_context(user_id, initial_data)

def update_user_context(user_id, data):
    return mcp_manager.update_context(user_id, data)

def get_user_context(user_id):
    return mcp_manager.get_context(user_id)

def extract_tagged_sentences(tag_chunks_result, subject):
    """tag_chunks_async 결과에서 sentence, score, reason, subject(회의주제)만 추출해서 리스트로 반환"""
    tagged_sentences = [
        {
            "sentence": s.get("sentence"),
            "score": s.get("score"),
            "reason": s.get("reason"),
            "subject": subject
        }
        for s in tag_chunks_result.get("sentence_scores", [])
    ]
    print(f"[extract_tagged_sentences] subject: {subject}")
    print(f"[extract_tagged_sentences] tagged_sentences: {tagged_sentences}")
    return tagged_sentences

# 예시: 전체 flow를 함수로 구현 (비동기)
async def process_tagging_and_summary(subject, chunks, summary_agent_executor):
    # 1️⃣ tag_chunks_async 호출 → 결과 받기
    tagging_result = await tag_chunks_async(subject, chunks)

    # 2️⃣ extract_tagged_sentences 명시적 호출
    sentence_scores = extract_tagged_sentences(tagging_result, subject)

    # 3️⃣ score별 문장 분류
    summary_sentences = [x["sentence"] for x in sentence_scores if x["score"] is not None and x["score"] >= 2]
    feedback_sentences = [x["sentence"] for x in sentence_scores if x["score"] in (0, 1)]
    role_sentences = [x["sentence"] for x in sentence_scores if x["score"] == 3]

    # 4️⃣ 준비된 데이터로 Agent 호출 (예시)
    summary_result = summary_agent_executor.invoke({"input": "\n".join(summary_sentences)})

    return {
        "subject": subject,
        "summary_sentences": summary_sentences,
        "feedback_sentences": feedback_sentences,
        "role_sentences": role_sentences,
        "summary_result": summary_result
    }