from rest_framework import serializers

from tapir.deliveries.models import Joker
from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.wirgarten.models import (
    Subscription,
    PickupLocation,
    PickupLocationOpeningTime,
    Product,
    ProductType,
    GrowingPeriod,
)
from tapir.wirgarten.parameters import OPTIONS_WEEKDAYS


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

    day_of_week_string = serializers.SerializerMethodField()

    @staticmethod
    def get_day_of_week_string(opening_time: PickupLocationOpeningTime):
        return OPTIONS_WEEKDAYS[opening_time.day_of_week][1]


class DeliverySerializer(serializers.Serializer):
    delivery_date = serializers.DateField()
    pickup_location = PickupLocationSerializer()
    subscriptions = SubscriptionSerializer(many=True)
    pickup_location_opening_times = PickupLocationOpeningTimeSerializer(many=True)
    joker_used = serializers.BooleanField()
    can_joker_be_used = serializers.BooleanField()
    can_joker_be_used_relative_to_date_limit = serializers.BooleanField()
    is_delivery_cancelled_this_week = serializers.BooleanField()


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
    delivery_date = serializers.DateField()


class JokerRestrictionSerializer(serializers.Serializer):
    start_day = serializers.IntegerField()
    start_month = serializers.IntegerField()
    end_day = serializers.IntegerField()
    end_month = serializers.IntegerField()
    max_jokers = serializers.IntegerField()


class UsedJokerInGrowingPeriodSerializer(serializers.Serializer):
    growing_period_start = serializers.DateField()
    growing_period_end = serializers.DateField()
    number_of_used_jokers = serializers.IntegerField()
    joker_restrictions = JokerRestrictionSerializer(many=True)
    max_jokers = serializers.IntegerField()


class MemberJokerInformationSerializer(serializers.Serializer):
    used_jokers = JokerWithCancellationLimitSerializer(many=True)
    weekday_limit = serializers.IntegerField()
    used_joker_in_growing_period = UsedJokerInGrowingPeriodSerializer(many=True)


class DeliveryDayAdjustmentSerializer(serializers.Serializer):
    calendar_week = serializers.IntegerField()
    adjusted_weekday = serializers.IntegerField()


class GrowingPeriodWithDeliveryDayAdjustmentsSerializer(serializers.Serializer):
    growing_period_id = serializers.CharField()
    growing_period_start_date = serializers.DateField()
    growing_period_end_date = serializers.DateField()
    growing_period_weeks_without_delivery = serializers.ListField(
        child=serializers.IntegerField()
    )
    adjustments = DeliveryDayAdjustmentSerializer(many=True)
    max_jokers_per_member = serializers.IntegerField()
    joker_restrictions = serializers.CharField(
        validators=[JokerManagementService.validate_joker_restrictions]
    )
    jokers_enabled = serializers.BooleanField(read_only=True)
