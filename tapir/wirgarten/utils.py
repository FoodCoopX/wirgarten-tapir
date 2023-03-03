import datetime
from decimal import Decimal


def format_date(date: datetime.date) -> str:
    return f"{str(date.day).zfill(2)}.{str(date.month).zfill(2)}.{date.year}"


def format_currency(number: int | float | Decimal):
    if number is None:
        return format_currency(0)
    return f"{number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
