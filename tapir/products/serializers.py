from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.fields import SerializerMethodField

from tapir.bestell_wizard.models import ProductTypeAccordionInBestellWizard
from tapir.deliveries.services.subscription_price_type_decider import (
    SubscriptionPricingStrategyDecider,
)
from tapir.pickup_locations.config import OPTIONS_PICKING_MODE
from tapir.pickup_locations.serializers import ProductBasketSizeEquivalenceSerializer
from tapir.products.services.tax_rate_service import TaxRateService
from tapir.subscriptions.config import NOTICE_PERIOD_UNIT_OPTIONS
from tapir.wirgarten.constants import DeliveryCycle, NO_DELIVERY
from tapir.wirgarten.models import Product, ProductType
from tapir.wirgarten.service.products import get_product_price
from tapir.wirgarten.utils import get_today


class ProductTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductType
        fields = "__all__"


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"

    type = ProductTypeSerializer()


class ProductTypeAccordionInBestellWizardSerializer(serializers.Serializer):
    title = serializers.CharField()
    description = serializers.CharField()
    order = serializers.IntegerField()


class ExtendedProductTypeSerializer(serializers.Serializer):
    name = serializers.CharField()
    description_bestellwizard_short = serializers.CharField(
        required=False, allow_blank=True
    )
    description_bestellwizard_long = serializers.CharField(
        required=False, allow_blank=True
    )
    order_in_bestellwizard = serializers.IntegerField()
    icon_link = serializers.CharField(required=False, allow_blank=True)
    contract_link = serializers.URLField(required=False, allow_blank=True)
    capacity = serializers.FloatField()
    delivery_cycle = serializers.ChoiceField(choices=DeliveryCycle)
    notice_period_duration = serializers.IntegerField(required=False)
    notice_period_unit = serializers.ChoiceField(
        choices=NOTICE_PERIOD_UNIT_OPTIONS, required=False
    )
    tax_rate = serializers.FloatField()
    tax_rate_change_date = serializers.DateField()
    single_subscription_only = serializers.BooleanField()
    is_affected_by_jokers = serializers.BooleanField()
    must_be_subscribed_to = serializers.BooleanField()
    force_waiting_list = serializers.BooleanField()
    accordions_in_bestell_wizard = ProductTypeAccordionInBestellWizardSerializer(
        many=True
    )
    title_bestellwizard_product_choice = serializers.CharField(allow_blank=True)
    title_bestellwizard_intro = serializers.CharField(allow_blank=True)
    background_image_in_bestellwizard = serializers.CharField(allow_blank=True)
    custom_cycle_delivery_weeks = serializers.DictField(
        child=serializers.ListSerializer(child=serializers.IntegerField())
    )


class ExtendedProductTypeAndConfigSerializer(serializers.Serializer):
    show_notice_period = serializers.BooleanField()
    show_jokers = serializers.BooleanField()
    delivery_cycle_options = serializers.DictField()
    extended_product_type = ExtendedProductTypeSerializer()
    can_update_notice_period = serializers.BooleanField()


class SaveExtendedProductTypeSerializer(serializers.Serializer):
    product_type_id = serializers.CharField(required=False)
    growing_period_id = serializers.CharField()
    extended_product_type = ExtendedProductTypeSerializer()


class ProductTypesAndConfigSerializer(serializers.Serializer):
    product_types_without_capacity = ProductTypeSerializer(many=True)
    show_notice_period = serializers.BooleanField()
    show_jokers = serializers.BooleanField()
    delivery_cycle_options = serializers.DictField()
    can_update_notice_period = serializers.BooleanField()


class ExtendedProductSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    deleted = serializers.BooleanField()
    base = serializers.BooleanField()
    price = serializers.FloatField()
    size = serializers.FloatField()
    basket_size_equivalences = ProductBasketSizeEquivalenceSerializer(many=True)
    growing_period_id = serializers.CharField(required=False)
    picking_mode = serializers.ChoiceField(choices=OPTIONS_PICKING_MODE, read_only=True)
    description_in_bestellwizard = serializers.CharField()
    url_of_image_in_bestellwizard = serializers.URLField(allow_blank=True)
    capacity = serializers.IntegerField(allow_null=True)
    min_coop_shares = serializers.IntegerField()
    price_per_delivery = serializers.BooleanField(read_only=True)


class PublicProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "price",
            "description_in_bestellwizard",
            "url_of_image_in_bestellwizard",
        ]

    price = SerializerMethodField()

    @extend_schema_field(OpenApiTypes.FLOAT)
    def get_price(self, product: Product):
        cache = self.context["cache"]
        return get_product_price(
            product=product, reference_date=get_today(cache=cache), cache=cache
        ).price


class PublicProductTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductType
        fields = [
            "id",
            "name",
            "description_bestellwizard_short",
            "description_bestellwizard_long",
            "products",
            "order_in_bestellwizard",
            "must_be_subscribed_to",
            "no_delivery",
            "single_subscription_only",
            "force_waiting_list",
            "accordions",
            "title_bestellwizard_product_choice",
            "title_bestellwizard_intro",
            "icon_link",
            "background_image_in_bestellwizard",
            "price_per_delivery",
            "tax_rate",
        ]

    products = SerializerMethodField()
    no_delivery = SerializerMethodField()
    accordions = SerializerMethodField()
    price_per_delivery = SerializerMethodField()
    tax_rate = SerializerMethodField()

    def get_tax_rate(self, product_type: ProductType) -> float:
        cache = self.context["cache"]
        return TaxRateService.get_tax_rate(
            product_type=product_type, at_date=get_today(cache=cache), cache=cache
        )

    @staticmethod
    def get_price_per_delivery(product_type: ProductType) -> bool:
        return SubscriptionPricingStrategyDecider.is_price_by_delivery(
            product_type.delivery_cycle
        )

    @extend_schema_field(PublicProductSerializer(many=True))
    def get_products(self, product_type: ProductType):
        serialized_products = PublicProductSerializer(
            Product.objects.filter(type=product_type, deleted=False),
            many=True,
            context=self.context,
        ).data

        return sorted(serialized_products, key=lambda product: product["price"])

    @staticmethod
    def get_no_delivery(product_type: ProductType) -> bool:
        return product_type.delivery_cycle == NO_DELIVERY[0]

    @extend_schema_field(ProductTypeAccordionInBestellWizardSerializer(many=True))
    def get_accordions(self, product_type: ProductType):
        return ProductTypeAccordionInBestellWizardSerializer(
            ProductTypeAccordionInBestellWizard.objects.filter(
                product_type=product_type
            ),
            many=True,
        ).data
