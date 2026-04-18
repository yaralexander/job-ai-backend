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

    for link in soup.find_all("a", href=True):
        href = link["href"]

        # фильтр — только вакансии
        if "/tyopaikat/tyo/" not in href:
            continue

        title = link.text.strip()

        if len(title) < 10:
            continue

        if "Lisää" in title:
            continue

        full_link = "https://duunitori.fi" + href

        try:
            job_page = requests.get(full_link, headers={
                "User-Agent": "Mozilla/5.0"
            })

            job_soup = BeautifulSoup(job_page.text, "html.parser")

            desc_block = job_soup.find("main")

            if desc_block:
                description = desc_block.get_text().strip()[:1000]
            else:
                description = ""

        except Exception as e:
            print("ERROR:", e)
            description = ""

        jobs.append({
            "title": title,
            "link": full_link,
            "description": description
        })

    return jobs


def get_job_description(url):
    try:
        res = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0"
        })

        soup = BeautifulSoup(res.text, "html.parser")

        desc = soup.select_one(".jobad-content, .job-description, .vacancy-description")

        if desc:
            return desc.text.strip()[:1000]

    except Exception as e:
        print("DESC ERROR:", e)

    return ""


def get_all_jobs():
    return get_jobs_from_duunitori()


def clean_html(raw):
    clean = re.sub('<.*?>', '', raw)
    clean = clean.replace("&nbsp;", " ")
    clean = clean.replace("\n", " ")
    return clean.strip()


from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Profile(BaseModel):
    skills: str
    experience: str
    goal: str


class JobRequest(BaseModel):
    profile: Profile
    job_description: str


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

    clean_text = result_text.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(clean_text)
    except Exception as e:
        print("JSON ERROR:", e)
        print("RAW:", result_text)
        parsed = result_text

    return parsed


@app.get("/check")
def check():
    return {"key_loaded": bool(os.getenv("OPENAI_API_KEY"))}


@app.get("/jobs")
def jobs():
    return get_jobs_from_duunitori()