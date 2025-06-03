import openai
from app.core.config import settings

openai.api_key = settings.OPENAI_API_KEY

def ask_gpt(prompt: str) -> str:
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content