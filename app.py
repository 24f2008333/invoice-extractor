from fastapi import FastAPI
from pydantic import BaseModel
import requests
import json
import re
from datetime import datetime

app = FastAPI(title="Invoice Extractor")


class InvoiceRequest(BaseModel):
    text: str


class InvoiceResponse(BaseModel):
    vendor: str
    amount: float
    currency: str
    date: str


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2"


def normalize_date(date_str):
    try:
        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except:
        pass

    patterns = [
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%d %B %Y",
        "%B %d %Y"
    ]

    for p in patterns:
        try:
            dt = datetime.strptime(date_str.strip(), p)
            return dt.strftime("%Y-%m-%d")
        except:
            continue

    m = re.search(r"\d{4}-\d{2}-\d{2}", date_str)
    if m:
        return m.group()

    return ""


@app.post("/extract", response_model=InvoiceResponse)
def extract(req: InvoiceRequest):

    if not req.text.strip():
        return InvoiceResponse(
            vendor="",
            amount=0,
            currency="USD",
            date=""
        )

    prompt = f"""
Extract invoice information.

Return ONLY valid JSON.

Example:

{{
"vendor":"Acme Ltd",
"amount":123.45,
"currency":"USD",
"date":"2026-04-18"
}}

Invoice:

{req.text}
"""

    r = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        },
        timeout=60
    )

    text = r.json()["response"]

    m = re.search(r"\{.*\}", text, re.S)

    if m:
        data = json.loads(m.group())
    else:
        data = {}

    vendor = str(data.get("vendor", ""))

    amount = float(data.get("amount", 0))

    currency = str(data.get("currency", "USD")).upper()

    date = normalize_date(str(data.get("date", "")))

    return InvoiceResponse(
        vendor=vendor,
        amount=amount,
        currency=currency,
        date=date
    )