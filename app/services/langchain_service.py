from app.api.langchain_utils import get_langchain_llm

def run_langchain(prompt: str) -> str:
    llm = get_langchain_llm()
    try:
        result = llm.invoke(prompt)
        return result.content
    except Exception as e:
        return f"LangChain 오류: {str(e)}"