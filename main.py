from fastapi import FastAPI
from pydantic import BaseModel
import re
import json
from datetime import datetime

app = FastAPI()


class InvoiceRequest(BaseModel):
    text: str


class InvoiceResponse(BaseModel):
    vendor: str
    amount: float
    currency: str
    date: str


# Try to use Ollama if installed
try:
    import ollama

    OLLAMA_AVAILABLE = True
except Exception:
    OLLAMA_AVAILABLE = False


def regex_extract(text: str):
    vendor = ""

    vendor_patterns = [
        r"Vendor[:\-]\s*(.+)",
        r"From[:\-]\s*(.+)",
        r"Supplier[:\-]\s*(.+)",
    ]

    for p in vendor_patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            vendor = m.group(1).split("\n")[0].strip()
            break

    if vendor == "":
        lines = [x.strip() for x in text.splitlines() if x.strip()]
        if lines:
            vendor = lines[0]

    currency = ""

    m = re.search(r"\b(USD|EUR|GBP)\b", text, re.I)
    if m:
        currency = m.group(1).upper()

    amount = 0.0

    patterns = [
        r"Total Due[:\s]*([A-Z]{3})?\s*\$?([\d,]+\.\d+)",
        r"Amount Due[:\s]*([A-Z]{3})?\s*\$?([\d,]+\.\d+)",
        r"Total[:\s]*([A-Z]{3})?\s*\$?([\d,]+\.\d+)",
        r"\b(USD|EUR|GBP)\s*([\d,]+\.\d+)",
    ]

    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            amount = float(m.group(len(m.groups())).replace(",", ""))
            break

    if amount == 0:
        nums = re.findall(r"\d+\.\d+", text)
        if nums:
            amount = float(nums[-1])

    date = ""

    m = re.search(r"(2026-\d{2}-\d{2})", text)
    if m:
        date = m.group(1)

    return {
        "vendor": vendor,
        "amount": amount,
        "currency": currency,
        "date": date,
    }


def llm_extract(text: str):

    prompt = f"""
Extract invoice information.

Return ONLY valid JSON.

Schema:

{{
"vendor":"",
"amount":0,
"currency":"",
"date":"YYYY-MM-DD"
}}

Invoice:

{text}
"""

    response = ollama.chat(
        model="llama3.2",
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    content = response["message"]["content"]

    first = content.find("{")
    last = content.rfind("}")

    content = content[first:last + 1]

    return json.loads(content)


@app.post("/extract", response_model=InvoiceResponse)
def extract(req: InvoiceRequest):

    text = req.text.strip()

    if not text:
        return InvoiceResponse(
            vendor="",
            amount=0,
            currency="",
            date="",
        )

    if OLLAMA_AVAILABLE:
        try:
            result = llm_extract(text)
            return InvoiceResponse(**result)
        except Exception:
            pass

    result = regex_extract(text)

    return InvoiceResponse(**result)