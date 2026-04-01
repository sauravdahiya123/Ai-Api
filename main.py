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

BASE_URL="https://aibot.borgdesk.com"

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


# @app.get("/ask")
# def ask(q: str, vistor_id: str, api_key: str, user=Depends(get_user)):
#     user_id = user["user_id"]

#     # 🔥 LIMIT CHECK
#     if user["used"] >= user["limit"]:
#         return {"answer": "Limit exceeded, please upgrade your plan"}

#     # 🔥 CHECK URL EXISTS
#     urls = get_user_urls(api_key)
#     if not urls:
#         return {"answer": "No URLs found for this user"}

#     print("USER:", user_id)
#     print("QUESTION:", q)

#     # 🔥 SEARCH (improved)
#     context = search(user_id, q)

#     print("CONTEXT LENGTH:", len(context))

#     # ❌ agar bilkul empty hai
#     if not context or len(context.strip()) < 20:
#         return {"answer": "No relevant data found"}

#     # 🔥 SMART PROMPT (बहुत important)
#     prompt = f"""
# You are a professional AI assistant.

# Rules:
# - Answer ONLY from the given context
# - Do NOT use outside knowledge
# - If exact answer not found, try to answer from closest matching content
# - Do NOT say "No relevant data found" if some information exists
# - Keep answer clear, structured, and professional
# - Answer in same language as question (Hindi / Hinglish / English)

# Context:
# {context}

# Question:
# {q}

# Answer:
# """

#     # 🔥 LLM CALL
#     client = Groq(api_key=api_key)

#     chat = client.chat.completions.create(
#         model="llama-3.1-8b-instant",
#         messages=[{"role": "user", "content": prompt}],
#         temperature=0.3   # 🔥 more accurate
#     )

#     answer = chat.choices[0].message.content
#     SALES_TRIGGER = 5
#     show_sales_popup = False
#     print("userd",user['used'])
#     if user["used"] >= SALES_TRIGGER:
#         show_sales_popup = True

#     # 🔥 UPDATE USAGE (only once)
#     try:
#         requests.post(
#             "http://127.0.0.1:8000/api/update-usage/",
#             json={"user_id": user_id}
#         )
#     except:
#         pass
#     import uuid

#     visitor_id = vistor_id

#     if not visitor_id:
#         visitor_id = str(uuid.uuid4())
#         user["visitor_id"] = visitor_id   # temporary store
#     try:
#         requests.post(
#             "http://127.0.0.1:8000/api/save-chat/",
#             json={
#                 "bot_id": user_id,   # ya alag bot_id use karo agar hai
#                 "visitor_id": visitor_id,
#                 "question": q,
#                 "answer": answer,
#                 "source_urls": urls
#             }
#         )
#     except Exception as e:
#         print("Save chat error:", e)

#     return {
#         "answer": answer,
#         "show_sales_popup": show_sales_popup,
#         "sales_message": "Would you like us to connect you with our sales team?",
#         "options": ["Yes", "No"]
#     }




@app.get("/ask")
def ask(q: str, vistor_id: str, api_key: str, user=Depends(get_user)):
    import requests
    import uuid
    from groq import Groq

    user_id = user["user_id"]

    # ============================================
    # 🔥 LIMIT CHECK
    # ============================================
    if user["used"] >= user["limit"]:
        return {"answer": "Limit exceeded, please upgrade your plan"}

    # ============================================
    # 🔥 GET USER URLS
    # ============================================
    urls = get_user_urls(api_key)
    if not urls:
        return {"answer": "No URLs found for this user"}

    print("QUESTION:", q)

    # ============================================
    # 🔥 STEP 1: FETCH SAVED Q&A FROM DJANGO API
    # ============================================
    saved_answers = ""

    try:
        res = requests.get(
            "https://aibot.borgdesk.com/api/get-qa/",
            params={"user_id": user_id, "question": q}
        )

        data = res.json()

        if data.get("results"):
            for qa in data["results"][:3]:  # 🔥 Top 3
                saved_answers += f"Q: {qa['question']}\nA: {qa['answer']}\n\n"

    except Exception as e:
        print("QA API error:", e)

    # ============================================
    # 🔥 STEP 2: WEBSITE CONTEXT (FAISS)
    # ============================================
    context = search(user_id, q)

    print("DB:", bool(saved_answers))
    print("WEB:", len(context) if context else 0)

    # ============================================
    # ❌ BOTH EMPTY CHECK
    # ============================================
    if not saved_answers and (not context or len(context.strip()) < 20):
        return {"answer": "No relevant data found"}

    # ============================================
    # 🔥 STEP 3: HYBRID PROMPT
    # ============================================
    
    


    prompt = f"""
You are a professional AI assistant.

Rules:
- Answer ONLY from the given context
- Do NOT use outside knowledge
- If exact answer not found, try to answer from closest matching content
- Do NOT say "No relevant data found" if some information exists
- Keep answer clear, structured, and professional

- Always prioritize the saved information as the main answer
- Use website context to enhance, expand, or explain the saved information
- Combine both sources naturally into one final answer

- Do NOT repeat raw data, rewrite it in a clean and professional format
- Improve clarity, structure, and readability
- Keep answer short, clear, and user-friendly
- Do NOT give unnecessary long explanations

- If extra details are available in context, include them smartly
- If context has no useful data, still format and improve the saved answer

- Answer in same language as question (Hindi / Hinglish / English)

Saved Info:
{saved_answers}

Context:
{context}

Question:
{q}

Answer:
"""

    # ============================================
    # 🔥 LLM CALL
    # ============================================
    client = Groq(api_key=api_key)

    chat = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5
    )

    final_answer = chat.choices[0].message.content.strip()

    # ============================================
    # 🔥 SALES POPUP LOGIC
    # ============================================
    SALES_TRIGGER = 5
    show_sales_popup = user["used"] >= SALES_TRIGGER

    # ============================================
    # 🔥 UPDATE USAGE
    # ============================================
    try:
        requests.post(
            "https://aibot.borgdesk.com/api/update-usage/",
            json={"user_id": user_id}
        )
    except:
        pass

    # ============================================
    # 🔥 VISITOR ID
    # ============================================
    visitor_id = vistor_id or str(uuid.uuid4())

    # ============================================
    # 🔥 SAVE CHAT
    # ============================================
    try:
        requests.post(
            "https://aibot.borgdesk.com/api/save-chat/",
            json={
                "bot_id": user_id,
                "visitor_id": visitor_id,
                "question": q,
                "answer": final_answer,
                "source": "hybrid"
            }
        )
    except Exception as e:
        print("Save chat error:", e)

    # ============================================
    # 🔥 RESPONSE
    # ============================================
    return {
        "answer": final_answer,
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
        crawl_task(data.user_id, url, 30)

    return {"message": "Crawling completed"}