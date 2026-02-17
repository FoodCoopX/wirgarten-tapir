import json
from typing import Any, Dict, List

from django.http import HttpRequest, JsonResponse
from django.views import View

from tapir.bakery.models import AvailableBreadsForDeliveryDay, Bread


class AvailableBreadsForDeliveryListView(View):
    """Get list of breads for a specific year, week and day"""

    def get(self, request: HttpRequest) -> JsonResponse:
        """Get list of breads available for a specific year, week and day"""
        year: str | None = request.GET.get("year")
        week: str | None = request.GET.get("week")
        day: str | None = request.GET.get("day")

        if not all([year, week, day]):
            return JsonResponse(
                {"error": "Missing parameters. Required: year, week, day"}, status=400
            )

        try:
            year_int: int = int(year)
            week_int: int = int(week)
            day_int: int = int(day)
        except (ValueError, TypeError):
            return JsonResponse(
                {"error": "Invalid year, week or day format"}, status=400
            )

        # Get available breads for this delivery configuration
        available_breads = (
            AvailableBreadsForDeliveryDay.objects.filter(
                year=year_int,
                delivery_week=week_int,
                delivery_day=day_int,
                bread__is_active=True,
            )
            .select_related("bread")
            .order_by("bread__name")
        )

        breads: List[Dict[str, Any]] = [
            {
                "id": str(entry.bread.id),
                "name": entry.bread.name,
            }
            for entry in available_breads
        ]

        return JsonResponse(
            {"year": year_int, "week": week_int, "day": day_int, "breads": breads}
        )

    def post(self, request: HttpRequest) -> JsonResponse:
        """Toggle bread availability for a delivery day"""
        try:
            data = json.loads(request.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            return JsonResponse({"error": f"Invalid JSON: {str(e)}"}, status=400)

        year = data.get("year")
        week = data.get("week")
        day = data.get("day")
        bread_id = data.get("bread_id")
        is_active = data.get("is_active")

        # Debug logging
        print(f"Received POST data: {data}")
        print(
            f"year={year}, week={week}, day={day}, bread_id={bread_id}, is_active={is_active}"
        )

        if (
            year is None
            or week is None
            or day is None
            or bread_id is None
            or is_active is None
        ):
            return JsonResponse(
                {
                    "error": "Missing required fields: year, week, day, bread_id, is_active",
                    "received": data,
                },
                status=400,
            )

        try:
            bread = Bread.objects.get(id=bread_id)
        except Bread.DoesNotExist:
            return JsonResponse({"error": "Bread not found"}, status=404)

        if is_active:
            # Create or update entry
            entry, created = AvailableBreadsForDeliveryDay.objects.get_or_create(
                year=int(year),
                delivery_week=int(week),
                delivery_day=int(day),
                bread=bread,
            )
            return JsonResponse(
                {
                    "success": True,
                    "created": created,
                    "bread_id": str(bread_id),
                }
            )
        else:
            # Delete entry
            deleted_count, _ = AvailableBreadsForDeliveryDay.objects.filter(
                year=int(year),
                delivery_week=int(week),
                delivery_day=int(day),
                bread=bread,
            ).delete()
            return JsonResponse(
                {
                    "success": True,
                    "deleted": deleted_count > 0,
                    "bread_id": str(bread_id),
                }
            )
