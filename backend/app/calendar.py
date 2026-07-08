"""Pure BS <-> AD calendar conversion (nepali-datetime). No I/O."""

import datetime
from typing import NamedTuple

import nepali_datetime as nd


class CalendarError(ValueError):
    """Raised for out-of-range or otherwise invalid calendar dates."""


class BSDate(NamedTuple):
    year: int
    month: int
    day: int


def bs_to_ad(year: int, month: int, day: int) -> datetime.date:
    """Convert a Bikram Sambat date to the Gregorian (AD) date."""
    try:
        bs_date = nd.date(year, month, day)
    except ValueError as exc:
        raise CalendarError(
            f"Invalid BS date {year}-{month:02d}-{day:02d}: {exc}"
        ) from exc
    return bs_date.to_datetime_date()


def ad_to_bs(date: datetime.date) -> BSDate:
    """Convert a Gregorian (AD) date to Bikram Sambat."""
    try:
        bs_date = nd.date.from_datetime_date(date)
    except (ValueError, OverflowError) as exc:
        raise CalendarError(
            f"AD date {date.isoformat()} is outside the supported BS range "
            f"({nd.MINYEAR}-{nd.MAXYEAR}): {exc}"
        ) from exc
    return BSDate(bs_date.year, bs_date.month, bs_date.day)
