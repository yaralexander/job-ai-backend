
import feedparser
import os
import json
import re

import requests
from bs4 import BeautifulSoup

def get_jobs_from_duunitori():
    url = "https://duunitori.fi/tyopaikat?haku=developer"

    response = requests.get(url, headers={
        "User-Agent": "Mozilla/5.0"
    })

    soup = BeautifulSoup(response.text, "html.parser")

    jobs = []

    for job in soup.select(".job-box__hover"):
        link = job.get("href")

        title_el = job.select_one(".job-box__title")
        company_el = job.select_one(".job-box__company")

        if not link or not title_el:
            continue

        title = title_el.text.strip()

        jobs.append({
            "title": title,
            "link": "https://duunitori.fi" + link,
            "description": company_el.text.strip() if company_el else ""
        })

    return jobs

def get_job_description(url):
    try:
        res = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0"
        })

        soup = BeautifulSoup(res.text, "html.parser")

        # ищем основной блок текста
        desc = soup.select_one(".jobad-content, .job-description, .vacancy-description")

        if desc:
            return desc.text.strip()[:1000]

    except Exception as e:
        print("DESC ERROR:", e)

    return ""

def get_all_jobs():
    return get_jobs_from_duunitori()

def clean_html(raw):
    clean = re.sub('<.*?>', '', raw)        # убираем HTML
    clean = clean.replace("&nbsp;", " ")    # убираем мусор
    clean = clean.replace("\n", " ")        # убираем переносы
    return clean.strip()

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

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

def get_jobs_from_rss():
    import requests

    url = "https://weworkremotely.com/categories/remote-programming-jobs.rss"

    response = requests.get(url, headers={
        "User-Agent": "Mozilla/5.0"
    })

    feed = feedparser.parse(response.text)

    print("ENTRIES:", len(feed.entries))  # ← ОДИН НОРМАЛЬНЫЙ PRINT

    jobs = []

    for entry in feed.entries:
        jobs.append({
            "title": entry.title,
            "link": entry.link,
            "description": clean_html(entry.summary)[:300]
        })

    return jobs

# проверка ключа
@app.get("/check")
def check():
    return {"key_loaded": bool(os.getenv("OPENAI_API_KEY"))}

@app.get("/jobs")
def jobs():
    return get_jobs_from_duunitori()
