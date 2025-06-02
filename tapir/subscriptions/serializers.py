from rest_framework import serializers

from tapir.core.config import LEGAL_STATUS_OPTIONS
from tapir.deliveries.serializers import (
    ProductSerializer,
    SubscriptionSerializer,
    PickupLocationSerializer,
    ProductTypeSerializer,
)
from tapir.pickup_locations.config import OPTIONS_PICKING_MODE
from tapir.pickup_locations.serializers import ProductBasketSizeEquivalenceSerializer
from tapir.wirgarten.models import Member, CoopShareTransaction, ProductType


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


class PublicProductTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductType
        fields = ["id", "name", "description_bestellwizard"]
