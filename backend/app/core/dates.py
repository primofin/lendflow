"""Calendar helpers shared by age checks (LF-004) and repayment schedules (LF-014)."""

from datetime import date


def add_months(day: date, months: int) -> date:
    """`day` moved forward by whole months. The day is capped at 28 so every month has it."""
    index = day.month - 1 + months
    year, month = day.year + index // 12, index % 12 + 1
    return date(year, month, min(day.day, 28))
