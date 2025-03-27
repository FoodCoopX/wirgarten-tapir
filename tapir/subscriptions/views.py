from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.configuration.parameter import get_parameter_value
from tapir.coop.services.membership_cancellation_manager import (
    MembershipCancellationManager,
)
from tapir.pickup_locations.services.basket_size_capacities_service import (
    BasketSizeCapacitiesService,
)
from tapir.subscriptions.serializers import (
    CancellationDataSerializer,
    CancelSubscriptionsViewResponseSerializer,
    ExtendedProductSerializer,
)
from tapir.subscriptions.services.product_updater import ProductUpdater
from tapir.subscriptions.services.subscription_cancellation_manager import (
    SubscriptionCancellationManager,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import Member, Product
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.products import (
    get_active_and_future_subscriptions,
    get_product_price,
)
from tapir.wirgarten.utils import check_permission_or_self


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

        data = {
            "can_cancel_coop_membership": MembershipCancellationManager.can_member_cancel_coop_membership(
                member
            ),
            "subscribed_products": self.build_subscribed_products_data(member),
        }

        return Response(
            CancellationDataSerializer(data).data,
            status=status.HTTP_200_OK,
        )

    @classmethod
    def build_subscribed_products_data(cls, member):
        return [
            {
                "product": subscribed_product,
                "is_in_trial": TrialPeriodManager.is_product_in_trial(
                    subscribed_product, member
                ),
                "cancellation_date": SubscriptionCancellationManager.get_earliest_possible_cancellation_date(
                    product=subscribed_product, member=member
                ),
            }
            for subscribed_product in cls.get_subscribed_products(member)
        ]

    @classmethod
    def get_subscribed_products(cls, member):
        return {
            subscription.product
            for subscription in get_active_and_future_subscriptions().filter(
                member=member, cancellation_ts__isnull=True
            )
        }


class CancelSubscriptionsView(APIView):
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
        subscribed_products = GetCancellationDataView.get_subscribed_products(member)
        cancel_coop_membership = (
            request.query_params.get("cancel_coop_membership") == "true"
        )

        if (
            cancel_coop_membership
            and not MembershipCancellationManager.can_member_cancel_coop_membership(
                member
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

        if self.is_at_least_one_additional_product_not_selected(
            subscribed_products, products_selected_for_cancellation
        ) and self.are_all_base_products_selected(
            subscribed_products, products_selected_for_cancellation
        ):
            return self.build_response(
                False,
                [
                    _(
                        "Du kannst keine Zusatzabos beziehen wenn du das Basisabo kündigst."
                    )
                ],
            )

        with transaction.atomic():
            for product in products_selected_for_cancellation:
                SubscriptionCancellationManager.cancel_subscriptions(product, member)

            if cancel_coop_membership:
                MembershipCancellationManager.cancel_coop_membership(member)

        return Response("OK", status=status.HTTP_200_OK)

    @staticmethod
    def are_all_base_products_selected(
        subscribed_products: set[Product],
        products_selected_for_cancellation: set[Product],
    ):
        base_product_type_id = get_parameter_value(Parameter.COOP_BASE_PRODUCT_TYPE)
        for subscribed_product in subscribed_products:
            if (
                subscribed_product.type_id == base_product_type_id
                and subscribed_product not in products_selected_for_cancellation
            ):
                return False

        return True

    @staticmethod
    def is_at_least_one_additional_product_not_selected(
        subscribed_products: set[Product],
        products_selected_for_cancellation: set[Product],
    ):
        base_product_type_id = get_parameter_value(Parameter.COOP_BASE_PRODUCT_TYPE)
        for subscribed_product in subscribed_products:
            if (
                subscribed_product.type_id != base_product_type_id
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

        product_price_object = get_product_price(product)
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

        data["picking_mode"] = get_parameter_value(Parameter.PICKING_MODE)

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
