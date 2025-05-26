import datetime

from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.apps import DeliveriesConfig
from tapir.deliveries.models import Joker, DeliveryDayAdjustment
from tapir.deliveries.serializers import (
    DeliverySerializer,
    MemberJokerInformationSerializer,
    UsedJokerInGrowingPeriodSerializer,
    GrowingPeriodSerializer,
    GrowingPeriodWithDeliveryDayAdjustmentsSerializer,
)
from tapir.deliveries.services.get_deliveries_service import GetDeliveriesService
from tapir.deliveries.services.joker_management_service import (
    JokerManagementService,
)
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.utils.shortcuts import get_monday
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import Member, GrowingPeriod
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.delivery import get_next_delivery_date
from tapir.wirgarten.utils import check_permission_or_self, get_today, format_date


class GetMemberDeliveriesView(APIView):
    @extend_schema(
        responses={200: DeliverySerializer(many=True)},
        parameters=[OpenApiParameter(name="member_id", type=str)],
    )
    def get(self, request):
        member_id = request.query_params.get("member_id")
        check_permission_or_self(member_id, request)
        member = get_object_or_404(Member, id=member_id)
        cache = {}

        deliveries = GetDeliveriesService.get_deliveries(
            member=member,
            date_from=get_today(),
            date_to=get_today() + datetime.timedelta(days=365),
            cache=cache,
        )

        return Response(
            DeliverySerializer(deliveries, many=True).data,
            status=status.HTTP_200_OK,
        )


class GetMemberJokerInformationView(APIView):
    @extend_schema(
        responses={200: MemberJokerInformationSerializer()},
        parameters=[OpenApiParameter(name="member_id", type=str)],
    )
    def get(self, request):
        cache = {}
        if not get_parameter_value(ParameterKeys.JOKERS_ENABLED, cache=cache):
            return Response(
                "The joker feature is disabled",
                status=status.HTTP_403_FORBIDDEN,
            )

        member_id = request.query_params.get("member_id")
        check_permission_or_self(member_id, request)

        growing_periods = GrowingPeriod.objects.filter(
            end_date__gte=get_today()
        ).order_by("start_date")
        jokers = []
        if growing_periods.exists():
            jokers = Joker.objects.filter(
                member_id=member_id, date__gte=growing_periods.first().start_date
            ).order_by("date")

        joker_data = [
            {
                "joker": joker,
                "cancellation_limit": JokerManagementService.get_date_limit_for_joker_changes(
                    joker.date, cache=cache
                ),
                "delivery_date": get_next_delivery_date(
                    get_monday(joker.date), cache=cache
                ),
            }
            for joker in jokers
        ]

        data = {
            "used_jokers": joker_data,
            "weekday_limit": get_parameter_value(
                ParameterKeys.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL, cache=cache
            ),
            "used_joker_in_growing_period": self.build_data_used_joker_in_growing_period(
                member_id
            ),
        }

        return Response(
            MemberJokerInformationSerializer(data).data,
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def build_data_used_joker_in_growing_period(member_id):
        growing_periods = GrowingPeriod.objects.filter(
            end_date__gte=get_today()
        ).order_by("start_date")
        data = []
        for growing_period in growing_periods:
            nb_used_jokers_in_growing_period = Joker.objects.filter(
                member_id=member_id,
                date__gte=growing_period.start_date,
                date__lte=growing_period.end_date,
            ).count()
            data.append(
                UsedJokerInGrowingPeriodSerializer(
                    {
                        "growing_period_start": growing_period.start_date,
                        "growing_period_end": growing_period.end_date,
                        "number_of_used_jokers": nb_used_jokers_in_growing_period,
                        "max_jokers": growing_period.max_jokers_per_member,
                        "joker_restrictions": JokerManagementService.get_extra_joker_restrictions(
                            growing_period
                        ),
                    }
                ).data
            )

        return data


class CancelJokerView(APIView):
    @extend_schema(
        responses={200: str, 403: str},
        parameters=[OpenApiParameter(name="joker_id", type=str)],
    )
    def post(self, request):
        cache = {}
        if not get_parameter_value(ParameterKeys.JOKERS_ENABLED, cache=cache):
            return Response(
                "The joker feature is disabled",
                status=status.HTTP_403_FORBIDDEN,
            )

        joker_id = request.query_params.get("joker_id")
        joker = get_object_or_404(Joker, id=joker_id)
        check_permission_or_self(joker.member_id, request)

        if not JokerManagementService.can_joker_be_cancelled(joker, cache=cache):
            return Response(
                f"Es ist zu spät um dieses Joker abzusagen. Heute: {format_date(get_today(cache=cache))}, Joker: {format_date(joker.date)}",
                status=status.HTTP_403_FORBIDDEN,
            )

        JokerManagementService.cancel_joker(joker)

        TransactionalTrigger.fire_action(
            trigger_data=TransactionalTriggerData(
                key=DeliveriesConfig.MAIL_TRIGGER_JOKER_CANCELLED,
                recipient_id_in_base_queryset=joker.member.id,
                token_data={"joker_date": joker.date},
            ),
        )

        return Response(
            "Joker abgesagt",
            status=status.HTTP_200_OK,
        )


class UseJokerView(APIView):
    @extend_schema(
        responses={200: str, 403: str},
        parameters=[
            OpenApiParameter(name="member_id", type=str),
            OpenApiParameter(name="date", type=datetime.date),
        ],
    )
    def post(self, request):
        cache = {}
        if not get_parameter_value(ParameterKeys.JOKERS_ENABLED, cache=cache):
            return Response(
                "The joker feature is disabled",
                status=status.HTTP_403_FORBIDDEN,
            )

        member_id = request.query_params.get("member_id")
        date_string = request.query_params.get("date")
        date = datetime.datetime.strptime(date_string, "%Y-%m-%d").date()
        check_permission_or_self(member_id, request)

        member = get_object_or_404(Member, id=member_id)

        if not JokerManagementService.can_joker_be_used_in_week(
            member, date, cache=cache
        ):
            return Response(
                "Du darfst an dem Liefertag kein Joker einsetzen",
                status=status.HTTP_403_FORBIDDEN,
            )

        joker = Joker.objects.create(member=member, date=date)

        TransactionalTrigger.fire_action(
            TransactionalTriggerData(
                key=DeliveriesConfig.MAIL_TRIGGER_JOKER_USED,
                recipient_id_in_base_queryset=joker.member.id,
                token_data={"joker_date": joker.date},
            ),
        )

        return Response(
            "Joker angesetzt",
            status=status.HTTP_200_OK,
        )


class GrowingPeriodViewSet(ModelViewSet):
    queryset = GrowingPeriod.objects.order_by("start_date")
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]
    serializer_class = GrowingPeriodSerializer


