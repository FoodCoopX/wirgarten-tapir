from rest_framework.exceptions import ValidationError

from typing import Any, Optional, Tuple

from rest_framework import status
from rest_framework.response import Response

# How many breads a member may mark as favourites. Enforced on the server as
# well as in PreferredBreadsModal.tsx: without a limit a member counts as
# trivially "satisfied" in the metrics and multiplies their claims in the
# solver's preference weighting.
MAX_PREFERRED_BREADS = 3


def str_to_bool(value: Optional[str]) -> Optional[bool]:
    """
    Convert string representation of boolean to actual boolean.

    """
    if value is None:
        return None
    return value.lower() in ["true", "1", "yes"]


def parse_week_params(query_params: Any) -> Tuple[int, int, Optional[int]] | Response:
    """
    Parse year, delivery_week, and optional delivery_day from query params.

    Returns:
        Tuple of (year, delivery_week, delivery_day) on success
        Response object with error on failure
    """
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
    """
    An optional integer query parameter, or None.

    Raises DRF's ValidationError - a 400 - rather than letting a non-numeric
    value reach the ORM, where it would surface as an unhandled ValueError.
    """
    raw = request.query_params.get(name)
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise ValidationError({name: "Muss eine ganze Zahl sein."})
