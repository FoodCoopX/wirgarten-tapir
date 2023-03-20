import datetime
from decimal import Decimal


def format_date(date: datetime.date) -> str:
    if date is None:
        return ""
    return f"{str(date.day).zfill(2)}.{str(date.month).zfill(2)}.{date.year}"


def format_currency(number: int | float | Decimal | str):
    if number is None or number == "":
        return format_currency(0)
    if type(number) is str:
        number = float(number)

    return f"{number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
