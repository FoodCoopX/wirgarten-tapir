from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status, permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.services.subscription_price_type_decider import (
    SubscriptionPricingStrategyDecider,
)
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.log.util import freeze_for_log
from tapir.pickup_locations.services.basket_size_capacities_service import (
    BasketSizeCapacitiesService,
)
from tapir.products.services.product_name_validator import ProductNameValidator
from tapir.products.serializers import (
    ExtendedProductSerializer,
    PublicProductTypeSerializer,
    ProductSerializer,
)
from tapir.solidarity_contribution.services.solidarity_validator import (
    SolidarityValidator,
)
from tapir.subscriptions.models import (
    SubscriptionPriceChangedLogEntry,
    SubscriptionTrialChangedLogEntry,
)
from tapir.subscriptions.serializers import (
    OrderConfirmationResponseSerializer,
    SubscriptionDateChangeRequestSerializer,
    ConvertWeekToDateForSubscriptionChangeRequestSerializer,
    ConvertWeekToDateForSubscriptionChangeResponseSerializer,
    SubscriptionPriceOverrideChangeRequestSerializer,
    SubscriptionDetailsSerializer,
    SubscriptionTrialChangeRequestSerializer,
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
from tapir.wirgarten.utils import legal_status_is_cooperative


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
                "hidden_in_bestell_wizard",
                "solidarity_choices",
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

        data["show_min_coop_shares"] = legal_status_is_cooperative(cache=cache)

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

        try:
            SolidarityValidator.validate_solidarity_dropdown_values(
                request_serializer.validated_data["solidarity_choices"]
            )
            ProductNameValidator.validate_name_is_unique(
                product_name=request_serializer.validated_data["name"],
                product_id=request_serializer.validated_data["id"],
                cache={},
            )
        except ValidationError as error:
            return Response(data=error.message, status=status.HTTP_400_BAD_REQUEST)

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
    queryset = Subscription.objects.select_related("product", "period")
    serializer_class = SubscriptionDetailsSerializer

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cache = {}

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "cache": self.cache}


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

        action = serializer.validated_data["action"]
        update_other_contracts = serializer.validated_data["update_other_contracts"]
        date = serializer.validated_data.get("date")

        try:
            SubscriptionDateChangeApplier.validate(
                subscription=subscription,
                action=action,
                date=date,
                update_other_contracts=update_other_contracts,
                cache=self.cache,
            )
        except ValidationError as error:
            return Response(
                OrderConfirmationResponseSerializer(
                    {"order_confirmed": False, "error": error.message}
                ).data
            )

        with transaction.atomic():
            SubscriptionDateChangeApplier.apply_changes(
                actor=request.user,
                subscription=subscription,
                action=action,
                date=date,
                update_other_contracts=update_other_contracts,
                cache=self.cache,
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


class ConvertWeekToDateForSubscriptionChangeApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        responses={200: ConvertWeekToDateForSubscriptionChangeResponseSerializer},
        parameters=[ConvertWeekToDateForSubscriptionChangeRequestSerializer],
    )
    def get(self, request):
        serializer = ConvertWeekToDateForSubscriptionChangeRequestSerializer(
            data=request.query_params
        )
        serializer.is_valid(raise_exception=True)
        growing_period = get_object_or_404(
            Subscription, id=serializer.validated_data["subscription_id"]
        ).period

        try:
            date = SubscriptionChangeWeekToDateConverter.get_date_from_calendar_week(
                week=serializer.validated_data["week"],
                growing_period=growing_period,
                boundary=serializer.validated_data["boundary"],
            )
        except ValidationError as error:
            return Response(
                ConvertWeekToDateForSubscriptionChangeResponseSerializer(
                    {"date": None, "error": error.message}
                ).data
            )

        return Response(
            ConvertWeekToDateForSubscriptionChangeResponseSerializer(
                {"date": date, "error": None}
            ).data
        )


class SubscriptionTrialChangeApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        responses={200: OrderConfirmationResponseSerializer},
        request=SubscriptionTrialChangeRequestSerializer,
    )
    def post(self, request):
        serializer = SubscriptionTrialChangeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        subscription = get_object_or_404(
            Subscription, id=serializer.validated_data["subscription_id"]
        )

        trial_disabled = serializer.validated_data["trial_disabled"]
        trial_end_date_override = serializer.validated_data.get(
            "trial_end_date_override"
        )
        cache = {}

        if not trial_disabled and not get_parameter_value(
            ParameterKeys.TRIAL_PERIOD_ENABLED, cache=cache
        ):
            return Response(
                OrderConfirmationResponseSerializer(
                    {
                        "order_confirmed": False,
                        "error": "Probezeit ist global deaktiviert",
                    }
                ).data
            )

        if (
            not trial_disabled
            and trial_end_date_override is not None
            and trial_end_date_override.weekday() != 6
        ):
            return Response(
                OrderConfirmationResponseSerializer(
                    {
                        "order_confirmed": False,
                        "error": "Das Probezeit-Enddatum muss ein Sonntag sein",
                    }
                ).data
            )

        if trial_disabled:
            trial_end_date_override = None

        trial_disabled_before = subscription.trial_disabled
        trial_end_date_override_before = subscription.trial_end_date_override

        with transaction.atomic():
            subscription.trial_disabled = trial_disabled
            subscription.trial_end_date_override = trial_end_date_override
            subscription.save()

            SubscriptionTrialChangedLogEntry().populate_trial_change(
                subscription=subscription,
                trial_disabled_before=trial_disabled_before,
                trial_end_date_override_before=trial_end_date_override_before,
                actor=request.user,
                user=subscription.member,
            ).save()

        return Response(
            OrderConfirmationResponseSerializer(
                {"order_confirmed": True, "error": None}
            ).data
        )
