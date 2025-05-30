from app.api.openai_gpt import ask_gpt

def get_gpt_response(prompt: str) -> str:
    return ask_gpt(prompt)