"""
Trading Calendar
================
Manages trading days, holidays, and special trading sessions for Indian markets.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import pytz

logger = logging.getLogger('market_data.calendar')


class HolidayType(str, Enum):
    WEEKEND = "WEEKEND"
    NATIONAL_HOLIDAY = "NATIONAL_HOLIDAY"
    FESTIVAL = "FESTIVAL"
    BSE_SPECIAL = "BSE_SPECIAL"
    NSE_SPECIAL = "NSE_SPECIAL"
    POWER_CUT = "POWER_CUT"
    EMERGENCY = "EMERGENCY"


@dataclass
class Holiday:
    date: date
    description: str
    exchange: str
    holiday_type: HolidayType
    is_trading_holiday: bool = True


@dataclass
class TradingDay:
    date: date
    day_type: str
    sessions: List[str]
    is_trading_day: bool


class TradingCalendar:
    """
    Comprehensive trading calendar for Indian markets.
    """

    NSE_HOLIDAYS_2024 = [
        ("2024-01-26", "Republic Day", HolidayType.NATIONAL_HOLIDAY),
        ("2024-02-19", "Mahashivratri", HolidayType.FESTIVAL),
        ("2024-03-25", "Holi", HolidayType.FESTIVAL),
        ("2024-03-29", "Good Friday", HolidayType.NATIONAL_HOLIDAY),
        ("2024-04-11", "Id-ul-Fitr", HolidayType.FESTIVAL),
        ("2024-04-17", "Maharashtra Day", HolidayType.NSE_SPECIAL),
        ("2024-05-01", "Labour Day", HolidayType.NATIONAL_HOLIDAY),
        ("2024-06-17", "Id-ul-Zuha", HolidayType.FESTIVAL),
        ("2024-07-17", "Ashoka Jayanti", HolidayType.NSE_SPECIAL),
        ("2024-08-15", "Independence Day", HolidayType.NATIONAL_HOLIDAY),
        ("2024-09-16", "Ganesh Chaturthi", HolidayType.FESTIVAL),
        ("2024-10-02", "Mahatma Gandhi Jayanti", HolidayType.NATIONAL_HOLIDAY),
        ("2024-10-11", "Dussehra", HolidayType.FESTIVAL),
        ("2024-10-31", "Diwali", HolidayType.FESTIVAL),
        ("2024-11-01", "Diwali (Banking)", HolidayType.NSE_SPECIAL),
        ("2024-12-25", "Christmas", HolidayType.NATIONAL_HOLIDAY),
    ]

    NSE_HOLIDAYS_2025 = [
        ("2025-01-01", "New Year", HolidayType.NATIONAL_HOLIDAY),
        ("2025-01-13", "Makar Sankranti", HolidayType.FESTIVAL),
        ("2025-01-26", "Republic Day", HolidayType.NATIONAL_HOLIDAY),
        ("2025-02-26", "Mahashivratri", HolidayType.FESTIVAL),
        ("2025-03-14", "Holi", HolidayType.FESTIVAL),
        ("2025-04-18", "Good Friday", HolidayType.NATIONAL_HOLIDAY),
        ("2025-04-21", "Easter", HolidayType.FESTIVAL),
        ("2025-05-01", "Labour Day", HolidayType.NATIONAL_HOLIDAY),
        ("2025-08-15", "Independence Day", HolidayType.NATIONAL_HOLIDAY),
        ("2025-10-02", "Mahatma Gandhi Jayanti", HolidayType.NATIONAL_HOLIDAY),
        ("2025-10-20", "Dussehra", HolidayType.FESTIVAL),
        ("2025-10-31", "Diwali", HolidayType.FESTIVAL),
        ("2025-12-25", "Christmas", HolidayType.NATIONAL_HOLIDAY),
    ]

    def __init__(self):
        self._holidays: Dict[date, Holiday] = {}
        self._tz = pytz.timezone("Asia/Kolkata")

        self._load_holidays()

    def _load_holidays(self) -> None:
        holiday_lists = [
            self.NSE_HOLIDAYS_2024,
            self.NSE_HOLIDAYS_2025,
        ]

        for holiday_list in holiday_lists:
            for date_str, description, holiday_type in holiday_list:
                d = date.fromisoformat(date_str)
                self._holidays[d] = Holiday(
                    date=d,
                    description=description,
                    exchange="NSE",
                    holiday_type=holiday_type,
                )

    def is_trading_day(self, check_date: Optional[date] = None) -> bool:
        if check_date is None:
            check_date = datetime.now(self._tz).date()

        if check_date.weekday() >= 5:
            return False

        return check_date not in self._holidays

    def is_holiday(self, check_date: Optional[date] = None) -> bool:
        if check_date is None:
            check_date = datetime.now(self._tz).date()

        return check_date in self._holidays

    def get_holiday(self, check_date: date) -> Optional[Holiday]:
        return self._holidays.get(check_date)

    def get_holidays_in_range(
        self,
        start_date: date,
        end_date: date,
    ) -> List[Holiday]:
        holidays = []
        current = start_date

        while current <= end_date:
            holiday = self._holidays.get(current)
            if holiday:
                holidays.append(holiday)
            current += timedelta(days=1)

        return holidays

    def get_trading_days_in_range(
        self,
        start_date: date,
        end_date: date,
    ) -> List[date]:
        trading_days = []
        current = start_date

        while current <= end_date:
            if self.is_trading_day(current):
                trading_days.append(current)
            current += timedelta(days=1)

        return trading_days

    def get_next_trading_day(
        self,
        from_date: Optional[date] = None,
    ) -> Optional[date]:
        if from_date is None:
            from_date = datetime.now(self._tz).date()

        next_day = from_date + timedelta(days=1)

        for _ in range(10):
            if self.is_trading_day(next_day):
                return next_day
            next_day += timedelta(days=1)

        return None

    def get_previous_trading_day(
        self,
        from_date: Optional[date] = None,
    ) -> Optional[date]:
        if from_date is None:
            from_date = datetime.now(self._tz).date()

        prev_day = from_date - timedelta(days=1)

        for _ in range(10):
            if self.is_trading_day(prev_day):
                return prev_day
            prev_day -= timedelta(days=1)

        return None

    def get_trading_dates(
        self,
        year: int,
        month: Optional[int] = None,
    ) -> List[date]:
        if month:
            start = date(year, month, 1)
            if month == 12:
                end = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                end = date(year, month + 1, 1) - timedelta(days=1)
        else:
            start = date(year, 1, 1)
            end = date(year, 12, 31)

        return self.get_trading_days_in_range(start, end)

    def get_month_calendar(
        self,
        year: int,
        month: int,
    ) -> Dict[str, Any]:
        trading_days = self.get_trading_dates(year, month)
        holidays = self.get_holidays_in_range(
            date(year, month, 1),
            date(year, month, 28) if month != 12 else date(year, 12, 31),
        )

        return {
            "year": year,
            "month": month,
            "trading_days": [d.isoformat() for d in trading_days],
            "holidays": [
                {"date": h.date.isoformat(), "description": h.description, "type": h.holiday_type.value}
                for h in holidays
            ],
            "total_trading_days": len(trading_days),
        }

    def get_upcoming_holidays(
        self,
        days_ahead: int = 30,
    ) -> List[Holiday]:
        today = datetime.now(self._tz).date()
        end_date = today + timedelta(days=days_ahead)

        return [
            h for d, h in sorted(self._holidays.items())
            if today <= d <= end_date
        ]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_holidays_loaded": len(self._holidays),
            "upcoming_holidays_30_days": len(self.get_upcoming_holidays(30)),
        }


_calendar: Optional[TradingCalendar] = None


def get_trading_calendar() -> TradingCalendar:
    global _calendar
    if _calendar is None:
        _calendar = TradingCalendar()
    return _calendar