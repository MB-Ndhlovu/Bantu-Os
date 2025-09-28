"""
SchedulingAgent - SQLite-backed simple scheduler.

Stores events in events.db under settings.DATA_DIR.
Provides add_event, list_events, remove_event and simple time parsing
(e.g., "tomorrow at 8AM", "in 30 minutes", "2025-10-01 14:00").
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

from bantu_os.config import settings


EVENTS_DB = settings.DATA_DIR / "events.db"


def _ensure_db(path: Path) -> None:
    settings.ensure_dirs_exist()
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                when_ts TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


@dataclass
class Event:
    id: int
    title: str
    when_ts: str  # ISO format local timestamp

    def when_datetime(self) -> datetime:
        return datetime.fromisoformat(self.when_ts)


class SchedulingAgent:
    """Simple SQLite-backed scheduler."""

    def __init__(self, db_path: Path = EVENTS_DB) -> None:
        self.db_path = db_path
        _ensure_db(self.db_path)

    # -------------------- Public API --------------------
    def add_event(self, title: str, when_str: str, now: Optional[datetime] = None) -> int:
        when_dt = parse_natural_time(when_str, now=now)
        if when_dt is None:
            raise ValueError(f"Could not parse time from: {when_str}")
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO events(title, when_ts) VALUES (?, ?)",
                (title, when_dt.isoformat(timespec="minutes")),
            )
            conn.commit()
            return int(cur.lastrowid)

    def list_events(self) -> List[Event]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT id, title, when_ts FROM events ORDER BY when_ts ASC")
            out: List[Event] = []
            for row in cur.fetchall():
                out.append(Event(id=row[0], title=row[1], when_ts=row[2]))
            return out

    def remove_event(self, event_id: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
            conn.commit()
            return cur.rowcount > 0


# -------------------- Simple natural time parsing --------------------
AMPM = re.compile(r"\b(?P<hour>1[0-2]|0?[1-9])\s*(?P<ampm>am|pm)\b", re.IGNORECASE)
HHMM = re.compile(r"\b(?P<hour>\d{1,2}):(?(?=\d{2})\d{2})\b")
IN_X = re.compile(r"\bin\s+(?P<num>\d+)\s+(?P<unit>minute|minutes|hour|hours)\b", re.IGNORECASE)
DATE_TIME = re.compile(r"\b(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<time>\d{1,2}:\d{2})\b")


def _apply_ampm(hour: int, ampm: str) -> int:
    ampm = ampm.lower()
    if ampm == "am":
        return 0 if hour == 12 else hour
    # pm
    return hour if hour == 12 else hour + 12


def parse_natural_time(text: str, now: Optional[datetime] = None) -> Optional[datetime]:
    """Parse a small subset of natural language times. Returns local datetime.

    Supported examples:
    - "tomorrow at 8AM"
    - "today at 14:00" or "at 14:00"
    - "in 30 minutes", "in 2 hours"
    - "2025-10-01 14:00"
    - "8:00" or "8AM" (today, next future occurrence)
    """
    text = text.strip()
    now = now or datetime.now()

    # Absolute date time: YYYY-MM-DD HH:MM
    m = DATE_TIME.search(text)
    if m:
        try:
            dt = datetime.fromisoformat(f"{m.group('date')} {m.group('time')}")
            return dt
        except Exception:
            pass

    # in X minutes/hours
    m = IN_X.search(text)
    if m:
        num = int(m.group("num"))
        unit = m.group("unit").lower()
        delta = timedelta(minutes=num) if unit.startswith("minute") else timedelta(hours=num)
        return now + delta

    lower = text.lower()

    # tomorrow at HH(:MM|AM/PM)?
    if "tomorrow" in lower:
        base = (now + timedelta(days=1)).replace(second=0, microsecond=0)
        # am/pm pattern
        m = AMPM.search(lower)
        if m:
            hour_24 = _apply_ampm(int(m.group("hour")), m.group("ampm"))
            return base.replace(hour=hour_24, minute=0)
        # HH:MM
        m = HHMM.search(lower)
        if m:
            h, mi = m.group(0).split(":")
            return base.replace(hour=int(h), minute=int(mi))
        # default 09:00
        return base.replace(hour=9, minute=0)

    # today at HH(:MM|AM/PM)? or "at HH:MM"
    if "today" in lower or lower.startswith("at ") or " at " in lower:
        base = now.replace(second=0, microsecond=0)
        m = AMPM.search(lower)
        if m:
            hour_24 = _apply_ampm(int(m.group("hour")), m.group("ampm"))
            dt = base.replace(hour=hour_24, minute=0)
            return dt if dt > now else dt + timedelta(days=1)
        m = HHMM.search(lower)
        if m:
            h, mi = m.group(0).split(":")
            dt = base.replace(hour=int(h), minute=int(mi))
            return dt if dt > now else dt + timedelta(days=1)

    # bare HH:MM or 8AM
    m = AMPM.search(lower)
    if m:
        hour_24 = _apply_ampm(int(m.group("hour")), m.group("ampm"))
        dt = now.replace(hour=hour_24, minute=0, second=0, microsecond=0)
        return dt if dt > now else dt + timedelta(days=1)
    m = HHMM.search(lower)
    if m:
        h, mi = m.group(0).split(":")
        dt = now.replace(hour=int(h), minute=int(mi), second=0, microsecond=0)
        return dt if dt > now else dt + timedelta(days=1)

    return None
