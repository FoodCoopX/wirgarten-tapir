from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status, permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.serializers import (
    SubscriptionSerializer,
)
from tapir.deliveries.services.subscription_price_type_decider import (
    SubscriptionPricingStrategyDecider,
)
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.log.util import freeze_for_log
from tapir.pickup_locations.services.basket_size_capacities_service import (
    BasketSizeCapacitiesService,
)
from tapir.products.serializers import (
    ExtendedProductSerializer,
    PublicProductTypeSerializer,
    ProductSerializer,
)
from tapir.subscriptions.models import (
    SubscriptionPriceChangedLogEntry,
)
from tapir.subscriptions.serializers import (
    OrderConfirmationResponseSerializer,
    SubscriptionDateChangeRequestSerializer,
    ConvertWeekToDateForSubscriptionChangesResponseSerializer,
    SubscriptionPriceOverrideChangeRequestSerializer,
)
from tapir.subscriptions.services.product_updater import ProductUpdater
from tapir.subscriptions.services.subscription_change_week_to_date_converter import (
    SubscriptionChangeWeekToDateConverter,
)
from tapir.subscriptions.services.subscription_date_change_applier import (
    SubscriptionDateChangeApplier,
)
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import (
    Product,
    ProductType,
    Subscription,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import (
    get_product_price,
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
            for attribute in [
                "id",
                "name",
                "deleted",
                "base",
                "description_in_bestellwizard",
                "url_of_image_in_bestellwizard",
                "capacity",
                "min_coop_shares",
            ]
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
                product, cache=cache
            ).items()
        ]

        data["picking_mode"] = get_parameter_value(
            ParameterKeys.PICKING_MODE, cache=cache
        )

        data["price_per_delivery"] = (
            SubscriptionPricingStrategyDecider.is_price_by_delivery(
                product.type.delivery_cycle
            )
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


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]
    queryset = Product.objects.select_related("type")
    serializer_class = ProductSerializer


class PublicProductTypeViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = []
    queryset = ProductType.objects.all()
    serializer_class = PublicProductTypeSerializer


class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer


class SubscriptionDateChangeApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    def __init__(self):
        super().__init__()
        self.cache = {}

    @extend_schema(
        responses={200: OrderConfirmationResponseSerializer},
        request=SubscriptionDateChangeRequestSerializer,
    )
    def post(self, request):
        serializer = SubscriptionDateChangeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        subscription = get_object_or_404(
            Subscription, id=serializer.validated_data["subscription_id"]
        )

        if serializer.validated_data["start_date_is_on_period_start"]:
            start_date = subscription.period.start_date
        else:
            start_week = serializer.validated_data["start_week"]
            start_date = (
                SubscriptionChangeWeekToDateConverter.get_date_from_calendar_week(
                    week=start_week,
                    growing_period=subscription.period,
                    boundary="start",
                )
            )

        if serializer.validated_data["end_date_is_on_period_end"]:
            end_date = subscription.period.end_date
        else:
            end_week = serializer.validated_data["end_week"]
            end_date = (
                SubscriptionChangeWeekToDateConverter.get_date_from_calendar_week(
                    week=end_week, growing_period=subscription.period, boundary="end"
                )
            )

        try:
            SubscriptionDateChangeApplier.validate_dates(
                subscription=subscription,
                start_date=start_date,
                end_date=end_date,
                cache=self.cache,
            )

            with transaction.atomic():
                SubscriptionDateChangeApplier.apply_changes(
                    actor=request.user,
                    start_date=start_date,
                    end_date=end_date,
                    subscription=subscription,
                    update_end_date_of_other_contracts=serializer.validated_data[
                        "update_end_date_of_other_contracts"
                    ],
                    cache=self.cache,
                )
        except ValidationError as error:
            return Response(
                OrderConfirmationResponseSerializer(
                    {"order_confirmed": False, "error": error.message}
                ).data
            )

        return Response(
            OrderConfirmationResponseSerializer(
                {"order_confirmed": True, "error": None}
            ).data
        )


class SubscriptionPriceOverrideApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        responses={200: OrderConfirmationResponseSerializer},
        request=SubscriptionPriceOverrideChangeRequestSerializer,
    )
    def post(self, request):
        serializer = SubscriptionPriceOverrideChangeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        subscription = get_object_or_404(
            Subscription, id=serializer.validated_data["subscription_id"]
        )

        price_override = serializer.validated_data["price_override"]
        if price_override is not None and price_override < 0:
            return Response(
                OrderConfirmationResponseSerializer(
                    {
                        "order_confirmed": False,
                        "error": "Der Preis darf nicht negativ sein",
                    }
                ).data
            )

        subscription_before = freeze_for_log(subscription)
        price_before = subscription.price_override
        subscription.price_override = price_override

        with transaction.atomic():
            subscription.save()

            SubscriptionPriceChangedLogEntry().populate_price_change(
                subscription_frozen_before_changes=subscription_before,
                subscription=subscription,
                user=subscription.member,
                actor=request.user,
                price_before=price_before,
            ).save()

        return Response(
            OrderConfirmationResponseSerializer(
                {"order_confirmed": True, "error": None}
            ).data
        )


class ConvertWeeksToDateForSubscriptionChangesApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        responses={200: ConvertWeekToDateForSubscriptionChangesResponseSerializer},
        parameters=[
            OpenApiParameter(name="start_week", type=int),
            OpenApiParameter(name="end_week", type=int),
            OpenApiParameter(name="subscription_id", type=str),
        ],
    )
    def get(self, request):
        start_week = int(request.query_params.get("start_week"))
        end_week = int(request.query_params.get("end_week"))
        growing_period = get_object_or_404(
            Subscription, id=request.query_params.get("subscription_id")
        ).period

        start_date = SubscriptionChangeWeekToDateConverter.get_date_from_calendar_week(
            week=start_week,
            growing_period=growing_period,
            boundary="start",
        )

        end_date = SubscriptionChangeWeekToDateConverter.get_date_from_calendar_week(
            week=end_week,
            growing_period=growing_period,
            boundary="end",
        )

        return Response(
            ConvertWeekToDateForSubscriptionChangesResponseSerializer(
                {"start_date": start_date, "end_date": end_date}
            ).data
        )
