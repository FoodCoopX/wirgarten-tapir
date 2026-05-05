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
from tapir.deliveries.services.subscription_price_type_decider import (
    SubscriptionPricingStrategyDecider,
)
from tapir.pickup_locations.config import OPTIONS_PICKING_MODE
from tapir.pickup_locations.serializers import ProductBasketSizeEquivalenceSerializer
from tapir.products.serializers import ProductTypeAccordionInBestellWizardSerializer
from tapir.subscriptions.config import NOTICE_PERIOD_UNIT_OPTIONS
from tapir.subscriptions.services.subscription_price_calculator import (
    SubscriptionPriceCalculator,
)
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
    last_day_of_notice_period = serializers.DateField()
    date_limit_for_trial_cancellation = serializers.DateField(required=False)
    notice_period_duration = serializers.IntegerField()
    notice_period_unit = serializers.ChoiceField(choices=NOTICE_PERIOD_UNIT_OPTIONS)
    subscription_end_date = serializers.DateField()


class SolidarityContributionCancellationDataSerializer(serializers.Serializer):
    exists = serializers.BooleanField()
    is_in_trial = serializers.BooleanField()
    cancellation_date = serializers.DateField()


class CancellationDataSerializer(serializers.Serializer):
    can_cancel_coop_membership = serializers.BooleanField()
    subscribed_products = ProductForCancellationSerializer(many=True)
    solidarity_contribution_data = SolidarityContributionCancellationDataSerializer()
    legal_status = serializers.ChoiceField(choices=LEGAL_STATUS_OPTIONS)
    default_cancellation_reasons = serializers.ListField(child=serializers.CharField())
    show_trial_period_help_text = serializers.BooleanField()
    trial_period_duration = serializers.IntegerField()
    trial_period_is_flexible = serializers.BooleanField()


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
    price_per_delivery = serializers.BooleanField(read_only=True)


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
            "title_bestellwizard_intro",
            "icon_link",
            "background_image_in_bestellwizard",
            "price_per_delivery",
        ]

    products = SerializerMethodField()
    no_delivery = SerializerMethodField()
    accordions = SerializerMethodField()
    price_per_delivery = SerializerMethodField()

    @staticmethod
    def get_price_per_delivery(product_type: ProductType) -> bool:
        return SubscriptionPricingStrategyDecider.is_price_by_delivery(
            product_type.delivery_cycle
        )

    @extend_schema_field(PublicProductSerializer(many=True))
    def get_products(self, product_type: ProductType):
        serialized_products = PublicProductSerializer(
            Product.objects.filter(type=product_type, deleted=False), many=True
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
        cache = {}
        return float(
            SubscriptionPriceCalculator.get_monthly_price(
                subscription=subscription,
                reference_date=get_today(cache=cache),
                cache=cache,
            )
        )

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
    cancellation_policy_read = serializers.BooleanField()
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
    product_ids = serializers.ListField(child=serializers.CharField(), required=False)
    cancel_coop_membership = serializers.BooleanField()
    cancellation_reasons = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    custom_cancellation_reason = serializers.CharField(required=False)
    cancel_solidarity_contribution = serializers.BooleanField()


class MemberSubscriptionDataSerializer(serializers.Serializer):
    product_types = PublicProductTypeSerializer(many=True)
    subscriptions = PublicSubscriptionSerializer(many=True)
    bestell_wizard_url_template = serializers.URLField()


class SubscriptionDateChangeRequestSerializer(serializers.Serializer):
    start_date_is_on_period_start = serializers.BooleanField()
    end_date_is_on_period_end = serializers.BooleanField()
    start_week = serializers.IntegerField()
    end_week = serializers.IntegerField()
    subscription_id = serializers.CharField()


class ConvertWeekToDateForSubscriptionChangesResponseSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()


class ConfirmSubscriptionChangesRequestSerializer(serializers.Serializer):
    confirm_cancellation_ids = serializers.ListField(child=serializers.CharField())
    confirm_creation_ids = serializers.ListField(child=serializers.CharField())
    confirm_purchase_ids = serializers.ListField(child=serializers.CharField())
    confirm_deletion_ids = serializers.ListField(child=serializers.IntegerField())
