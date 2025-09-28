import re
from datetime import datetime
from typing import Optional, Dict, Any

AMOUNT_RE = re.compile(r"\$?\s*(?P<amount>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))")
DATE_RE = re.compile(r"(?P<date>\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})")


def parse_bill_text(text: str) -> Dict[str, Any]:
    """Simple heuristic parser for bills from text.

    Returns dict with amount, due_date (ISO) and vendor if found.
    """
    result: Dict[str, Any] = {"amount": None, "due_date": None, "vendor": None}

    # amount
    m = AMOUNT_RE.search(text)
    if m:
        amt = m.group("amount")
        # normalize commas and dots
        amt_norm = amt.replace(',', '')
        try:
            result["amount"] = float(amt_norm)
        except Exception:
            try:
                result["amount"] = float(amt.replace(',', '.'))
            except Exception:
                result["amount"] = amt

    # date
    d = DATE_RE.search(text)
    if d:
        ds = d.group("date")
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d/%m/%Y", "%d/%m/%y"):
            try:
                parsed = datetime.strptime(ds, fmt)
                result["due_date"] = parsed.date().isoformat()
                break
            except Exception:
                continue

    # vendor heuristic: look for 'From:' or 'Vendor:' or common patterns
    vendor = None
    for line in text.splitlines():
        low = line.lower()
        if 'vendor' in low or 'from:' in low or 'pay to' in low or 'biller' in low:
            # take text after colon if present
            parts = line.split(':', 1)
            vendor = parts[1].strip() if len(parts) > 1 else line.strip()
            break

    # fallback: take first non-empty line as vendor
    if not vendor:
        for line in text.splitlines():
            if line.strip():
                vendor = line.strip()
                break

    result["vendor"] = vendor
    return result