class GrowingPeriodWithDeliveryDayAdjustmentsView(APIView):
    def __init__(self):
        super().__init__()
        self.cache = {}

    @extend_schema(
        responses={200: GrowingPeriodWithDeliveryDayAdjustmentsSerializer()},
        parameters=[OpenApiParameter(name="growing_period_id", type=str)],
    )
    def get(self, request):
        if not request.user.has_perm(Permission.Coop.MANAGE):
            return Response(status=status.HTTP_403_FORBIDDEN)

        growing_period = get_object_or_404(
            GrowingPeriod, id=request.query_params.get("growing_period_id")
        )
        adjustments = DeliveryDayAdjustment.objects.filter(
            growing_period=growing_period
        ).order_by("calendar_week")

        growing_period.weeks_without_delivery.sort()

        return Response(
            GrowingPeriodWithDeliveryDayAdjustmentsSerializer(
                {
                    "growing_period_id": growing_period.id,
                    "growing_period_start_date": growing_period.start_date,
                    "growing_period_end_date": growing_period.end_date,
                    "growing_period_weeks_without_delivery": growing_period.weeks_without_delivery,
                    "adjustments": [
                        {
                            "calendar_week": adjustment.calendar_week,
                            "adjusted_weekday": adjustment.adjusted_weekday,
                        }
                        for adjustment in adjustments
                    ],
                    "max_jokers_per_member": growing_period.max_jokers_per_member,
                    "joker_restrictions": growing_period.joker_restrictions,
                    "jokers_enabled": get_parameter_value(
                        ParameterKeys.JOKERS_ENABLED, cache=self.cache
                    ),
                }
            ).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        responses={200: str},
        request=GrowingPeriodWithDeliveryDayAdjustmentsSerializer(),
    )
    def patch(self, request):
        if not request.user.has_perm(Permission.Coop.MANAGE):
            return Response(status=status.HTTP_403_FORBIDDEN)

        request_serializer = GrowingPeriodWithDeliveryDayAdjustmentsSerializer(
            data=request.data
        )
        request_serializer.is_valid(raise_exception=True)

        growing_period = get_object_or_404(
            GrowingPeriod, id=request_serializer.validated_data["growing_period_id"]
        )

        with transaction.atomic():
            growing_period.start_date = request_serializer.validated_data[
                "growing_period_start_date"
            ]
            growing_period.end_date = request_serializer.validated_data[
                "growing_period_end_date"
            ]
            growing_period.weeks_without_delivery = request_serializer.validated_data[
                "growing_period_weeks_without_delivery"
            ]
            growing_period.max_jokers_per_member = request_serializer.validated_data[
                "max_jokers_per_member"
            ]
            growing_period.joker_restrictions = request_serializer.validated_data[
                "joker_restrictions"
            ]
            growing_period.save()

            DeliveryDayAdjustment.objects.filter(growing_period=growing_period).delete()
            DeliveryDayAdjustment.objects.bulk_create(
                [
                    DeliveryDayAdjustment(
                        growing_period=growing_period,
                        adjusted_weekday=adjustment_data["adjusted_weekday"],
                        calendar_week=adjustment_data["calendar_week"],
                    )
                    for adjustment_data in request_serializer.validated_data[
                        "adjustments"
                    ]
                ]
            )

        return Response(
            "OK",
            status=status.HTTP_200_OK,
        )
