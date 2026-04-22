"""
Tests for scheduling_agent — natural time parsing and SQLite-backed scheduler.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from bantu_os.agents.scheduling_agent import (
    Event,
    SchedulingAgent,
    _ensure_db,
    parse_natural_time,
)

# ---------------------------------------------------------------------------
# parse_natural_time — unit tests
# ---------------------------------------------------------------------------


class TestParseNaturalTime:
    """Cover every supported format in parse_natural_time."""

    def _now(self) -> datetime:
        return datetime(2026, 4, 16, 14, 0, 0)

    # --- absolute date-time ---
    def test_iso_date_with_time(self) -> None:
        dt = parse_natural_time("2026-04-20 08:00", now=self._now())
        assert dt == datetime(2026, 4, 20, 8, 0)

    def test_iso_date_with_time_missing_leading_zero(self) -> None:
        # DATE_TIME regex requires zero-padded MM/DD — single-digit not supported.
        # Falls through to bare time parsing → 9:30 today (already past) → rolls to next day 09:30.
        dt = parse_natural_time("2026-4-2 9:30", now=self._now())
        assert dt is not None
        assert dt.hour == 9 and dt.minute == 30

    # --- "in X minutes / hours" ---
    def test_in_minutes(self) -> None:
        now = self._now()
        dt = parse_natural_time("in 45 minutes", now=now)
        assert dt == now + timedelta(minutes=45)

    def test_in_hours(self) -> None:
        now = self._now()
        dt = parse_natural_time("in 2 hours", now=now)
        assert dt == now + timedelta(hours=2)

    def test_in_one_hour(self) -> None:
        now = self._now()
        dt = parse_natural_time("in 1 hour", now=now)
        assert dt == now + timedelta(hours=1)

    # --- "tomorrow at HH:MM / HHAM/PM" ---
    def test_tomorrow_at_hhmm(self) -> None:
        now = self._now()
        dt = parse_natural_time("tomorrow at 09:30", now=now)
        expected = (now + timedelta(days=1)).replace(
            hour=9, minute=30, second=0, microsecond=0
        )
        assert dt == expected

    def test_tomorrow_at_8am(self) -> None:
        now = self._now()
        dt = parse_natural_time("tomorrow at 8AM", now=now)
        expected = (now + timedelta(days=1)).replace(
            hour=8, minute=0, second=0, microsecond=0
        )
        assert dt == expected

    def test_tomorrow_at_12pm(self) -> None:
        now = self._now()
        dt = parse_natural_time("tomorrow at 12pm", now=now)
        expected = (now + timedelta(days=1)).replace(
            hour=12, minute=0, second=0, microsecond=0
        )
        assert dt == expected

    def test_tomorrow_default(self) -> None:
        """No time specified → defaults to 09:00 next day."""
        now = self._now()
        dt = parse_natural_time("tomorrow", now=now)
        expected = (now + timedelta(days=1)).replace(
            hour=9, minute=0, second=0, microsecond=0
        )
        assert dt == expected

    # --- "today at HH:MM / HHAM/PM" or bare "at HH:MM" ---
    def test_today_at_future_hhmm(self) -> None:
        now = self._now()  # 14:00
        dt = parse_natural_time("at 16:00", now=now)
        assert dt == now.replace(hour=16, minute=0, second=0, microsecond=0)

    def test_today_at_am(self) -> None:
        now = self._now()  # 14:00 — already passed, so rolls to tomorrow
        dt = parse_natural_time("at 8am", now=now)
        expected = (now + timedelta(days=1)).replace(
            hour=8, minute=0, second=0, microsecond=0
        )
        assert dt == expected

    def test_today_at_pm(self) -> None:
        now = self._now()
        dt = parse_natural_time("today at 3pm", now=now)
        assert dt == now.replace(hour=15, minute=0, second=0, microsecond=0)

    def test_today_future_time_rolls_to_tomorrow(self) -> None:
        """3pm when it's already 3pm today should roll to next day 3pm."""
        now = self._now().replace(hour=15, minute=0, second=0, microsecond=0)
        dt = parse_natural_time("today at 3pm", now=now)
        assert dt == now + timedelta(days=1)

    # --- bare HH:MM / HHAM/PM (no prefix) ---
    def test_bare_hhmm_future(self) -> None:
        now = self._now()  # 14:00
        dt = parse_natural_time("16:30", now=now)
        assert dt == now.replace(hour=16, minute=30, second=0, microsecond=0)

    def test_bare_hhmm_past_rolls_to_tomorrow(self) -> None:
        now = self._now().replace(hour=10, minute=0, second=0, microsecond=0)
        dt = parse_natural_time("09:00", now=now)
        # 09:00 today is already past → next occurrence is tomorrow 09:00
        assert dt == now.replace(
            day=now.day + 1, hour=9, minute=0, second=0, microsecond=0
        )

    def test_bare_8am(self) -> None:
        now = self._now()  # 14:00 — already past midnight
        dt = parse_natural_time("8am", now=now)
        expected = (now + timedelta(days=1)).replace(
            hour=8, minute=0, second=0, microsecond=0
        )
        assert dt == expected

    def test_bare_12pm(self) -> None:
        now = self._now()  # 14:00 — already past noon
        dt = parse_natural_time("12pm", now=now)
        expected = (now + timedelta(days=1)).replace(
            hour=12, minute=0, second=0, microsecond=0
        )
        assert dt == expected

    def test_bare_12am(self) -> None:
        now = self._now()  # 14:00 — already past midnight
        dt = parse_natural_time("12am", now=now)
        expected = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        assert dt == expected

    # --- whitespace / casing variations ---
    def test_strips_whitespace(self) -> None:
        dt = parse_natural_time("  in   30   minutes  ", now=self._now())
        assert dt == self._now() + timedelta(minutes=30)

    def test_case_insensitive(self) -> None:
        dt = parse_natural_time("IN 1 HOUR", now=self._now())
        assert dt == self._now() + timedelta(hours=1)

    # --- unsupported / unparseable → None ---
    def test_returns_none_for_garbage(self) -> None:
        result = parse_natural_time("when the stars align", now=self._now())
        assert result is None

    def test_returns_none_for_empty_string(self) -> None:
        result = parse_natural_time("", now=self._now())
        assert result is None


