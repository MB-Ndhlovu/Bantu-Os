#!/usr/bin/env python3
"""Validate the daily Bantu-OS handoff chain and publish a freshness summary."""

from __future__ import annotations

import argparse
import re
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPORT_DIR = Path(__file__).resolve().parents[1] / "reports"
SUMMARY = REPORT_DIR / "00-SUMMARY.md"
LOCAL_TZ = ZoneInfo("Africa/Johannesburg")
REPORT_NAMES = {
    1: "01-systems-init-lead.md",
    2: "02-rust-shell-engineer.md",
    3: "03-ai-engine-lead.md",
    4: "04-memory-rag-engineer.md",
    5: "05-services-backend-engineer.md",
    6: "06-integrations-engineer.md",
    7: "07-devops-ci-build-engineer.md",
    8: "08-security-reviewer.md",
    9: "09-docs-community-lead.md",
}
DATE_RE = re.compile(r"(?:Run date|Audit date)\*?:?\*?\s*:?\s*(\d{4}-\d{2}-\d{2})")
BLOCKER_RE = re.compile(r"\bBLOCKER:\s*(YES|NO)\b", re.IGNORECASE)


def get_report_state(path: Path, expected: date) -> dict[str, str | bool]:
    if not path.exists():
        return {"name": path.name, "status": "MISSING", "fresh": False, "blocker": "UNKNOWN"}

    text = path.read_text(encoding="utf-8")
    dates = DATE_RE.findall(text)
    blocker = BLOCKER_RE.search(text)
    fresh = expected.isoformat() in dates
    blocker_value = blocker.group(1).upper() if blocker else "UNKNOWN"
    if not fresh:
        status = "STALE"
    elif blocker_value != "NO":
        status = f"BLOCKED ({blocker_value})"
    else:
        status = "PASS"
    return {"name": path.name, "status": status, "fresh": fresh, "blocker": blocker_value}


def render_summary(run_date: date, states: list[dict[str, str | bool]]) -> str:
    healthy = all(state["status"] == "PASS" for state in states)
    overall = "NO" if healthy else "YES"
    lines = [
        "# Bantu-OS — Maintainer Run Summary",
        "",
        f"**Audit date:** {run_date.isoformat()} (Africa/Johannesburg)",
        f"**Report-chain status:** {'HEALTHY' if healthy else 'STALE/BLOCKED'}",
        f"**REPORT BLOCKER: {overall}**",
        "",
        "The watchdog checks the nine sequential handoff reports. A report is healthy only when it contains today's SAST date and `BLOCKER: NO`.",
        "",
        "| Report | Status | Blocker field |",
        "|---|---|---|",
    ]
    for state in states:
        lines.append(f"| `{state['name']}` | {state['status']} | {state['blocker']} |")
    lines.extend(
        [
            "",
            "## Decision",
            "",
            (
                "All nine handoffs are fresh and unblocked. The daily chain completed successfully."
                if healthy
                else "The chain is not complete for today's date. Do not treat scheduled automation existence as proof of completion; refresh or rerun the missing stages."
            ),
            "",
            f"Generated at {datetime.now(LOCAL_TZ).isoformat(timespec='seconds')}.",
            "",
        ]
    )
    return "\n".join(lines)


def send_alert(message: str) -> None:
    print(f"ALERT_REQUIRED: {message}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Override the SAST date (YYYY-MM-DD), mainly for tests")
    parser.add_argument(
        "--allow-stale",
        action="store_true",
        help="Write the audit summary without failing the process when reports are stale",
    )
    args = parser.parse_args()
    run_date = date.fromisoformat(args.date) if args.date else datetime.now(LOCAL_TZ).date()
    states = [get_report_state(REPORT_DIR / name, run_date) for name in REPORT_NAMES.values()]
    SUMMARY.write_text(render_summary(run_date, states), encoding="utf-8")
    for state in states:
        print(f"{state['name']}: {state['status']}")
    healthy = all(state["status"] == "PASS" for state in states)
    if not healthy:
        send_alert(f"Bantu-OS report chain is stale or blocked for {run_date.isoformat()}; inspect reports/00-SUMMARY.md")
    return 0 if healthy or args.allow_stale else 1


if __name__ == "__main__":
    raise SystemExit(main())
