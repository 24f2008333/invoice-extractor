from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
import os
import json
import re

app = FastAPI()

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

class InvoiceRequest(BaseModel):
    text: str

class InvoiceResponse(BaseModel):
    vendor: str
    amount: float
    currency: str
    date: str

@app.post("/extract", response_model=InvoiceResponse)
def extract(req: InvoiceRequest):

    if not req.text.strip():
        raise HTTPException(status_code=422, detail="Empty text")

    prompt = f"""
Extract the invoice fields.

Return ONLY JSON.

Schema:

{{
"vendor":"",
"amount":0,
"currency":"USD",
"date":"YYYY-MM-DD"
}}

Invoice:

{req.text}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role":"user",
                "content":prompt
            }
        ],
        temperature=0
    )

    content = response.choices[0].message.content

    match = re.search(r"\{.*\}", content, re.S)

    if not match:
        raise HTTPException(status_code=500, detail="Invalid model output")

    data = json.loads(match.group())

    return InvoiceResponse(
        vendor=data["vendor"],
        amount=float(data["amount"]),
        currency=data["currency"].upper(),
        date=data["date"]
    )
