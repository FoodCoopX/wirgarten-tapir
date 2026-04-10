import datetime

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime


class DataImportUtils:
    @staticmethod
    def normalize_cell(v):
        if v is None:
            return ""
        if isinstance(v, str):
            return v.strip()
        return v

    @classmethod
    def safe_int(cls, v, default=0):
        v = cls.normalize_cell(v)
        try:
            return int(v)
        except (TypeError, ValueError):
            return default

    @classmethod
    def safe_float(cls, v, default=0.0):
        v = cls.normalize_cell(v)
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    @classmethod
    def safe_bool(cls, v):
        v = cls.normalize_cell(v)
        if v == "":
            return None
        s = str(v).strip().lower()
        return s in {"1", "true", "yes", "ja", "j", "y", "x"}

    @classmethod
    def to_date(cls, v):
        v = cls.normalize_cell(v)
        if not v:
            return None
        d = parse_date(v)
        if d is None:
            try:
                d = datetime.date.strptime(v, "%d.%m.%Y")
            except ValueError:
                return None
        return d

    @classmethod
    def to_datetime_from_date(cls, v, hour=12, minute=0, tz=None):
        # Interpret a date string as a datetime at given hour in the provided/current tz
        d = cls.to_date(v)
        if not d:
            return None
        tzinfo = tz or timezone.get_current_timezone()
        return timezone.make_aware(
            datetime.datetime(d.year, d.month, d.day, hour, minute), tzinfo
        )

    @classmethod
    def to_datetime(cls, v):
        v = cls.normalize_cell(v)
        if not v:
            return None
        # Try parse full datetime first, then date-only
        dt = parse_datetime(v)
        if dt is None:
            return cls.to_datetime_from_date(v)
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        return dt

    @staticmethod
    def update_if_diff(obj, field, new_val):
        if new_val == getattr(obj, field):
            return False
        setattr(obj, field, new_val)
        return True

    @staticmethod
    def is_row_empty(row: dict):
        return not any(DataImportUtils.normalize_cell(v) for v in row.values())
