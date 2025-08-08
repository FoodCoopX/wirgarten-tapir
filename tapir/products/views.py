import datetime

from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.configuration.parameter import get_parameter_value
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.products.serializers import (
    ExtendedProductTypeAndConfigSerializer,
    SaveExtendedProductTypeSerializer,
    ProductTypesAndConfigSerializer,
)
from tapir.products.services.TaxRateService import TaxRateService
from tapir.subscriptions.models import NoticePeriod
from tapir.subscriptions.services.notice_period_manager import NoticePeriodManager
from tapir.wirgarten.constants import DeliveryCycleDict
from tapir.wirgarten.models import ProductType, GrowingPeriod, ProductCapacity
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import get_today, legal_status_is_association


class ExtendedProductTypeApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    direct_fields = [
        "name",
        "description_bestellwizard_short",
        "description_bestellwizard_long",
        "order_in_bestellwizard",
        "icon_link",
        "contract_link",
        "delivery_cycle",
        "single_subscription_only",
        "is_affected_by_jokers",
        "must_be_subscribed_to",
        "is_association_membership",
    ]

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
            ),
            "show_association_membership": legal_status_is_association(
                cache=self.cache
            ),
            "delivery_cycle_options": DeliveryCycleDict,
            "extended_product_type": self.build_extended_product_type_data(
                product_type=product_type, growing_period=growing_period
            ),
        }

        return Response(ExtendedProductTypeAndConfigSerializer(data).data)

    @extend_schema(
        responses={200: str},
        request=SaveExtendedProductTypeSerializer(),
    )
    def post(self, request):
        self.update_product_type(request, create_product_type=True)
        return Response("OK")

    @extend_schema(
        responses={200: str},
        request=SaveExtendedProductTypeSerializer(),
    )
    def patch(self, request):
        self.update_product_type(request, create_product_type=False)
        return Response("OK")

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
        with transaction.atomic():
            for field in self.direct_fields:
                setattr(product_type, field, extended_data[field])

            product_type.name = extended_data["name"]
            product_type.icon_link = extended_data["icon_link"]
            product_type.save()

            product_capacity.capacity = extended_data["capacity"]
            product_capacity.save()

            NoticePeriodManager.set_notice_period_duration(
                product_type=product_capacity.product_type,
                growing_period=product_capacity.period,
                notice_period_duration=extended_data.get("notice_period", None),
            )

            TaxRateService.create_or_update_default_tax_rate(
                product_type_id=product_type.id,
                tax_rate=extended_data["tax_rate"],
                tax_rate_change_date=extended_data["tax_rate_change_date"],
            )

    def build_extended_product_type_data(
        self, product_type: ProductType, growing_period: GrowingPeriod
    ):
        data = {field: getattr(product_type, field) for field in self.direct_fields}

        product_capacity = get_object_or_404(
            ProductCapacity, product_type=product_type, period=growing_period
        )

        data["capacity"] = product_capacity.capacity

        notice_period = NoticePeriod.objects.filter(
            product_type=product_type,
            growing_period=growing_period,
        ).first()
        if notice_period is None:
            data["notice_period"] = None
        else:
            data["notice_period"] = notice_period.duration

        data["tax_rate"] = TaxRateService.get_tax_rate(
            product_type=product_type,
            at_date=get_today(cache=self.cache),
            cache=self.cache,
        )
        data["tax_rate_change_date"] = growing_period.end_date + datetime.timedelta(
            days=1
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
            "show_association_membership": legal_status_is_association(cache=cache),
            "delivery_cycle_options": DeliveryCycleDict,
            "product_types_without_capacity": types_without_capacity,
        }

        return Response(ProductTypesAndConfigSerializer(data).data)
