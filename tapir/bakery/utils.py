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
        return (
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


def int_query_param(request, name: str):
    """An optional integer query parameter, or None; a non-numeric value is a 400."""
    raw = request.query_params.get(name)
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise ValidationError({name: "Muss eine ganze Zahl sein."})
