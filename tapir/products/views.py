import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.bestell_wizard.models import ProductTypeAccordionInBestellWizard
from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.config import DELIVERY_DONATION_MODE_DISABLED
from tapir.deliveries.models import CustomCycleScheduledDeliveryWeek
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.products.serializers import (
    ExtendedProductTypeAndConfigSerializer,
    SaveExtendedProductTypeSerializer,
    ProductTypesAndConfigSerializer,
)
from tapir.products.services.product_type_change_applier import ProductTypeChangeApplier
from tapir.products.services.product_type_change_validator import (
    ProductTypeChangeValidator,
)
from tapir.products.services.tax_rate_service import TaxRateService
from tapir.subscriptions.models import NoticePeriod
from tapir.subscriptions.serializers import OrderConfirmationResponseSerializer
from tapir.wirgarten.constants import DeliveryCycleDict
from tapir.wirgarten.models import ProductType, GrowingPeriod, ProductCapacity
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import get_today, legal_status_is_association


class ExtendedProductTypeApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    def __init__(self):
        super().__init__()
        self.cache = {}

    @extend_schema(
        responses={200: ExtendedProductTypeAndConfigSerializer},
        parameters=[
            OpenApiParameter(name="product_type_id", type=str, many=True),
            OpenApiParameter(name="growing_period_id", type=str, many=True),
        ],
    )
    def get(self, request):
        product_type = get_object_or_404(
            ProductType, id=request.query_params.get("product_type_id")
        )
        growing_period = get_object_or_404(
            GrowingPeriod, id=request.query_params.get("growing_period_id")
        )

        data = {
            "show_notice_period": get_parameter_value(
                ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL, cache=self.cache
            ),
            "show_jokers": get_parameter_value(
                ParameterKeys.JOKERS_ENABLED, cache=self.cache
            )
            or get_parameter_value(ParameterKeys.DELIVERY_DONATION_MODE)
            != DELIVERY_DONATION_MODE_DISABLED,
            "show_association_membership": legal_status_is_association(
                cache=self.cache
            ),
            "delivery_cycle_options": DeliveryCycleDict,
            "extended_product_type": self.build_extended_product_type_data(
                product_type=product_type, growing_period=growing_period
            ),
            "can_update_notice_period": settings.DEBUG,
        }

        return Response(ExtendedProductTypeAndConfigSerializer(data).data)

    @extend_schema(
        responses={200: OrderConfirmationResponseSerializer},
        request=SaveExtendedProductTypeSerializer(),
    )
    def post(self, request):
        error_message = None

        try:
            self.update_product_type(request, create_product_type=True)
        except (ValidationError, ValueError) as error:
            error_message = str(error)

        return Response(
            OrderConfirmationResponseSerializer(
                {"order_confirmed": error_message is None, "error": error_message}
            ).data
        )

    @extend_schema(
        responses={200: OrderConfirmationResponseSerializer},
        request=SaveExtendedProductTypeSerializer(),
    )
    def patch(self, request):
        error_message = None

        try:
            self.update_product_type(request, create_product_type=False)
        except (ValidationError, ValueError) as error:
            error_message = str(error)

        return Response(
            OrderConfirmationResponseSerializer(
                {"order_confirmed": error_message is None, "error": error_message}
            ).data
        )

    def update_product_type(self, request, create_product_type: bool):
        serializer = SaveExtendedProductTypeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if create_product_type:
            product_type = ProductType()
        else:
            product_type = get_object_or_404(
                ProductType, id=serializer.validated_data.get("product_type_id")
            )
        growing_period = get_object_or_404(
            GrowingPeriod, id=serializer.validated_data.get("growing_period_id")
        )
        product_capacity = ProductCapacity.objects.filter(
            product_type=product_type, period=growing_period
        ).first()
        if product_capacity is None:
            product_capacity = ProductCapacity(
                product_type=product_type, period=growing_period
            )

        extended_data = serializer.validated_data["extended_product_type"]

        ProductTypeChangeValidator.validate_custom_cycle_changes(
            extended_data=extended_data, product_type=product_type, cache=self.cache
        )

        with transaction.atomic():
            ProductTypeChangeApplier.apply_changes(
                product_type=product_type,
                product_capacity=product_capacity,
                extended_data=extended_data,
            )

    def build_extended_product_type_data(
        self, product_type: ProductType, growing_period: GrowingPeriod
    ):
        data = {
            field: getattr(product_type, field)
            for field in ProductTypeChangeApplier.direct_fields
        }

        product_capacity = get_object_or_404(
            ProductCapacity, product_type=product_type, period=growing_period
        )

        data["capacity"] = product_capacity.capacity

        notice_period = NoticePeriod.objects.filter(
            product_type=product_type,
            growing_period=growing_period,
        ).first()
        data["notice_period_duration"] = None
        data["notice_period_unit"] = None
        if notice_period is not None:
            data["notice_period_duration"] = notice_period.duration
            data["notice_period_unit"] = notice_period.unit

        data["tax_rate"] = TaxRateService.get_tax_rate(
            product_type=product_type,
            at_date=get_today(cache=self.cache),
            cache=self.cache,
        )
        data["tax_rate_change_date"] = growing_period.end_date + datetime.timedelta(
            days=1
        )

        data["accordions_in_bestell_wizard"] = (
            ProductTypeAccordionInBestellWizard.objects.filter(
                product_type=product_type
            )
        )

        custom_cycle_delivery_weeks = {}
        data["custom_cycle_delivery_weeks"] = custom_cycle_delivery_weeks
        for scheduled_week in CustomCycleScheduledDeliveryWeek.objects.filter(
            product_type=product_type
        ).order_by("calendar_week"):
            if (
                scheduled_week.growing_period_id
                not in custom_cycle_delivery_weeks.keys()
            ):
                custom_cycle_delivery_weeks[scheduled_week.growing_period_id] = []
            custom_cycle_delivery_weeks[scheduled_week.growing_period_id].append(
                scheduled_week.calendar_week
            )

        return data


class ProductTypesWithoutCapacityAndConfigApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        responses={200: ProductTypesAndConfigSerializer},
        parameters=[
            OpenApiParameter(name="growing_period_id", type=str, many=True),
        ],
    )
    def get(self, request):
        cache = {}
        growing_period = get_object_or_404(
            GrowingPeriod, id=request.query_params.get("growing_period_id")
        )

        types_without_capacity = ProductType.objects.exclude(
            id__in=ProductCapacity.objects.filter(period=growing_period).values_list(
                "product_type_id", flat=True
            )
        )

        data = {
            "show_notice_period": get_parameter_value(
                ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL, cache=cache
            ),
            "show_jokers": get_parameter_value(
                ParameterKeys.JOKERS_ENABLED, cache=cache
            ),
            "can_update_notice_period": settings.DEBUG,
            "show_association_membership": legal_status_is_association(cache=cache),
            "delivery_cycle_options": DeliveryCycleDict,
            "product_types_without_capacity": types_without_capacity,
        }

        return Response(ProductTypesAndConfigSerializer(data).data)
