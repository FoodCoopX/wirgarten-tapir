from typing import Type

from django.db import transaction
from django.db.models import Model
from django.http import Http404
from django.urls import reverse
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status, permissions
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.subscriptions.serializers import (
    MemberDataToConfirmSerializer,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import (
    Member,
    Subscription,
    CoopShareTransaction,
)
from tapir.wirgarten.utils import (
    get_today,
    get_now,
)


class MemberDataToConfirmApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        responses={200: MemberDataToConfirmSerializer(many=True)},
    )
    def get(self, request):
        changes_by_member = {}

        unconfirmed_cancellations = Subscription.objects.filter(
            cancellation_ts__isnull=False,
            cancellation_admin_confirmed__isnull=True,
        ).select_related("member", "product__type")
        self.group_changes_by_member_and_product_type(
            subscriptions=unconfirmed_cancellations,
            key="cancellations",
            changes_by_member=changes_by_member,
        )

        unconfirmed_creations = Subscription.objects.filter(
            admin_confirmed__isnull=True
        ).select_related("member", "product__type")
        self.group_changes_by_member_and_product_type(
            subscriptions=unconfirmed_creations,
            key="creations",
            changes_by_member=changes_by_member,
        )

        cache = {}

        for member in Member.objects.all():
            if member in changes_by_member.keys():
                continue
            unconfirmed_share_purchases = (
                TapirCache.get_unconfirmed_coop_share_purchases_by_member_id(
                    cache=cache
                ).get(member.id, [])
            )
            if len(unconfirmed_share_purchases) == 0:
                continue
            changes_by_member[member] = {}

        data = MemberDataToConfirmSerializer(
            [
                self.build_data_to_confirm_for_member(
                    member=member,
                    changes_by_product_type=changes_by_product_type,
                    cache=cache,
                )
                for member, changes_by_product_type in changes_by_member.items()
            ],
            many=True,
        ).data

        return Response(data)

    @staticmethod
    def get_number_of_unconfirmed_changes(cache: dict):

        return (
            Subscription.objects.filter(
                cancellation_ts__isnull=False,
                cancellation_admin_confirmed__isnull=True,
            ).count()
            + Subscription.objects.filter(admin_confirmed__isnull=True).count()
            + len(
                TapirCache.get_unconfirmed_coop_share_purchases_by_member_id(
                    cache=cache
                ).keys()
            )
        )

    @classmethod
    def group_changes_by_member_and_product_type(
        cls, subscriptions, key: str, changes_by_member: dict
    ):
        for subscription in subscriptions:
            if subscription.member not in changes_by_member.keys():
                changes_by_member[subscription.member] = {}

            if (
                subscription.product.type
                not in changes_by_member[subscription.member].keys()
            ):
                changes_by_member[subscription.member][subscription.product.type] = {
                    "cancellations": [],
                    "creations": [],
                }

            changes_by_member[subscription.member][subscription.product.type][
                key
            ].append(subscription)

    @classmethod
    def build_data_to_confirm_for_member(
        cls,
        member: Member,
        changes_by_product_type: dict,
        cache: dict,
    ) -> dict:
        pickup_location_id = (
            MemberPickupLocationService.get_member_pickup_location_id_from_cache(
                member.id, reference_date=get_today(cache=cache), cache=cache
            )
        )

        pickup_location = None
        if pickup_location_id is not None:
            pickup_location = TapirCache.get_pickup_location_by_id(
                cache=cache, pickup_location_id=pickup_location_id
            )

        creations = []
        cancellations = []
        changes = []
        for (
            product_type,
            changes_for_this_product_type,
        ) in changes_by_product_type.items():
            if product_type is None:
                continue
            creations_for_this_product_type = changes_for_this_product_type["creations"]
            cancellations_for_this_product_type = changes_for_this_product_type[
                "cancellations"
            ]

            if (
                len(creations_for_this_product_type) > 0
                and len(cancellations_for_this_product_type) == 0
            ):
                creations.extend(creations_for_this_product_type)
                continue

            if (
                len(creations_for_this_product_type) == 0
                and len(cancellations_for_this_product_type) > 0
            ):
                cancellations.extend(cancellations_for_this_product_type)
                continue

            changes.append(
                {
                    "product_type": product_type,
                    "subscription_cancellations": cancellations_for_this_product_type,
                    "subscription_creations": creations_for_this_product_type,
                }
            )

        cancellation_types = []
        show_warning = False
        for cancellation in cancellations:
            cancellation_type, cancellation_shows_warning = cls.get_cancellation_type(
                cancellation, cache=cache
            )
            show_warning = show_warning or cancellation_shows_warning
            cancellation_types.append(cancellation_type)

        return {
            "member": member,
            "member_profile_url": reverse("wirgarten:member_detail", args=[member.id]),
            "pickup_location": pickup_location,
            "subscription_cancellations": cancellations,
            "cancellation_types": cancellation_types,
            "show_warning": show_warning,
            "subscription_creations": creations,
            "subscription_changes": changes,
            "share_purchases": TapirCache.get_unconfirmed_coop_share_purchases_by_member_id(
                cache=cache
            ).get(
                member.id, []
            ),
        }

    @staticmethod
    def get_cancellation_type(subscription: Subscription, cache: dict):
        cancellation_type = "Reguläre Kündigung"
        show_warning = False
        growing_period = TapirCache.get_growing_period_at_date(
            reference_date=subscription.end_date, cache=cache
        )
        if growing_period.end_date > subscription.end_date:
            cancellation_type = "Unterjährige Kündigung"
            show_warning = True
        if TrialPeriodManager.is_subscription_in_trial(
            subscription=subscription,
            reference_date=subscription.cancellation_ts.date(),
            cache=cache,
        ):
            cancellation_type = "Kündigung in der Probezeit"
            show_warning = False

        return cancellation_type, show_warning


