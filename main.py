from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from groq import Groq
import requests

from utils import search, crawl_task
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = Groq(api_key="")

# -----------------------------
# 🔐 DJANGO AUTH API
# -----------------------------

BASE_URL="http://204.168.204.160:8000/"

DJANGO_VERIFY = f"{BASE_URL}/verify-user/"
DJANGO_UPDATE_USAGE = f"{BASE_URL}/update-usage/"
DJANGO_GET_URLS = f"{BASE_URL}/get-urls/"


def get_user(api_key: str = None):
    if not api_key:
        raise HTTPException(status_code=401, detail="API key missing")

    try:
        res = requests.post(DJANGO_VERIFY, json={"api_key": api_key})
        data = res.json()

        if not data.get("status"):
            raise HTTPException(status_code=401, detail="Invalid or blocked user")

        return {
            "user_id": str(data["user_id"]),
            "limit": data["limit"],
            "used": data["used"],
            "api_key": api_key
        }

    except:
        raise HTTPException(status_code=500, detail="Auth server error")


# -----------------------------
# 📥 GET USER URLS FROM DJANGO
# -----------------------------
def get_user_urls(api_key):
    try:
        res = requests.get(DJANGO_GET_URLS, params={"api_key": api_key})
        data = res.json()

        if data["status"]:
            return [u["url"] for u in data["data"]]

        return []
    except:
        return []


# -----------------------------
# 🤖 ASK CHATBOT
# -----------------------------
# @app.get("/ask")
# def ask(q: str, api_key: str, user=Depends(get_user)):
#     user_id = user["user_id"]
#     print("api_key",api_key)
#     # 🔥 LIMIT CHECK
#     if user["used"] >= user["limit"]:
#         return {"answer": "Limit exceeded, please upgrade your plan"}

#     # 🔥 ensure URLs exist
#     urls = get_user_urls(api_key)

#     if not urls:
#         return {"answer": "No URLs found for this user"}

#     # 🔥 search from FAISS
#     print("user_id",user_id)
#     context = search(user_id, q)

#     if not context:
#         return {"answer": "No relevant data found"}

#     requests.post(
#             "http://127.0.0.1:8000/api/update-usage/",
#             json={"user_id": user_id}
#         )
    
#     prompt = f"""
#     - Answer ONLY from the given context
#     - Do NOT use outside knowledge
#     Context: {context}
#     Question: {q}
#     """

#     client = Groq(api_key=api_key)

#     chat = client.chat.completions.create(
#         model="llama-3.1-8b-instant",
#         messages=[{"role": "user", "content": prompt}]
#     )

#     answer = chat.choices[0].message.content

#     # 🔥 UPDATE USAGE IN DJANGO
#     requests.post(DJANGO_UPDATE_USAGE, json={
#         "api_key": api_key
#     })

#     return {"answer": answer}


@app.get("/ask")
def ask(q: str, vistor_id: str, api_key: str, user=Depends(get_user)):
    user_id = user["user_id"]

    # 🔥 LIMIT CHECK
    if user["used"] >= user["limit"]:
        return {"answer": "Limit exceeded, please upgrade your plan"}

    # 🔥 CHECK URL EXISTS
    urls = get_user_urls(api_key)
    if not urls:
        return {"answer": "No URLs found for this user"}

    print("USER:", user_id)
    print("QUESTION:", q)

    # 🔥 SEARCH (improved)
    context = search(user_id, q)

    print("CONTEXT LENGTH:", len(context))

    # ❌ agar bilkul empty hai
    if not context or len(context.strip()) < 20:
        return {"answer": "No relevant data found"}

    # 🔥 SMART PROMPT (बहुत important)
    prompt = f"""
You are a professional AI assistant.

Rules:
- Answer ONLY from the given context
- Do NOT use outside knowledge
- If exact answer not found, try to answer from closest matching content
- Do NOT say "No relevant data found" if some information exists
- Keep answer clear, structured, and professional
- Answer in same language as question (Hindi / Hinglish / English)

Context:
{context}

Question:
{q}

Answer:
"""

    # 🔥 LLM CALL
    client = Groq(api_key=api_key)

    chat = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3   # 🔥 more accurate
    )

    answer = chat.choices[0].message.content
    SALES_TRIGGER = 5
    show_sales_popup = False
    print("userd",user['used'])
    if user["used"] >= SALES_TRIGGER:
        show_sales_popup = True

    # 🔥 UPDATE USAGE (only once)
    try:
        requests.post(
            "http://127.0.0.1:8000/api/update-usage/",
            json={"user_id": user_id}
        )
    except:
        pass
    import uuid

    visitor_id = vistor_id

    if not visitor_id:
        visitor_id = str(uuid.uuid4())
        user["visitor_id"] = visitor_id   # temporary store
    try:
        requests.post(
            "http://127.0.0.1:8000/api/save-chat/",
            json={
                "bot_id": user_id,   # ya alag bot_id use karo agar hai
                "visitor_id": visitor_id,
                "question": q,
                "answer": answer,
                "source_urls": urls
            }
        )
    except Exception as e:
        print("Save chat error:", e)

    return {
        "answer": answer,
        "show_sales_popup": show_sales_popup,
        "sales_message": "Would you like us to connect you with our sales team?",
        "options": ["Yes", "No"]
    }

# -----------------------------
# 🕷️ CRAWL API (Django se call hota hai)
# -----------------------------
class CrawlRequest(BaseModel):
    user_id: str
    urls: list[str]


@app.post("/crawl")
def crawl_urls(data: CrawlRequest):
    for url in data.urls:
        crawl_task(data.user_id, url, 20)

    return {"message": "Crawling completed"}