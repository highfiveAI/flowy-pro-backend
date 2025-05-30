import re

def classify_text(text: str) -> str:
    """
    입력된 텍스트를 간단히 분류하는 함수. (예시: 긍정/부정/중립)
    띄어쓰기와 상관없이 키워드가 포함되어 있으면 분류
    """
    positive_keywords = ["좋다", "행복", "기쁘다", "감사"]
    negative_keywords = ["싫다", "나쁘다", "화난다", "짜증"]

    # 모든 공백 문자 제거
    normalized_text = re.sub(r"\s+", "", text)
    print(f"[DEBUG] normalized_text: {normalized_text}")
    print(f"[DEBUG] positive_keywords: {positive_keywords}")
    print(f"[DEBUG] negative_keywords: {negative_keywords}")

    if any(word in normalized_text for word in positive_keywords):
        print("[DEBUG] 분류 결과: 긍정")
        return "긍정"
    elif any(word in normalized_text for word in negative_keywords):
        print("[DEBUG] 분류 결과: 부정")
        return "부정"
    else:
        print("[DEBUG] 분류 결과: 중립")
        return "중립" 