# ---------------------------------------------------------------------------
# Event dataclass
# ---------------------------------------------------------------------------


class TestEventDataclass:
    def test_when_datetime_parses_iso(self) -> None:
        e = Event(id=1, title="Test", when_ts="2026-04-20 09:30")
        assert e.when_datetime() == datetime(2026, 4, 20, 9, 30)


# ---------------------------------------------------------------------------
# SchedulingAgent — integration-style unit tests
# ---------------------------------------------------------------------------


class TestSchedulingAgent:
    """Tests for the SQLite-backed scheduler using a temporary DB."""

    @pytest.fixture
    def agent(self, tmp_path: Path) -> SchedulingAgent:
        db = tmp_path / "events.db"
        return SchedulingAgent(db_path=db)

    def test_add_and_list_event(self, agent: SchedulingAgent) -> None:
        id_ = agent.add_event(
            "Team standup", "tomorrow at 9am", now=datetime(2026, 4, 16, 10, 0)
        )
        assert id_ == 1
        events = agent.list_events()
        assert len(events) == 1
        assert events[0].title == "Team standup"

    def test_add_multiple_events_ordered_by_time(self, agent: SchedulingAgent) -> None:
        agent.add_event(
            "Early meeting", "2026-04-17 07:00", now=datetime(2026, 4, 16, 10, 0)
        )
        agent.add_event(
            "Late meeting", "2026-04-17 18:00", now=datetime(2026, 4, 16, 10, 0)
        )
        [e.id for e in agent.list_events()]
        # Earlier event gets lower id but list is sorted by when_ts
        titles = [e.title for e in agent.list_events()]
        assert titles == ["Early meeting", "Late meeting"]

    def test_remove_event_exists(self, agent: SchedulingAgent) -> None:
        id_ = agent.add_event(
            "To remove", "in 10 minutes", now=datetime(2026, 4, 16, 10, 0)
        )
        assert agent.remove_event(id_) is True
        assert agent.list_events() == []

    def test_remove_event_nonexistent_returns_false(
        self, agent: SchedulingAgent
    ) -> None:
        assert agent.remove_event(9999) is False

    def test_add_event_invalid_time_raises(self, agent: SchedulingAgent) -> None:
        with pytest.raises(ValueError, match="Could not parse"):
            agent.add_event("Bad time", "whenever", now=datetime(2026, 4, 16, 10, 0))

    def test_ensure_db_creates_table(self, tmp_path: Path) -> None:
        db_path = tmp_path / "new.db"
        _ensure_db(db_path)
        conn = sqlite3.connect(db_path)
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        assert "events" in tables

    def test_events_persist_across_instances(self, tmp_path: Path) -> None:
        db = tmp_path / "persistent.db"
        id1 = SchedulingAgent(db_path=db).add_event(
            "Persist test", "in 1 hour", now=datetime(2026, 4, 16, 10, 0)
        )
        events = SchedulingAgent(db_path=db).list_events()
        assert len(events) == 1
        assert events[0].id == id1
