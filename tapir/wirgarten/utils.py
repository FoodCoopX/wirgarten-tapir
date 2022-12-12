import datetime


def format_date(date: datetime.date) -> str:
    return f"{str(date.day).zfill(2)}.{str(date.month).zfill(2)}.{date.year}"