class ConfirmSubscriptionChangesView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        responses={200: str},
        parameters=[
            OpenApiParameter(
                name="confirm_cancellation_ids", type=str, required=True, many=True
            ),
            OpenApiParameter(
                name="confirm_creation_ids", type=str, required=True, many=True
            ),
            OpenApiParameter(
                name="confirm_purchase_ids", type=str, required=True, many=True
            ),
        ],
    )
    @transaction.atomic
    def post(self, request: Request):
        cache = {}

        confirm_cancellation_ids = request.query_params.getlist(
            "confirm_cancellation_ids"
        )
        self.apply_confirmation(
            model=Subscription,
            ids_to_confirm=confirm_cancellation_ids,
            confirmation_field="cancellation_admin_confirmed",
            cache=cache,
        )

        confirm_creation_ids = request.query_params.getlist("confirm_creation_ids")
        self.apply_confirmation(
            model=Subscription,
            ids_to_confirm=confirm_creation_ids,
            confirmation_field="admin_confirmed",
            cache=cache,
        )

        confirm_purchase_ids = request.query_params.getlist("confirm_purchase_ids")
        self.apply_confirmation(
            model=CoopShareTransaction,
            ids_to_confirm=confirm_purchase_ids,
            confirmation_field="admin_confirmed",
            cache=cache,
        )

        return Response("OK", status=status.HTTP_200_OK)

    @staticmethod
    def apply_confirmation(
        model: Type[Model],
        ids_to_confirm: list[str],
        confirmation_field: str,
        cache: dict,
    ):
        subscription_ids_to_confirm = [
            subscription_id.strip()
            for subscription_id in ids_to_confirm
            if subscription_id.strip() != ""
        ]

        subscriptions_to_confirm = model.objects.filter(
            id__in=subscription_ids_to_confirm
        ).filter(**{f"{confirmation_field}__isnull": True})

        ids_not_found = [
            subscription_id
            for subscription_id in subscription_ids_to_confirm
            if subscription_id
            not in [subscription.id for subscription in subscriptions_to_confirm]
        ]

        if len(ids_not_found) > 0:
            raise Http404(
                f"No subscription to confirm with ids {ids_not_found} found, field: {confirmation_field}"
            )

        subscriptions_to_confirm.update(**{confirmation_field: get_now(cache=cache)})
