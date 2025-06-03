import openai
import os
import json
from typing import List, Dict, Any

openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_todos(subject: str, chunks: List[str], sentence_scores: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    회의 내용에서 할 일을 추출하는 함수
    
    Args:
        subject (str): 회의 주제
        chunks (List[str]): 회의 내용 청크 리스트
        sentence_scores (List[Dict[str, Any]]): 문장별 점수와 평가 정보
        
    Returns:
        Dict[str, Any]: 추출된 할 일 목록과 관련 정보
    """
    # 점수가 2 이상인 문장들만 필터링 (관련성 높은 문장들)
    relevant_sentences = [
        score["sentence"] for score in sentence_scores 
        if score["score"] is not None and score["score"] >= 2
    ]
    
    # 할 일 추출을 위한 프롬프트 작성
    prompt = f"""회의 주제: "{subject}"

다음 문장들에서 할 일을 추출해주세요. 각 할 일은 다음 형식으로 정리해주세요:
1. 구체적인 행동
2. 담당자 (명시된 경우)
3. 기한 (명시된 경우)
4. 우선순위 (높음/중간/낮음)

문장들:
{chr(10).join(relevant_sentences)}

아래와 같은 JSON 형식으로만 답변해주세요:
{{
    "todos": [
        {{
            "action": "구체적인 할 일",
            "assignee": "담당자 (없으면 null)",
            "deadline": "기한 (없으면 null)",
            "priority": "높음/중간/낮음",
            "context": "관련 문장"
        }}
    ],
    "summary": "전체 할 일에 대한 간단한 요약"
}}
"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1024,
        )
        
        content = response.choices[0].message.content.strip()
        result = json.loads(content)
        
        return {
            "todos": result["todos"],
            "summary": result["summary"],
            "total_count": len(result["todos"])
        }
        
    except Exception as e:
        print(f"[extract_todos] 오류: {e}", flush=True)
        return {
            "todos": [],
            "summary": "할 일 추출 중 오류가 발생했습니다.",
            "total_count": 0,
            "error": str(e)
        } 