from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from tapir.core.config import LEGAL_STATUS_OPTIONS
from tapir.deliveries.serializers import (
    SubscriptionSerializer,
)
from tapir.pickup_locations.serializers import PickupLocationSerializer
from tapir.products.serializers import (
    PublicProductTypeSerializer,
    ProductTypeSerializer,
    ProductSerializer,
)
from tapir.subscriptions.config import NOTICE_PERIOD_UNIT_OPTIONS
from tapir.subscriptions.services.subscription_price_calculator import (
    SubscriptionPriceCalculator,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.wirgarten.models import (
    Member,
    CoopShareTransaction,
    Subscription,
    SubscriptionChangeLogEntry,
)
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
            "id",
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

    @extend_schema_field(PublicProductTypeSerializer)
    def get_product_type(self, subscription: Subscription):
        return PublicProductTypeSerializer(
            subscription.product.type, context=self.context
        ).data


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
    update_end_date_of_other_contracts = serializers.BooleanField()


class ConvertWeekToDateForSubscriptionChangesResponseSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()


class ConfirmSubscriptionChangesRequestSerializer(serializers.Serializer):
    confirm_cancellation_ids = serializers.ListField(child=serializers.CharField())
    confirm_creation_ids = serializers.ListField(child=serializers.CharField())
    confirm_purchase_ids = serializers.ListField(child=serializers.CharField())
    confirm_deletion_ids = serializers.ListField(child=serializers.IntegerField())


class SubscriptionPriceOverrideChangeRequestSerializer(serializers.Serializer):
    subscription_id = serializers.CharField()
    price_override = serializers.FloatField(allow_null=True)


class SubscriptionTrialFieldsSerializer(SubscriptionSerializer):
    is_in_trial = serializers.SerializerMethodField()
    default_trial_end_date = serializers.SerializerMethodField()
    effective_trial_end_date = serializers.SerializerMethodField()

    def get_is_in_trial(self, subscription) -> bool:
        cache = self.context["cache"]
        return TrialPeriodManager.is_contract_in_trial(subscription, cache=cache)

    def get_default_trial_end_date(self, subscription):
        cache = self.context["cache"]
        return TrialPeriodManager.get_last_day_of_trial_period_by_weeks(
            subscription, cache=cache
        )

    def get_effective_trial_end_date(self, subscription):
        cache = self.context["cache"]
        return TrialPeriodManager.get_last_day_of_trial_period(
            subscription, cache=cache
        )


class SubscriptionTrialChangeRequestSerializer(serializers.Serializer):
    subscription_id = serializers.CharField()
    trial_disabled = serializers.BooleanField()
    trial_end_date_override = serializers.DateField(allow_null=True, required=False)
