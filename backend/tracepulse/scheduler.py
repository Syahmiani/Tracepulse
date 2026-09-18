from __future__ import annotations
import re
import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, time as dt_time


_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def _parse_time(value: str) -> dt_time:
    match = _TIME_RE.match(value.strip())
    if not match:
        raise ValueError("time must be HH:MM 24-hour format")
    return dt_time(int(match.group(1)), int(match.group(2)))


@dataclass(frozen=True)
class ScheduledLock:
    schedule_id: str
    label: str
    start: dt_time
    end: dt_time
    days: frozenset[int]  # 0=Monday .. 6=Sunday, empty set means every day

    def covers(self, moment: datetime) -> bool:
        if self.days and moment.weekday() not in self.days:
            return False
        current = moment.time()
        if self.start <= self.end:
            return self.start <= current < self.end
        # window crosses midnight, e.g. 22:00-06:00
        return current >= self.start or current < self.end

    def as_dict(self) -> dict:
        return {
            "schedule_id": self.schedule_id,
            "label": self.label,
            "start": self.start.strftime("%H:%M"),
            "end": self.end.strftime("%H:%M"),
            "days": sorted(self.days),
        }


class ManualScheduler:
    """Pre-set hard-lock windows (e.g. GMI prayer breaks, lunch).

    This intentionally keeps schedules in memory only: they reset if the
    backend restarts. That is a reasonable and honest scope for a demo/FYP
    build; persisting schedules across restarts would mean adding a
    dedicated migration/table, which is future work rather than something
    to fake here.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._schedules: dict[str, ScheduledLock] = {}

    def add(self, *, label: str, start: str, end: str, days=()) -> ScheduledLock:
        label = label.strip()
        if not label:
            raise ValueError("label is required")
        parsed_days = frozenset(int(d) for d in days)
        if any(d < 0 or d > 6 for d in parsed_days):
            raise ValueError("days must be 0 (Monday) through 6 (Sunday)")
        schedule = ScheduledLock(secrets.token_urlsafe(9), label, _parse_time(start), _parse_time(end), parsed_days)
        with self._lock:
            self._schedules[schedule.schedule_id] = schedule
        return schedule

    def remove(self, schedule_id: str) -> bool:
        with self._lock:
            return self._schedules.pop(schedule_id, None) is not None

    def list(self) -> list[ScheduledLock]:
        with self._lock:
            return list(self._schedules.values())

    def active_at(self, moment: datetime) -> ScheduledLock | None:
        with self._lock:
            for schedule in self._schedules.values():
                if schedule.covers(moment):
                    return schedule
        return None
