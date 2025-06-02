from typing import Dict

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.configuration.parameter import get_parameter_value
from tapir.coop.services.membership_cancellation_manager import (
    MembershipCancellationManager,
)
from tapir.deliveries.serializers import ProductSerializer
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.pickup_locations.services.basket_size_capacities_service import (
    BasketSizeCapacitiesService,
)
from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.subscriptions.serializers import (
    CancellationDataSerializer,
    CancelSubscriptionsViewResponseSerializer,
    ExtendedProductSerializer,
    CancelledSubscriptionSerializer,
    ProductTypesAndNumberOfCancelledSubscriptionsToConfirmViewResponseSerializer,
    MemberDataToConfirmSerializer,
)
from tapir.subscriptions.services.base_product_type_service import (
    BaseProductTypeService,
)
from tapir.subscriptions.services.product_updater import ProductUpdater
from tapir.subscriptions.services.subscription_cancellation_manager import (
    SubscriptionCancellationManager,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import (
    Member,
    Product,
    Subscription,
    PickupLocation,
    ProductType,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import (
    get_active_and_future_subscriptions,
    get_product_price,
    get_current_growing_period,
)
from tapir.wirgarten.tapirmail import Events
from tapir.wirgarten.utils import (
    check_permission_or_self,
    format_date,
    get_today,
    get_now,
)


class GetCancellationDataView(APIView):
    @extend_schema(
        responses={200: CancellationDataSerializer()},
        parameters=[
            OpenApiParameter(name="member_id", type=str),
        ],
    )
    def get(self, request):
        member = get_object_or_404(Member, id=request.query_params.get("member_id"))
        check_permission_or_self(member.id, request)

        cache = {}
        data = {
            "can_cancel_coop_membership": MembershipCancellationManager.can_member_cancel_coop_membership(
                member, cache=cache
            ),
            "subscribed_products": self.build_subscribed_products_data(
                member, cache=cache
            ),
            "legal_status": get_parameter_value(
                ParameterKeys.ORGANISATION_LEGAL_STATUS, cache=cache
            ),
        }

        return Response(
            CancellationDataSerializer(data).data,
            status=status.HTTP_200_OK,
        )

    @classmethod
    def build_subscribed_products_data(cls, member, cache: Dict):
        return [
            {
                "product": subscribed_product,
                "is_in_trial": TrialPeriodManager.is_product_in_trial(
                    subscribed_product, member, cache=cache
                ),
                "cancellation_date": SubscriptionCancellationManager.get_earliest_possible_cancellation_date(
                    product=subscribed_product, member=member, cache=cache
                ),
            }
            for subscribed_product in cls.get_subscribed_products(member, cache=cache)
        ]

    @classmethod
    def get_subscribed_products(cls, member, cache: Dict):
        return {
            subscription.product
            for subscription in get_active_and_future_subscriptions(cache=cache).filter(
                member=member, cancellation_ts__isnull=True
            )
        }


class CancelSubscriptionsView(APIView):
    def __init__(self):
        super().__init__()
        self.cache = {}

    @extend_schema(
        responses={200: CancelSubscriptionsViewResponseSerializer()},
        parameters=[
            OpenApiParameter(name="member_id", type=str),
            OpenApiParameter(name="product_ids", type=str, many=True),
            OpenApiParameter(name="cancel_coop_membership", type=bool),
        ],
    )
    def post(self, request):
        member = get_object_or_404(Member, id=request.query_params.get("member_id"))
        check_permission_or_self(member.id, request)

        product_ids = request.query_params.getlist("product_ids")
        products_selected_for_cancellation = {
            get_object_or_404(Product, id=product_id)
            for product_id in product_ids
            if product_id != ""
        }
        subscribed_products = GetCancellationDataView.get_subscribed_products(
            member, cache=self.cache
        )

        cancel_coop_membership = (
            request.query_params.get("cancel_coop_membership") == "true"
        )
        if (
            cancel_coop_membership
            and not MembershipCancellationManager.can_member_cancel_coop_membership(
                member, cache=self.cache
            )
        ):
            return self.build_response(
                False,
                [
                    "Es ist nur möglich die Beitrittserklärung zu widerrufen wenn du noch nicht Mitglied bist."
                ],
            )

        if (
            cancel_coop_membership
            and products_selected_for_cancellation != subscribed_products
        ):
            return self.build_response(
                False,
                [
                    "Es ist nur möglich die Beitrittserklärung zu widerrufen wenn alle Verträge auch kündigst."
                ],
            )

        if (
            not get_parameter_value(
                ParameterKeys.SUBSCRIPTION_ADDITIONAL_PRODUCT_ALLOWED_WITHOUT_BASE_PRODUCT,
                cache=self.cache,
            )
            and self.is_at_least_one_additional_product_not_selected(
                subscribed_products,
                products_selected_for_cancellation,
                cache=self.cache,
            )
            and self.are_all_base_products_selected(
                subscribed_products,
                products_selected_for_cancellation,
                cache=self.cache,
            )
        ):
            return self.build_response(
                False,
                ["Du kannst keine Zusatzabos beziehen wenn du das Basis-Abo kündigst."],
            )

        with transaction.atomic():
            for product in products_selected_for_cancellation:
                cancelled_subscriptions = (
                    SubscriptionCancellationManager.cancel_subscriptions(
                        product, member, cache=self.cache
                    )
                )
                if len(cancelled_subscriptions) > 0:
                    TransactionalTrigger.fire_action(
                        TransactionalTriggerData(
                            key=Events.CONTRACT_CANCELLED,
                            recipient_id_in_base_queryset=member.id,
                            token_data={
                                "contract_list": cancelled_subscriptions,
                                "contract_end_date": format_date(
                                    cancelled_subscriptions[0].end_date
                                ),
                            },
                        ),
                    )

            if cancel_coop_membership:
                MembershipCancellationManager.cancel_coop_membership(
                    member, cache=self.cache
                )

        return self.build_response(subscriptions_cancelled=True, errors=[])

    @staticmethod
    def are_all_base_products_selected(
        subscribed_products: set[Product],
        products_selected_for_cancellation: set[Product],
        cache: Dict,
    ):
        base_product_type = BaseProductTypeService.get_base_product_type(cache=cache)
        for subscribed_product in subscribed_products:
            if (
                subscribed_product.type_id == base_product_type.id
                and subscribed_product not in products_selected_for_cancellation
            ):
                return False

        return True

    @staticmethod
    def is_at_least_one_additional_product_not_selected(
        subscribed_products: set[Product],
        products_selected_for_cancellation: set[Product],
        cache: Dict,
    ):
        base_product_type = BaseProductTypeService.get_base_product_type(cache=cache)
        for subscribed_product in subscribed_products:
            if (
                subscribed_product.type_id != base_product_type.id
                and subscribed_product not in products_selected_for_cancellation
            ):
                return True

        return False

    @staticmethod
    def build_response(subscriptions_cancelled: bool, errors: list[str]):
        return Response(
            CancelSubscriptionsViewResponseSerializer(
                {"subscriptions_cancelled": subscriptions_cancelled, "errors": errors}
            ).data,
            status=status.HTTP_200_OK,
        )


class ExtendedProductView(APIView):
    @extend_schema(
        responses={200: ExtendedProductSerializer()},
        parameters=[OpenApiParameter(name="product_id", type=str)],
    )
    def get(self, request):
        if not request.user.has_perm(Permission.Products.VIEW):
            return Response(status=status.HTTP_403_FORBIDDEN)

        product = get_object_or_404(Product, id=request.query_params.get("product_id"))

        data = {
            attribute: getattr(product, attribute)
            for attribute in ["id", "name", "deleted", "base"]
        }

        cache = {}
        product_price_object = get_product_price(product, cache=cache)
        if product_price_object:
            data.update(
                {"price": product_price_object.price, "size": product_price_object.size}
            )
        else:
            data.update({"price": 0, "size": 0})

        data["basket_size_equivalences"] = [
            {"basket_size_name": size_name, "quantity": quantity}
            for size_name, quantity in BasketSizeCapacitiesService.get_basket_size_equivalences_for_product(
                product
            ).items()
        ]

        data["picking_mode"] = get_parameter_value(
            ParameterKeys.PICKING_MODE, cache=cache
        )

        return Response(
            ExtendedProductSerializer(data).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        responses={200: str},
        request=ExtendedProductSerializer(),
    )
    def patch(self, request):
        if not request.user.has_perm(Permission.Products.MANAGE):
            return Response(status=status.HTTP_403_FORBIDDEN)

        request_serializer = ExtendedProductSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        product = get_object_or_404(Product, id=request_serializer.validated_data["id"])

        with transaction.atomic():
            ProductUpdater.update_product(product, request_serializer)

        return Response(
            "OK",
            status=status.HTTP_200_OK,
        )


class CancelledSubscriptionsApiView(APIView):
    serializer_class = CancelledSubscriptionSerializer
    pagination_class = LimitOffsetPagination
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    def __init__(self):
        super().__init__()
        self.cache = {}

    @extend_schema(
        responses={200: CancelledSubscriptionSerializer(many=True)},
        parameters=[
            OpenApiParameter(name="limit", type=int, required=True),
            OpenApiParameter(name="offset", type=int, required=True),
            OpenApiParameter(name="product_type_id", type=str, required=True),
        ],
    )
    @action(detail=False)
    def get(self, request: Request):
        pagination = self.pagination_class()
        subscriptions = self.get_unconfirmed_cancelled_subscriptions(
            product_type_id=request.query_params.get("product_type_id")
        ).order_by("cancellation_ts")
        subscriptions = pagination.paginate_queryset(subscriptions, request)
        members = Member.objects.filter(
            id__in=[subscription.member_id for subscription in subscriptions]
        ).distinct()
        members = MemberPickupLocationService.annotate_member_queryset_with_pickup_location_at_date(
            members, reference_date=get_today(cache=self.cache)
        )
        pickup_locations = PickupLocation.objects.filter(
            id__in=[
                getattr(
                    member,
                    MemberPickupLocationService.ANNOTATION_CURRENT_PICKUP_LOCATION_ID,
                )
                for member in members
            ]
        )

        members_by_id = {member.id: member for member in members}
        pickup_locations_by_id = {
            pickup_location.id: pickup_location for pickup_location in pickup_locations
        }

        subscription_datas = []
        for subscription in subscriptions:
            member = members_by_id[subscription.member_id]
            pickup_location = pickup_locations_by_id[
                getattr(
                    member,
                    MemberPickupLocationService.ANNOTATION_CURRENT_PICKUP_LOCATION_ID,
                )
            ]
            cancellation_type, show_warning = self.get_cancellation_type(
                subscription, cache=self.cache
            )

            subscription_datas.append(
                {
                    "subscription": subscription,
                    "member": member,
                    "pickup_location": pickup_location,
                    "cancellation_type": cancellation_type,
                    "show_warning": show_warning,
                }
            )

        serializer = CancelledSubscriptionSerializer(
            subscription_datas,
            many=True,
        )
        return pagination.get_paginated_response(serializer.data)

    @classmethod
    def get_unconfirmed_cancelled_subscriptions(cls, product_type_id):
        return Subscription.objects.filter(
            cancellation_ts__isnull=False,
            cancellation_admin_confirmed__isnull=True,
            product__type_id=product_type_id,
        )

    @classmethod
    def get_cancellation_type(cls, subscription: Subscription, cache: dict):
        cancellation_type = "Reguläre Kündigung"
        show_warning = False
        if (
            get_current_growing_period(subscription.end_date, cache=cache).end_date
            > subscription.end_date
        ):
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


class ProductTypesAndNumberOfCancelledSubscriptionsToConfirmView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        responses={
            200: ProductTypesAndNumberOfCancelledSubscriptionsToConfirmViewResponseSerializer()
        },
    )
    def get(self, request: Request):
        product_types = ProductType.objects.all()
        number_of_subscriptions = [
            CancelledSubscriptionsApiView.get_unconfirmed_cancelled_subscriptions(
                product_type.id
            ).count()
            for product_type in product_types
        ]
        return Response(
            ProductTypesAndNumberOfCancelledSubscriptionsToConfirmViewResponseSerializer(
                {
                    "product_types": list(product_types),
                    "number_of_subscriptions": number_of_subscriptions,
                }
            ).data,
            status=status.HTTP_200_OK,
        )


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]
    queryset = Product.objects.select_related("type")
    serializer_class = ProductSerializer


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
            cancellation_type, cancellation_shows_warning = (
                CancelledSubscriptionsApiView.get_cancellation_type(
                    cancellation, cache=cache
                )
            )
            show_warning = show_warning or cancellation_shows_warning
            cancellation_types.append(cancellation_type)

        return {
            "member": member,
            "pickup_location": pickup_location,
            "subscription_cancellations": cancellations,
            "cancellation_types": cancellation_types,
            "show_warning": show_warning,
            "subscription_creations": creations,
            "subscription_changes": changes,
            "share_transactions": [],
        }


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
        ],
    )
    @transaction.atomic
    def post(self, request: Request):
        cache = {}

        confirm_cancellation_ids = request.query_params.getlist(
            "confirm_cancellation_ids"
        )
        self.apply_confirmation(
            subscription_ids_to_confirm=confirm_cancellation_ids,
            confirmation_field="cancellation_admin_confirmed",
            cache=cache,
        )

        confirm_creation_ids = request.query_params.getlist("confirm_creation_ids")
        self.apply_confirmation(
            subscription_ids_to_confirm=confirm_creation_ids,
            confirmation_field="admin_confirmed",
            cache=cache,
        )

        return Response("OK", status=status.HTTP_200_OK)

    @staticmethod
    def apply_confirmation(
        subscription_ids_to_confirm: list[str],
        confirmation_field: str,
        cache: dict,
    ):
        subscription_ids_to_confirm = [
            id.strip() for id in subscription_ids_to_confirm if id.strip() is not ""
        ]

        subscriptions_to_confirm = Subscription.objects.filter(
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
