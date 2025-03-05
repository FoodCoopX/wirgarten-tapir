from rest_framework import serializers

from tapir.deliveries.models import Joker
from tapir.wirgarten.models import (
    Subscription,
    PickupLocation,
    PickupLocationOpeningTime,
    Product,
    ProductType,
    GrowingPeriod,
)


class ProductTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductType
        fields = "__all__"


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"

    type = ProductTypeSerializer()


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = "__all__"

    product = ProductSerializer()


class PickupLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickupLocation
        fields = "__all__"


class PickupLocationOpeningTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickupLocationOpeningTime
        fields = "__all__"


class DeliverySerializer(serializers.Serializer):
    delivery_date = serializers.DateField()
    pickup_location = PickupLocationSerializer()
    subscriptions = SubscriptionSerializer(many=True)
    pickup_location_opening_times = PickupLocationOpeningTimeSerializer(many=True)
    joker_used = serializers.BooleanField()
    can_joker_be_used = serializers.BooleanField()


class JokerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Joker
        fields = "__all__"


class GrowingPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = GrowingPeriod
        fields = "__all__"


class JokerWithCancellationLimitSerializer(serializers.Serializer):
    joker = JokerSerializer()
    cancellation_limit = serializers.DateField()


class MemberJokerInformationSerializer(serializers.Serializer):
    used_jokers = JokerWithCancellationLimitSerializer(many=True)
    max_jokers_per_growing_period = serializers.IntegerField()
    growing_periods = GrowingPeriodSerializer(many=True)
    weekday_limit = serializers.IntegerField()
