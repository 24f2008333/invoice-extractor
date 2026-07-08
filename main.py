from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
import os
import json
import re

app = FastAPI(title="Invoice Extractor")

client = OpenAI(
    api_key=os.environ["AIPIPE_TOKEN"],
    base_url="https://aipipe.org/openrouter/v1"
)

class InvoiceRequest(BaseModel):
    text: str

class InvoiceResponse(BaseModel):
    vendor: str
    amount: float
    currency: str
    date: str


@app.post("/extract", response_model=InvoiceResponse)
def extract(req: InvoiceRequest):

    if not req.text or not req.text.strip():
        raise HTTPException(status_code=422, detail="Empty input")

    prompt = f"""
Extract the following invoice information.

Return ONLY valid JSON.

Schema:

{{
  "vendor":"",
  "amount":0,
  "currency":"USD",
  "date":"YYYY-MM-DD"
}}

Invoice Text:

{req.text}
"""

    try:
        response = client.chat.completions.create(
            model="openai/gpt-4.1-nano",
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        content = response.choices[0].message.content

        match = re.search(r"\{.*\}", content, re.DOTALL)

        if not match:
            raise Exception("No JSON returned")

        data = json.loads(match.group())

        return InvoiceResponse(
            vendor=str(data.get("vendor", "")),
            amount=float(data.get("amount", 0)),
            currency=str(data.get("currency", "")).upper(),
            date=str(data.get("date", ""))
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
