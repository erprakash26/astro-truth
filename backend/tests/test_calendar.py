import datetime

import pytest

from app.calendar import CalendarError, ad_to_bs, bs_to_ad


def test_bs_to_ad_reference_date():
    ad_date = bs_to_ad(2056, 9, 17)
    assert ad_date == datetime.date(2000, 1, 1)
    assert ad_date.strftime("%A") == "Saturday"


def test_ad_to_bs_reference_date():
    assert ad_to_bs(datetime.date(2000, 1, 1)) == (2056, 9, 17)


def test_round_trip():
    assert ad_to_bs(bs_to_ad(2056, 9, 17)) == (2056, 9, 17)


@pytest.mark.parametrize(
    "year, month, day",
    [(2056, 13, 1), (2056, 9, 35), (1974, 1, 1), (2101, 1, 1)],
)
def test_bs_to_ad_invalid_dates_raise_calendar_error(year, month, day):
    with pytest.raises(CalendarError):
        bs_to_ad(year, month, day)


def test_ad_to_bs_out_of_range_raises_calendar_error():
    with pytest.raises(CalendarError):
        ad_to_bs(datetime.date(1900, 1, 1))
