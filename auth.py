from fastapi import Header, HTTPException
from db import users_col

import requests
from fastapi import Header, HTTPException

DJANGO_API = "http://127.0.0.1:8000/verify-user/"

def get_user(api_key: str = Header(None)):
    if not api_key:
        raise HTTPException(status_code=401, detail="API key missing")

    try:
        res = requests.post(DJANGO_API, json={"api_key": api_key})
        data = res.json()

        if not data.get("status"):
            raise HTTPException(status_code=401, detail="Invalid or blocked user")

        return data

    except:
        raise HTTPException(status_code=500, detail="Auth server error")