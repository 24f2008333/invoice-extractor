from fastapi import FastAPI
from pydantic import BaseModel
import re

app = FastAPI(title="Invoice Extractor")


class InvoiceRequest(BaseModel):
    text: str


class InvoiceResponse(BaseModel):
    vendor: str
    amount: float
    currency: str
    date: str


@app.get("/")
def root():
    return {"status": "running"}


@app.post("/extract", response_model=InvoiceResponse)
def extract(req: InvoiceRequest):

    text = req.text or ""

    vendor = ""
    amount = 0.0
    currency = ""
    date = ""

    # Vendor
    vendor_patterns = [
        r"Vendor\s*[:\-]\s*(.+)",
        r"Supplier\s*[:\-]\s*(.+)",
        r"From\s*[:\-]\s*(.+)",
    ]

    for p in vendor_patterns:
        m = re.search(p, text, re.I)
        if m:
            vendor = m.group(1).split("\n")[0].strip()
            break

    if not vendor:
        for line in text.splitlines():
            line = line.strip()
            if line:
                vendor = line
                break

    # Currency
    m = re.search(r"\b(USD|EUR|GBP)\b", text, re.I)
    if m:
        currency = m.group(1).upper()

    # Amount
    patterns = [
        r"Total Due.*?(\d+(?:\.\d+)?)",
        r"Amount Due.*?(\d+(?:\.\d+)?)",
        r"Total.*?(\d+(?:\.\d+)?)",
        r"(?:USD|EUR|GBP)\s*(\d+(?:\.\d+)?)",
    ]

    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            amount = float(m.group(1))
            break

    # Date
    m = re.search(r"(2026-\d{2}-\d{2})", text)
    if m:
        date = m.group(1)

    return InvoiceResponse(
        vendor=vendor,
        amount=amount,
        currency=currency,
        date=date,
    )
