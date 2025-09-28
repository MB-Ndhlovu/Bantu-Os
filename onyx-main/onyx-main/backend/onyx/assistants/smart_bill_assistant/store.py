from datetime import datetime, timedelta
from typing import Any, Dict, List

from onyx.key_value_store.factory import get_kv_store

KV_BILLS_PREFIX = "smart_bill_assistant:bills:"


def _user_key(user_id: str) -> str:
    return f"{KV_BILLS_PREFIX}{user_id}"


def save_bill(user_id: str, bill: Dict[str, Any]) -> None:
    store = get_kv_store()
    key = _user_key(user_id)
    try:
        existing = store.load(key) or []
    except Exception:
        existing = []
    # add metadata
    bill_copy = dict(bill)
    bill_copy.setdefault("created_at", datetime.utcnow().isoformat())
    bill_copy.setdefault("archived", False)
    existing.append(bill_copy)
    store.store(key, existing)


def list_bills(user_id: str, include_archived: bool = False) -> List[Dict[str, Any]]:
    store = get_kv_store()
    key = _user_key(user_id)
    try:
        bills = store.load(key) or []
    except Exception:
        bills = []
    if not include_archived:
        bills = [b for b in bills if not b.get("archived", False)]
    return bills


def archive_old_bills(user_id: str, months: int = 3) -> int:
    store = get_kv_store()
    key = _user_key(user_id)
    try:
        bills = store.load(key) or []
    except Exception:
        return 0
    cutoff = datetime.utcnow() - timedelta(days=30 * months)
    changed = False
    count = 0
    for b in bills:
        created = b.get("created_at")
        if created:
            try:
                created_dt = datetime.fromisoformat(created)
            except Exception:
                continue
            if created_dt < cutoff and not b.get("archived", False):
                b["archived"] = True
                changed = True
                count += 1
    if changed:
        store.store(key, bills)
    return count

