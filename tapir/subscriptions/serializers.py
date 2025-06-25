from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.fields import SerializerMethodField

from tapir.core.config import LEGAL_STATUS_OPTIONS
from tapir.deliveries.serializers import (
    ProductSerializer,
    SubscriptionSerializer,
    PickupLocationSerializer,
    ProductTypeSerializer,
)
from tapir.pickup_locations.config import OPTIONS_PICKING_MODE
from tapir.pickup_locations.serializers import ProductBasketSizeEquivalenceSerializer
from tapir.subscriptions.services.subscription_price_manager import (
    SubscriptionPriceManager,
)
from tapir.wirgarten.constants import NO_DELIVERY
from tapir.wirgarten.models import (
    Member,
    CoopShareTransaction,
    ProductType,
    Product,
    Subscription,
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
    url_of_image_in_bestellwizard = serializers.URLField()


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


class MemberDataToConfirmSerializer(serializers.Serializer):
    member = MemberSerializer()
    member_profile_url = serializers.CharField()
    pickup_location = PickupLocationSerializer()
    subscription_cancellations = SubscriptionSerializer(many=True)
    subscription_creations = SubscriptionSerializer(many=True)
    subscription_changes = SubscriptionChangeSerializer(many=True)
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
        ]

    products = SerializerMethodField()
    no_delivery = SerializerMethodField()

    @extend_schema_field(PublicProductSerializer(many=True))
    def get_products(self, product_type: ProductType):
        return PublicProductSerializer(
            Product.objects.filter(type=product_type), many=True
        ).data

    def get_no_delivery(self, product_type: ProductType) -> bool:
        return product_type.delivery_cycle == NO_DELIVERY[0]


class PersonalDataSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    phone_number = serializers.CharField()
    street = serializers.CharField()
    street_2 = serializers.CharField(allow_blank=True)
    postcode = serializers.CharField()
    city = serializers.CharField()
    country = serializers.CharField()
    birthdate = serializers.DateField()
    account_owner = serializers.CharField()
    iban = serializers.CharField()


class BestellWizardConfirmOrderRequestSerializer(serializers.Serializer):
    # map of productId -> quantity ordered
    shopping_cart = serializers.DictField(child=serializers.IntegerField())
    personal_data = PersonalDataSerializer()
    sepa_allowed = serializers.BooleanField()
    contract_accepted = serializers.BooleanField()
    statute_accepted = serializers.BooleanField()
    nb_shares = serializers.IntegerField()
    pickup_location_id = serializers.CharField()
    student_status_enabled = serializers.BooleanField()


class BestellWizardConfirmOrderResponseSerializer(serializers.Serializer):
    order_confirmed = serializers.BooleanField()
    errors = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField())
    )


class BestellWizardCapacityCheckRequestSerializer(serializers.Serializer):
    # map of productId -> quantity ordered
    shopping_cart = serializers.DictField(child=serializers.IntegerField())


class BestellWizardCapacityCheckResponseSerializer(serializers.Serializer):
    ids_of_products_over_capacity = serializers.ListField(child=serializers.CharField())
    ids_of_product_types_over_capacity = serializers.ListField(
        child=serializers.CharField()
    )


class BestellWizardBaseDataResponseSerializer(serializers.Serializer):
    price_of_a_share = serializers.FloatField()
    theme = serializers.CharField()
    allow_investing_membership = serializers.BooleanField()
    product_types = PublicProductTypeSerializer(many=True)
    force_waiting_list = serializers.BooleanField()
    intro_enabled = serializers.BooleanField()
    student_status_allowed = serializers.BooleanField()


class BestellWizardDeliveryDatesForOrderRequestSerializer(serializers.Serializer):
    shopping_cart = serializers.DictField(child=serializers.IntegerField())
    pickup_location_id = serializers.CharField()


class BestellWizardDeliveryDatesForOrderResponseSerializer(serializers.Serializer):
    product_type_id_to_next_delivery_date_map = serializers.DictField(
        child=serializers.DateField()
    )


class PublicSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = [
            "product_name",
            "product_id",
            "product_type_name",
            "product_type_id",
            "quantity",
            "start_date",
            "end_date",
            "monthly_price",
            "solidarity_display",
        ]

    monthly_price = serializers.SerializerMethodField()
    product_name = serializers.SerializerMethodField()
    product_type_name = serializers.SerializerMethodField()
    product_type_id = serializers.SerializerMethodField()
    solidarity_display = serializers.SerializerMethodField()

    @staticmethod
    def get_monthly_price(subscription: Subscription) -> float:
        return SubscriptionPriceManager.get_monthly_price_of_subscription_without_solidarity(
            subscription=subscription, reference_date=None, cache={}
        )

    @staticmethod
    def get_product_name(subscription: Subscription) -> str:
        return subscription.product.name

    @staticmethod
    def get_product_type_name(subscription: Subscription) -> str:
        return subscription.product.type.name

    @staticmethod
    def get_product_type_id(subscription: Subscription) -> str:
        return subscription.product.type_id

    @staticmethod
    def get_solidarity_display(subscription: Subscription) -> str | None:
        prefix = ""

        if (
            subscription.solidarity_price_percentage is not None
            and subscription.solidarity_price_percentage != 0
        ):
            if subscription.solidarity_price_percentage > 0:
                prefix = "+"
            return f"{prefix}{subscription.solidarity_price_percentage}%"

        if (
            subscription.solidarity_price_absolute is not None
            and subscription.solidarity_price_absolute != 0
        ):
            if subscription.solidarity_price_absolute > 0:
                prefix = "+"
            return f"{prefix}{subscription.solidarity_price_absolute}€"
        return None
