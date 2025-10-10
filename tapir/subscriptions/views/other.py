import datetime

from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from rest_framework import status, permissions, viewsets, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.serializers import ProductSerializer, SubscriptionSerializer
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.log.util import freeze_for_log
from tapir.payments.services.member_credit_creator import MemberCreditCreator
from tapir.pickup_locations.services.basket_size_capacities_service import (
    BasketSizeCapacitiesService,
)
from tapir.subscriptions.models import SubscriptionChangedLogEntry
from tapir.subscriptions.serializers import (
    ExtendedProductSerializer,
    PublicProductTypeSerializer,
    OrderConfirmationResponseSerializer,
)
from tapir.subscriptions.services.product_updater import ProductUpdater
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import (
    Product,
    ProductType,
    Subscription,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import OPTIONS_WEEKDAYS
from tapir.wirgarten.service.products import (
    get_product_price,
)
from tapir.wirgarten.utils import get_now, get_today


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
        request=inline_serializer(
            name="subscription_date_change",
            fields={
                "start_date": serializers.DateField(),
                "end_date": serializers.DateField(),
                "subscription_id": serializers.CharField(),
            },
        ),
    )
    def post(self, request):
        subscription_id = request.data.get("subscription_id")
        subscription = get_object_or_404(Subscription, id=subscription_id)

        start_date = datetime.datetime.strptime(
            request.data.get("start_date"), "%Y-%m-%d"
        ).date()
        end_date = datetime.datetime.strptime(
            request.data.get("end_date"), "%Y-%m-%d"
        ).date()

        try:
            self.validate_dates(
                subscription=subscription,
                start_date=start_date,
                end_date=end_date,
                cache=self.cache,
            )
        except ValidationError as error:
            return Response(
                OrderConfirmationResponseSerializer(
                    {"order_confirmed": False, "error": error.message}
                ).data
            )

        with transaction.atomic():
            subscription_before = freeze_for_log(subscription)
            subscription.start_date = start_date
            if end_date != subscription.end_date:
                subscription.cancellation_ts = get_now(cache=self.cache)
                Subscription.objects.filter(
                    member_id=subscription.member_id,
                    product_id=subscription.product_id,
                    end_date__gt=end_date,
                ).delete()

            subscription.end_date = end_date
            subscription.save()

            MemberCreditCreator.create_member_credit_if_necessary(
                member=subscription.member,
                product_type=subscription.product.type,
                reference_date=get_today(cache=self.cache),
                comment="Vertragsdaten vom Admin durch der Vertragsliste angepasst.",
                cache=self.cache,
                actor=request.user,
            )

            SubscriptionChangedLogEntry().populate(
                old_frozen=subscription_before,
                new_model=subscription,
                user=subscription.member,
                actor=request.user,
            ).save()

        return Response(
            OrderConfirmationResponseSerializer(
                {"order_confirmed": True, "error": None}
            ).data
        )

    @classmethod
    def validate_dates(
        cls,
        subscription: Subscription,
        start_date: datetime.date,
        end_date: datetime.date,
        cache: dict,
    ):
        if subscription.start_date == start_date and subscription.end_date == end_date:
            raise ValidationError("Keine Änderungen")

        if end_date != subscription.end_date:
            end_date_must_be_on_weekday = get_parameter_value(
                key=ParameterKeys.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL, cache=cache
            )
            if end_date.weekday() != end_date_must_be_on_weekday:
                raise ValidationError(
                    f"Das End-Datum muss am gleichem Wochentag sein wie die Kommissioniervariable ({OPTIONS_WEEKDAYS[end_date_must_be_on_weekday][1]}), "
                    f"du hast {OPTIONS_WEEKDAYS[end_date.weekday()][1]} angegeben"
                )

        if TapirCache.get_growing_period_at_date(
            subscription.start_date, cache=cache
        ) != TapirCache.get_growing_period_at_date(start_date, cache=cache):
            raise ValidationError(
                "Das neue Start-Datum muss im gleiche Vertragsperiode liegen wie das alte"
            )

        if TapirCache.get_growing_period_at_date(
            subscription.end_date, cache=cache
        ) != TapirCache.get_growing_period_at_date(end_date, cache=cache):
            raise ValidationError(
                "Das neue End-Datum muss im gleiche Vertragsperiode liegen wie das alte"
            )
