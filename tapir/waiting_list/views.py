from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import permissions
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.views import APIView

from tapir.coop.services.membership_cancellation_manager import (
    MembershipCancellationManager,
)
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.waiting_list.serializers import WaitingListEntrySerializer
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import WaitingListEntry
from tapir.wirgarten.service.products import get_active_and_future_subscriptions
from tapir.wirgarten.utils import get_today


class WaitingListView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = "waiting_list/list.html"
    permission_required = Permission.Coop.MANAGE


class WaitingListApiView(APIView):
    serializer_class = WaitingListEntrySerializer(many=True)
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]
    pagination_class = LimitOffsetPagination

    def __init__(self):
        super().__init__()
        self.cache = {}

    @extend_schema(
        responses={200: WaitingListEntrySerializer(many=True)},
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
        serializer = WaitingListEntrySerializer(data, many=True)

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
            "pickup_location_wishes": [
                wish.pickup_location for wish in entry.pickup_location_wishes.all()
            ],
            "product_wishes": [wish.product for wish in entry.product_wishes.all()],
            "desired_start_date": entry.desired_start_date,
            "number_of_coop_shares": entry.number_of_coop_shares,
        }

    def fill_entry_with_personal_data(self, entry: WaitingListEntry):
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
