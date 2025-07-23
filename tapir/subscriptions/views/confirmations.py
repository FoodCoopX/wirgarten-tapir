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
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.subscriptions.serializers import (
    MemberDataToConfirmSerializer,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import (
    Member,
    Subscription,
    CoopShareTransaction,
    WaitingListEntry,
    WaitingListProductWish,
)
from tapir.wirgarten.utils import (
    get_today,
    get_now,
    format_subscription_list_html,
    format_date,
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

        self.send_confirmation_mail_if_necessary(
            confirm_creation_ids=confirm_creation_ids,
            confirm_purchase_ids=confirm_purchase_ids,
        )

        return Response("OK", status=status.HTTP_200_OK)

    @staticmethod
    def apply_confirmation(
        model: Type[Model],
        ids_to_confirm: list[str],
        confirmation_field: str,
        cache: dict,
    ):
        ids_to_confirm = [
            id_to_confirm.strip()
            for id_to_confirm in ids_to_confirm
            if id_to_confirm.strip() != ""
        ]

        objects_to_confirm = model.objects.filter(id__in=ids_to_confirm).filter(
            **{f"{confirmation_field}__isnull": True}
        )

        ids_not_found = [
            object_id
            for object_id in ids_to_confirm
            if object_id not in [obj.id for obj in objects_to_confirm]
        ]

        if len(ids_not_found) > 0:
            raise Http404(
                f"No {model.__name__} to confirm with ids {ids_not_found} found, field: {confirmation_field}"
            )

        objects_to_confirm.update(**{confirmation_field: get_now(cache=cache)})

    @staticmethod
    def send_confirmation_mail_if_necessary(confirm_creation_ids, confirm_purchase_ids):
        if len(confirm_creation_ids) == 0 and len(confirm_purchase_ids) == 0:
            return

        data_by_member = {}

        for subscription in Subscription.objects.filter(
            id__in=confirm_creation_ids
        ).select_related("member"):
            if subscription.member not in data_by_member.keys():
                data_by_member[subscription.member] = {
                    "subscriptions": [],
                    "number_of_coop_shares": 0,
                }

            data_by_member[subscription.member]["subscriptions"].append(subscription)

        for share_transaction in CoopShareTransaction.objects.filter(
            id__in=confirm_purchase_ids
        ).select_related("member"):
            if share_transaction.member not in data_by_member.keys():
                data_by_member[share_transaction.member] = {
                    "subscriptions": [],
                    "number_of_coop_shares": 0,
                }

            data_by_member[share_transaction.member][
                "number_of_coop_shares"
            ] += share_transaction.quantity

        for member, data in data_by_member.items():
            TransactionalTrigger.fire_action(
                TransactionalTriggerData(
                    key=Events.ORDER_CONFIRMED_BY_ADMIN,
                    recipient_id_in_base_queryset=member.id,
                    token_data={
                        "contract_list": format_subscription_list_html(
                            data["subscriptions"]
                        ),
                        "number_of_coop_shares": data["number_of_coop_shares"],
                    },
                ),
            )


class RevokeChangesApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        responses={200: str},
        parameters=[
            OpenApiParameter(
                name="subscription_creation_ids", type=str, required=True, many=True
            ),
            OpenApiParameter(
                name="coop_share_purchase_ids", type=str, required=True, many=True
            ),
        ],
    )
    @transaction.atomic
    def post(self, request: Request):
        cache = {}

        subscriptions = self.delete_objects_or_404(
            ids_to_delete=request.query_params.getlist("subscription_creation_ids"),
            model=Subscription,
        )
        share_transactions = self.delete_objects_or_404(
            ids_to_delete=request.query_params.getlist("coop_share_purchase_ids"),
            model=CoopShareTransaction,
        )

        if len(subscriptions) > 0:
            member = subscriptions[0].member
        else:
            member = share_transactions[0].member

        nb_shares = sum(
            [share_transaction.quantity for share_transaction in share_transactions]
        )

        waiting_list_entry = WaitingListEntry.objects.create(
            member=member,
            comment=f"Erzeugt von einem Widerruf am {format_date(get_now(cache=cache))}",
            number_of_coop_shares=nb_shares,
            first_name=member.first_name,
            last_name=member.last_name,
            phone_number=member.phone_number,
            email=member.email,
            privacy_consent=get_now(cache=cache),
        )

        WaitingListProductWish.objects.bulk_create(
            [
                WaitingListProductWish(
                    waiting_list_entry=waiting_list_entry,
                    product_id=subscription.product_id,
                    quantity=subscription.quantity,
                )
                for subscription in subscriptions
            ],
        )

        return Response("OK")

    @staticmethod
    def delete_objects_or_404(ids_to_delete: list[str], model: Type[Model]):
        ids_to_delete = [
            ids_to_delete.strip()
            for ids_to_delete in ids_to_delete
            if ids_to_delete.strip() != ""
        ]

        objects_to_delete = model.objects.filter(
            id__in=ids_to_delete, admin_confirmed__isnull=True
        ).select_related("member")
        found_ids = [obj.id for obj in objects_to_delete]
        ids_not_found = [
            object_id for object_id in ids_to_delete if object_id not in found_ids
        ]

        if len(ids_not_found) > 0:
            raise Http404(f"Could not find {model.__name__} with ids {ids_not_found}")

        objects = list(objects_to_delete)
        objects_to_delete.delete()
        return objects
