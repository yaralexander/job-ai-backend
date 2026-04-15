import os
import json
from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

# загрузка .env
load_dotenv()

# клиент OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# FastAPI
app = FastAPI()

# модели
class Profile(BaseModel):
    skills: str
    experience: str
    goal: str

class JobRequest(BaseModel):
    profile: Profile
    job_description: str

# endpoint
@app.post("/analyze-job")
def analyze(req: JobRequest):

    prompt = f"""
Ты карьерный AI-ассистент.

Кандидат:
Навыки: {req.profile.skills}
Опыт: {req.profile.experience}
Цель: {req.profile.goal}

Вакансия:
{req.job_description}

Верни JSON:
{{
  "match_score": 0-100,
  "missing_skills": [],
  "strengths": [],
  "advice": ""
}}

Отвечай строго JSON без текста вне JSON.
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    result_text = response.output_text

# чистим markdown
    clean_text = result_text.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(clean_text)
    except Exception as e:
        print("JSON ERROR:", e)
        print("RAW:", result_text)
        parsed = result_text

    return parsed

# проверка ключа
@app.get("/check")
def check():
    return {"key_loaded": bool(os.getenv("OPENAI_API_KEY"))}