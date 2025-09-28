from fastapi import APIRouter, Body
from typing import Dict, Any
from onyx.utils.logger import setup_logger
from .parser import parse_bill_text
from .store import save_bill, list_bills, archive_old_bills

logger = setup_logger()
router = APIRouter(prefix="/smart-bills", tags=["smart-bills"])


@router.post("/parse-sample")
def parse_sample(user_id: str = Body(...), text: str = Body(...)) -> Dict[str, Any]:
    """Parse a piece of text (email or OCR'd PDF) and store the extracted bill in memory (sandbox)."""
    parsed = parse_bill_text(text)
    parsed["source"] = "sample"
    save_bill(user_id, parsed)
    return {"status": "ok", "parsed": parsed}


@router.get("/list")
def get_bills(user_id: str) -> Dict[str, Any]:
    # archive old bills on each listing to maintain the 3-month rule
    archived = archive_old_bills(user_id)
    bills = list_bills(user_id)
    # add urgency detection
    from datetime import date, datetime

    results = []
    for b in bills:
        due = b.get("due_date")
        urgency = "unknown"
        if due:
            try:
                due_dt = datetime.fromisoformat(due)
                days = (due_dt.date() - date.today()).days
                if days < 0:
                    urgency = "past_due"
                elif days <= 7:
                    urgency = "due_soon"
                else:
                    urgency = "ok"
            except Exception:
                urgency = "unknown"
        results.append({"bill": b, "urgency": urgency})

    return {"archived_pruned": archived, "bills": results}


@router.post("/action")
def action_on_bill(user_id: str = Body(...), bill_index: int = Body(...), action: str = Body(...), confirm: bool = Body(False)) -> Dict[str, Any]:
    """Sandbox-only actions: confirm-payment, set-reminder, archive.
    Requires confirm=True to actually execute (confirm-before-execute).
    """
    bills = list_bills(user_id, include_archived=True)
    if bill_index < 0 or bill_index >= len(bills):
        return {"status": "error", "message": "invalid bill index"}

    bill = bills[bill_index]
    # simulate actions
    if action == "confirm-payment":
        if not confirm:
            return {"status": "confirm_required", "message": "Please confirm payment execution."}
        # sandbox: mark paid
        bill["paid"] = True
        save_bill(user_id, bill)
        return {"status": "ok", "message": "Payment simulated (sandbox)", "bill": bill}

    if action == "set-reminder":
        if not confirm:
            # store a pending reminder decision
            bill.setdefault("reminders", [])
            bill["reminders"].append({"scheduled": "in 3 days", "pending": True})
            save_bill(user_id, bill)
            return {"status": "ok", "message": "Reminder scheduled (pending confirm)", "bill": bill}
        else:
            # confirm the reminder
            for r in bill.get("reminders", []):
                r["pending"] = False
            save_bill(user_id, bill)
            return {"status": "ok", "message": "Reminder confirmed", "bill": bill}

    if action == "archive":
        bill["archived"] = True
        save_bill(user_id, bill)
        return {"status": "ok", "message": "Archived (sandbox)", "bill": bill}

    return {"status": "error", "message": "unknown action"}
