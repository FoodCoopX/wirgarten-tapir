from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import permissions, viewsets, status
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.configuration.parameter import get_parameter_value
from tapir.coop.services.membership_cancellation_manager import (
    MembershipCancellationManager,
)
from tapir.core.config import LEGAL_STATUS_COOPERATIVE
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.waiting_list.serializers import (
    WaitingListEntryDetailsSerializer,
    WaitingListEntrySerializer,
    WaitingListEntryUpdateSerializer,
)
from tapir.waiting_list.services.waiting_list_categories_service import (
    WaitingListCategoriesService,
)
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import (
    WaitingListEntry,
    WaitingListProductWish,
    WaitingListPickupLocationWish,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import get_active_and_future_subscriptions
from tapir.wirgarten.utils import get_today


class WaitingListView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = "waiting_list/list.html"
    permission_required = Permission.Coop.MANAGE


class WaitingListApiView(APIView):
    serializer_class = WaitingListEntryDetailsSerializer(many=True)
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]
    pagination_class = LimitOffsetPagination

    def __init__(self):
        super().__init__()
        self.cache = {}

    @extend_schema(
        responses={200: WaitingListEntryDetailsSerializer(many=True)},
        parameters=[
            OpenApiParameter(name="limit", type=int, required=True),
            OpenApiParameter(name="offset", type=int, required=True),
        ],
    )
    def get(self, request):
        pagination = self.pagination_class()
        entries = (
            WaitingListEntry.objects.order_by("created_at")
            .prefetch_related(
                "product_wishes__product", "pickup_location_wishes__pickup_location"
            )
            .select_related("member")
        )
        entries = pagination.paginate_queryset(entries, request)

        data = [self.build_entry_data(entry) for entry in entries]
        serializer = WaitingListEntryDetailsSerializer(data, many=True)

        return pagination.get_paginated_response(serializer.data)

    def build_entry_data(self, entry: WaitingListEntry):
        date_of_entry_in_cooperative = None
        current_pickup_location = None
        member_no = None
        current_products = None
        if entry.member is not None:
            member_no = entry.member.member_no
            self.fill_entry_with_personal_data(entry)
            date_of_entry_in_cooperative = (
                MembershipCancellationManager.get_coop_entry_date(entry.member)
            )
            pickup_location_id = (
                MemberPickupLocationService.get_member_pickup_location_id(
                    entry.member, reference_date=get_today(cache=self.cache)
                )
            )
            current_pickup_location = TapirCache.get_pickup_location_by_id(
                cache=self.cache,
                pickup_location_id=pickup_location_id,
            )
            current_products = {
                subscription.product
                for subscription in get_active_and_future_subscriptions(
                    cache=self.cache
                )
                .filter(member=entry.member)
                .select_related("product__type")
            }

        return {
            "id": entry.id,
            "member_no": member_no,
            "waiting_since": entry.created_at,
            "first_name": entry.first_name,
            "last_name": entry.last_name,
            "email": entry.email,
            "phone_number": entry.phone_number,
            "street": entry.street,
            "street_2": entry.street_2,
            "postcode": entry.postcode,
            "city": entry.city,
            "country": entry.country,
            "date_of_entry_in_cooperative": date_of_entry_in_cooperative,
            "current_pickup_location": current_pickup_location,
            "current_products": current_products,
            "pickup_location_wishes": entry.pickup_location_wishes.all(),
            "product_wishes": entry.product_wishes.all(),
            "desired_start_date": entry.desired_start_date,
            "number_of_coop_shares": entry.number_of_coop_shares,
            "comment": entry.comment,
            "category": entry.category,
            "member_already_exists": entry.member is not None,
        }

    @staticmethod
    def fill_entry_with_personal_data(entry: WaitingListEntry):
        personal_data_fields = [
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "street",
            "street_2",
            "postcode",
            "city",
            "country",
        ]
        for field in personal_data_fields:
            setattr(entry, field, getattr(entry.member, field))


class WaitingListEntryViewSet(viewsets.ModelViewSet):
    queryset = WaitingListEntry.objects.all()
    serializer_class = WaitingListEntrySerializer
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]


class WaitingListEntryUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    def __init__(self):
        super().__init__()
        self.cache = {}

    @extend_schema(
        responses={200: str},
        request=WaitingListEntryUpdateSerializer,
    )
    @transaction.atomic
    def post(self, request):
        serializer = WaitingListEntryUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        waiting_list_entry = get_object_or_404(
            WaitingListEntry, pk=serializer.validated_data["id"]
        )
        waiting_list_entry.first_name = serializer.validated_data["first_name"]
        waiting_list_entry.last_name = serializer.validated_data["last_name"]
        waiting_list_entry.email = serializer.validated_data["email"]
        waiting_list_entry.phone_number = serializer.validated_data["phone_number"]
        waiting_list_entry.street = serializer.validated_data["street"]
        waiting_list_entry.street_2 = serializer.validated_data["street_2"]
        waiting_list_entry.postcode = serializer.validated_data["postcode"]
        waiting_list_entry.city = serializer.validated_data["city"]
        waiting_list_entry.desired_start_date = serializer.validated_data.get(
            "desired_start_date", None
        )
        waiting_list_entry.comment = serializer.validated_data["comment"]
        waiting_list_entry.category = serializer.validated_data.get("category", None)
        waiting_list_entry.save()

        waiting_list_entry.product_wishes.all().delete()
        product_wishes = []
        for index, product_id in enumerate(serializer.validated_data["product_ids"]):
            product_wishes.append(
                WaitingListProductWish(
                    waiting_list_entry=waiting_list_entry,
                    product_id=product_id,
                    quantity=serializer.validated_data["product_quantities"][index],
                )
            )
        WaitingListProductWish.objects.bulk_create(product_wishes)

        waiting_list_entry.pickup_location_wishes.all().delete()
        pickup_location_wishes = []
        for index, pickup_location_id in enumerate(
            serializer.validated_data["pickup_location_ids"]
        ):
            pickup_location_wishes.append(
                WaitingListPickupLocationWish(
                    waiting_list_entry=waiting_list_entry,
                    pickup_location_id=pickup_location_id,
                    priority=index + 1,
                )
            )
        WaitingListPickupLocationWish.objects.bulk_create(pickup_location_wishes)

        return Response("OK", status=status.HTTP_200_OK)


class WaitingListCategoriesView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        responses={200: list[str]},
    )
    def get(self, request):
        return Response(
            WaitingListCategoriesService.get_categories(cache={}),
            status=status.HTTP_200_OK,
        )


class WaitingListShowsCoopContentView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        responses={200: bool},
    )
    def get(self, request):
        return Response(
            (
                get_parameter_value(ParameterKeys.ORGANISATION_LEGAL_STATUS)
                == LEGAL_STATUS_COOPERATIVE
            ),
            status=status.HTTP_200_OK,
        )
