from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.fields import SerializerMethodField

from tapir.bestell_wizard.models import ProductTypeAccordionInBestellWizard
from tapir.core.config import LEGAL_STATUS_OPTIONS
from tapir.deliveries.serializers import (
    ProductSerializer,
    SubscriptionSerializer,
    PickupLocationSerializer,
    ProductTypeSerializer,
)
from tapir.pickup_locations.config import OPTIONS_PICKING_MODE
from tapir.pickup_locations.serializers import ProductBasketSizeEquivalenceSerializer
from tapir.products.serializers import ProductTypeAccordionInBestellWizardSerializer
from tapir.wirgarten.constants import NO_DELIVERY
from tapir.wirgarten.models import (
    Member,
    CoopShareTransaction,
    ProductType,
    Product,
    Subscription,
    SubscriptionChangeLogEntry,
)
from tapir.wirgarten.service.products import get_product_price
from tapir.wirgarten.utils import get_today


class ProductForCancellationSerializer(serializers.Serializer):
    product = ProductSerializer(read_only=True)
    is_in_trial = serializers.BooleanField()
    cancellation_date = serializers.DateField()


class CancellationDataSerializer(serializers.Serializer):
    can_cancel_coop_membership = serializers.BooleanField()
    subscribed_products = ProductForCancellationSerializer(many=True)
    legal_status = serializers.ChoiceField(choices=LEGAL_STATUS_OPTIONS)
    default_cancellation_reasons = serializers.ListField(child=serializers.CharField())


class CancelSubscriptionsViewResponseSerializer(serializers.Serializer):
    subscriptions_cancelled = serializers.BooleanField()
    errors = serializers.ListField(child=serializers.CharField())


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


class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        exclude = ["groups", "user_permissions"]


class CancelledSubscriptionSerializer(serializers.Serializer):
    subscription = SubscriptionSerializer()
    member = MemberSerializer()
    pickup_location = PickupLocationSerializer()
    cancellation_type = serializers.CharField()
    show_warning = serializers.BooleanField()


class SubscriptionChangeSerializer(serializers.Serializer):
    product_type = ProductTypeSerializer()
    subscription_cancellations = SubscriptionSerializer(many=True)
    subscription_creations = SubscriptionSerializer(many=True)


class CoopShareTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoopShareTransaction
        fields = "__all__"


class SubscriptionChangeLogEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionChangeLogEntry
        fields = "__all__"


class MemberDataToConfirmSerializer(serializers.Serializer):
    member = MemberSerializer()
    member_profile_url = serializers.CharField()
    pickup_location = PickupLocationSerializer()
    subscription_cancellations = SubscriptionSerializer(many=True)
    subscription_creations = SubscriptionSerializer(many=True)
    subscription_changes = SubscriptionChangeSerializer(many=True)
    subscriptions_deleted = SubscriptionChangeLogEntrySerializer(many=True)
    show_warning = serializers.BooleanField()
    cancellation_types = serializers.ListField(child=serializers.CharField())
    share_purchases = CoopShareTransactionSerializer(many=True)


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
        cache = {}
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
            "icon_link",
            "background_image_in_bestellwizard",
        ]

    products = SerializerMethodField()
    no_delivery = SerializerMethodField()
    accordions = SerializerMethodField()

    @extend_schema_field(PublicProductSerializer(many=True))
    def get_products(self, product_type: ProductType):
        return PublicProductSerializer(
            Product.objects.filter(type=product_type, deleted=False), many=True
        ).data

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


class OrderConfirmationResponseSerializer(serializers.Serializer):
    order_confirmed = serializers.BooleanField()
    error = serializers.CharField(allow_null=True)
    redirect_url = serializers.CharField(required=False)


class PublicSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = [
            "product_name",
            "product_id",
            "product_type",
            "quantity",
            "start_date",
            "end_date",
            "monthly_price",
        ]

    monthly_price = serializers.SerializerMethodField()
    product_name = serializers.SerializerMethodField()
    product_type = serializers.SerializerMethodField()

    @staticmethod
    def get_monthly_price(subscription: Subscription) -> float:
        return float(subscription.total_price(reference_date=None, cache={}))

    @staticmethod
    def get_product_name(subscription: Subscription) -> str:
        return subscription.product.name

    @staticmethod
    def get_product_type_name(subscription: Subscription) -> str:
        return subscription.product.type.name

    @staticmethod
    @extend_schema_field(PublicProductTypeSerializer)
    def get_product_type(subscription: Subscription):
        return PublicProductTypeSerializer(subscription.product.type).data


class UpdateSubscriptionsRequestSerializer(serializers.Serializer):
    member_id = serializers.CharField()
    product_type_id = serializers.CharField()
    shopping_cart = serializers.DictField(child=serializers.IntegerField())
    sepa_allowed = serializers.BooleanField()
    pickup_location_id = serializers.CharField(required=False)
    growing_period_id = serializers.CharField()
    account_owner = serializers.CharField(allow_blank=True)
    iban = serializers.CharField(allow_blank=True)
    payment_rhythm = serializers.CharField(required=False)


class MemberProfileCapacityCheckRequestSerializer(serializers.Serializer):
    member_id = serializers.CharField()
    shopping_cart = serializers.DictField(child=serializers.IntegerField())


class CancelSubscriptionsRequestSerializer(serializers.Serializer):
    member_id = serializers.CharField()
    product_ids = serializers.ListField(child=serializers.CharField())
    cancel_coop_membership = serializers.BooleanField()
    cancellation_reasons = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    custom_cancellation_reason = serializers.CharField(required=False)


class MemberSubscriptionDataSerializer(serializers.Serializer):
    product_types = PublicProductTypeSerializer(many=True)
    subscriptions = PublicSubscriptionSerializer(many=True)
    bestell_wizard_url_template = serializers.URLField()
