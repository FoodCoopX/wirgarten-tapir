from rest_framework import serializers

from tapir.deliveries.models import Joker
from tapir.wirgarten.models import (
    Subscription,
    PickupLocation,
    PickupLocationOpeningTime,
)


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = "__all__"


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


class JokerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Joker
        fields = "__all__"
