"""Política temporal central: instantes en UTC y fechas civiles en Ecuador continental."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

ECUADOR_TZ = ZoneInfo("America/Guayaquil")


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def ecuador_now() -> datetime:
    return datetime.now(ECUADOR_TZ)


def ecuador_today() -> date:
    return ecuador_now().date()
