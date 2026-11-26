import datetime

from rest_framework.exceptions import ValidationError

from typing import Any, Optional, Tuple

from rest_framework import status
from rest_framework.response import Response

# Also enforced in the frontend's PreferredBreadsModal.tsx.
MAX_PREFERRED_BREADS = 3


def str_to_bool(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    return value.lower() in ["true", "1", "yes"]


ISO_WEEK_MISSING_MESSAGE = "Diese Woche gibt es in dem Jahr nicht."


def is_valid_iso_week(year: int, week: int) -> bool:
    """
    A year has 52 or 53 ISO weeks. Every day of the week must be a date
    Python can hold, the Sunday included.
    """
    try:
        datetime.date.fromisocalendar(year, week, 7)
    except (ValueError, OverflowError, TypeError):
        return False
    return True


def parse_week_params(query_params: Any) -> Tuple[int, int, Optional[int]] | Response:
    year = query_params.get("year")
    delivery_week = query_params.get("delivery_week")
    delivery_day_param = query_params.get("delivery_day")

    if not year or not delivery_week:
        return Response(
            {"error": "Missing required parameters: year, delivery_week"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        parsed = (
            int(year),
            int(delivery_week),
            int(delivery_day_param) if delivery_day_param else None,
        )
    except (ValueError, TypeError):
        return Response(
            {
                "error": "Invalid parameter format. Year and delivery_week must be integers."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not is_valid_iso_week(parsed[0], parsed[1]):
        return Response(
            {"error": ISO_WEEK_MISSING_MESSAGE}, status=status.HTTP_400_BAD_REQUEST
        )
    if parsed[2] is not None and not 0 <= parsed[2] <= 6:
        return Response(
            {"error": "delivery_day must be between 0 (Monday) and 6 (Sunday)."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return parsed


def int_query_param(request, name: str):
    """An optional integer query parameter, or None; a non-numeric value is a 400."""
    raw = request.query_params.get(name)
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise ValidationError({name: "Muss eine ganze Zahl sein."})
