from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.bakery.models import AvailableBreadsForDeliveryDay, Bread
from tapir.bakery.serializers import (
    AvailableBreadsForDeliveryListResponseSerializer,
    ToggleBreadRequestSerializer,
    ToggleBreadResponseSerializer,
)
from tapir.generic_exports.permissions import HasCoopManagePermission


class AvailableBreadsForDeliveryListView(APIView):
    """
    Get or toggle breads for a specific year, week and day
    """

    permission_classes = [IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        summary="Get breads for a delivery day",
        parameters=[
            OpenApiParameter(name="year", type=int, required=True),
            OpenApiParameter(name="week", type=int, required=True),
            OpenApiParameter(name="day", type=int, required=True),
        ],
        responses={200: AvailableBreadsForDeliveryListResponseSerializer},
    )
    def get(self, request: Request) -> Response:
        year = request.query_params.get("year")
        week = request.query_params.get("week")
        day = request.query_params.get("day")

        if not all([year, week, day]):
            return Response(
                {"error": "Missing parameters. Required: year, week, day"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            year_int = int(year)
            week_int = int(week)
            day_int = int(day)
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid year, week or day format"},
                status=status.HTTP_400_BAD_REQUEST,
            )

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

        breads = [
            {"id": str(entry.bread.id), "name": entry.bread.name}
            for entry in available_breads
        ]

        return Response(
            {"year": year_int, "week": week_int, "day": day_int, "breads": breads}
        )

    @extend_schema(
        summary="Toggle bread availability for a delivery day",
        request=ToggleBreadRequestSerializer,
        responses={200: ToggleBreadResponseSerializer},
    )
    def post(self, request):
        serializer = ToggleBreadRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        year = data["year"]
        week = data["week"]
        day = data["day"]
        bread_id = data["bread_id"]
        is_active = data["is_active"]

        try:
            bread = Bread.objects.get(id=bread_id)
        except Bread.DoesNotExist:
            return Response(
                {"error": "Bread not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if is_active:
            entry, created = AvailableBreadsForDeliveryDay.objects.get_or_create(
                year=year,
                delivery_week=week,
                delivery_day=day,
                bread=bread,
            )
            return Response(
                {
                    "success": True,
                    "created": created,
                    "bread_id": str(bread_id),
                }
            )
        else:
            deleted_count, _ = AvailableBreadsForDeliveryDay.objects.filter(
                year=year,
                delivery_week=week,
                delivery_day=day,
                bread=bread,
            ).delete()
            return Response(
                {
                    "success": True,
                    "deleted": deleted_count > 0,
                    "bread_id": str(bread_id),
                }
            )
