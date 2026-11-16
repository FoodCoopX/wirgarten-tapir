from rest_framework import serializers

from tapir.bidding_round.config import OPTIONS_BIDDING_ROUND_PROCEDURE


class RoundProductPriceInputSerializer(serializers.Serializer):
    product_id = serializers.CharField()
    reference_value = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    min_amount = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    size = serializers.CharField(required=True, allow_null=False, allow_blank=False)


class RoundCreateSerializer(serializers.Serializer):
    growing_period_id = serializers.CharField(required=False, allow_null=True)
    name = serializers.CharField()
    end_at = serializers.DateTimeField()
    start_at = serializers.DateTimeField(required=False, allow_null=True)
    comment = serializers.CharField(required=False, allow_blank=True)
    product_type_id = serializers.CharField(required=False, allow_null=True)
    target_amount_per_year = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    prices = RoundProductPriceInputSerializer(many=True, required=False)
    bidding_procedure = serializers.ChoiceField(
        choices=OPTIONS_BIDDING_ROUND_PROCEDURE, required=False
    )
    bid_levels = serializers.IntegerField(required=False, min_value=1, max_value=3)
    include_auto_renewed = serializers.BooleanField(required=False)


class RoundConfigSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    comment = serializers.CharField(required=False, allow_blank=True)
    start_at = serializers.DateTimeField(required=False, allow_null=True)
    end_at = serializers.DateTimeField(required=False)
    product_type_id = serializers.CharField(required=False, allow_null=True)
    target_amount_per_year = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    prices = RoundProductPriceInputSerializer(many=True, required=False)
    bidding_procedure = serializers.ChoiceField(
        choices=OPTIONS_BIDDING_ROUND_PROCEDURE, required=False
    )
    bid_levels = serializers.IntegerField(required=False, min_value=1, max_value=3)
    include_auto_renewed = serializers.BooleanField(required=False)


class BidSubmitItemSerializer(serializers.Serializer):
    round_product_type_id = serializers.CharField()
    product_id = serializers.CharField()
    quantity = serializers.IntegerField(
        required=False, min_value=1, max_value=5, default=1
    )
    amount_1 = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    amount_2 = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    amount_3 = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class BidSubmitSerializer(serializers.Serializer):
    items = BidSubmitItemSerializer(many=True)


class BidAdminItemSerializer(serializers.Serializer):
    round_product_type_id = serializers.CharField()
    product_id = serializers.CharField()
    quantity = serializers.IntegerField(
        required=False, min_value=1, max_value=5, default=1
    )
    amount_1 = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    amount_2 = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    amount_3 = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class BidAdminSerializer(serializers.Serializer):
    member_id = serializers.CharField(required=False)
    items = BidAdminItemSerializer(many=True, required=False)
    entered_by_admin = serializers.BooleanField(required=False)
    admin_confirmed = serializers.BooleanField(required=False)


class BidAdminCreateSerializer(BidAdminSerializer):
    member_id = serializers.CharField()
    items = BidAdminItemSerializer(many=True)


class ConfirmBidsSerializer(serializers.Serializer):
    bid_ids = serializers.ListField(child=serializers.CharField(), required=False)


class LockAverageBidSerializer(serializers.Serializer):
    position = serializers.FloatField(min_value=0, max_value=100)
    surcharge_percent = serializers.FloatField(
        required=False, min_value=0, max_value=100, default=0
    )
    surcharge_on_bids = serializers.BooleanField(required=False, default=False)
    surcharge_on_average = serializers.BooleanField(required=False, default=False)


class MemberOptionSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    email = serializers.CharField()


class CreateContractsSerializer(serializers.Serializer):
    bid_ids = serializers.ListField(child=serializers.CharField(), required=False)
    bid_level = serializers.IntegerField(required=False, min_value=1, max_value=3)
    create_auto_renewed_contracts = serializers.BooleanField(
        required=False, default=False
    )


class RoundProductPriceSerializer(serializers.Serializer):
    product_id = serializers.CharField()
    product_name = serializers.CharField()
    reference_value = serializers.CharField(allow_null=True)
    min_amount = serializers.CharField(allow_null=True)
    size = serializers.CharField(allow_null=True)


class RoundProductSerializer(serializers.Serializer):
    product_type_id = serializers.CharField()
    product_type_name = serializers.CharField()
    target_amount_per_year = serializers.CharField(allow_null=True)
    prices = RoundProductPriceSerializer(many=True)


class RoundSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    display_name = serializers.CharField()
    status = serializers.CharField()
    bidding_procedure = serializers.CharField()
    bid_levels = serializers.IntegerField()
    include_auto_renewed = serializers.BooleanField()
    average_bid_locked_at = serializers.DateTimeField(allow_null=True)
    locked_bid_range_position = serializers.CharField(allow_null=True)
    locked_bidder_average_per_share_per_month = serializers.CharField(allow_null=True)
    locked_surcharge_percent = serializers.CharField()
    locked_surcharge_on_bids = serializers.BooleanField()
    locked_surcharge_on_average = serializers.BooleanField()
    start_at = serializers.DateTimeField(allow_null=True)
    end_at = serializers.DateTimeField()
    contracts_created_at = serializers.DateTimeField(allow_null=True)
    growing_period_id = serializers.CharField(allow_null=True)
    comment = serializers.CharField()
    has_bids = serializers.BooleanField()
    product = RoundProductSerializer(allow_null=True)


class BidItemSerializer(serializers.Serializer):
    round_product_type_id = serializers.CharField()
    product_type_name = serializers.CharField()
    product_id = serializers.CharField()
    product_name = serializers.CharField()
    quantity = serializers.IntegerField()
    amount_1 = serializers.CharField(allow_null=True)
    amount_2 = serializers.CharField(allow_null=True)
    amount_3 = serializers.CharField(allow_null=True)
    amount_per_year = serializers.CharField()


class BidSerializer(serializers.Serializer):
    id = serializers.CharField()
    member_id = serializers.CharField()
    entered_by_admin = serializers.BooleanField()
    admin_confirmed = serializers.DateTimeField(allow_null=True)
    pickup_location_id = serializers.CharField(allow_null=True)
    updated_at = serializers.DateTimeField(allow_null=True)
    total_per_year = serializers.CharField()
    items = BidItemSerializer(many=True)


class BidProductVariantSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    reference_value = serializers.CharField(allow_null=True)
    min_amount = serializers.CharField(allow_null=True)
    size = serializers.CharField(allow_null=True)
    current_quantity = serializers.IntegerField(allow_null=True)


class BiddableProductSerializer(serializers.Serializer):
    id = serializers.CharField()
    product_type_id = serializers.CharField()
    product_type_name = serializers.CharField()
    products = BidProductVariantSerializer(many=True)


class BidTextsSerializer(serializers.Serializer):
    level_1_label = serializers.CharField()
    level_2_label = serializers.CharField()
    level_3_label = serializers.CharField()
    amount_label = serializers.CharField()
    reference_value_hint = serializers.CharField()
    simple_explanation = serializers.CharField()
    bid_range_explanation = serializers.CharField()
    green_label = serializers.CharField()
    yellow_label = serializers.CharField()
    red_label = serializers.CharField()
    live_yearly_label = serializers.CharField()
    monthly_hint = serializers.CharField()
    monthly_unit = serializers.CharField()
    yearly_unit = serializers.CharField()
    confirm_text = serializers.CharField()
    success_text = serializers.CharField()
    error_text = serializers.CharField()


class RoundTextsSerializer(serializers.Serializer):
    intro_title = serializers.CharField()
    intro_text = serializers.CharField()
    ended_text = serializers.CharField()
    login_title = serializers.CharField()
    login_text = serializers.CharField()
    summary_title = serializers.CharField()
    pickup_location_title = serializers.CharField()
    submit_label = serializers.CharField()
    bid = BidTextsSerializer()


class CurrentPickupLocationSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    yearly_delivery_charge = serializers.CharField()


class PublicDataResponseSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
    url_enabled = serializers.BooleanField(required=False)
    url = serializers.CharField(allow_null=True, required=False)
    display_name = serializers.CharField(required=False)
    round = RoundSerializer(allow_null=True, required=False)
    round_status = serializers.CharField(required=False)
    texts = RoundTextsSerializer(required=False)
    biddable_product = BiddableProductSerializer(allow_null=True, required=False)
    is_authenticated = serializers.BooleanField(required=False)
    status_enabled = serializers.BooleanField(required=False)
    status_public_enabled = serializers.BooleanField(required=False)
    current_pickup_location = CurrentPickupLocationSerializer(
        allow_null=True, required=False
    )
    bid = BidSerializer(allow_null=True, required=False)


class GrowingPeriodOptionSerializer(serializers.Serializer):
    id = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()


class ProductOptionSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    size = serializers.DecimalField(max_digits=8, decimal_places=2, allow_null=True)


class ProductTypeOptionSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    products = ProductOptionSerializer(many=True)


class RoundStatsBidSerializer(serializers.Serializer):
    bid_id = serializers.CharField()
    member_id = serializers.CharField()
    member_name = serializers.CharField()
    email = serializers.CharField()
    entered_by_admin = serializers.BooleanField()
    admin_confirmed = serializers.DateTimeField(allow_null=True)
    updated_at = serializers.DateTimeField(allow_null=True)
    amount_per_month = serializers.CharField()
    amount_per_year = serializers.CharField()
    items = BidItemSerializer(many=True)


class EvaluationLevelSerializer(serializers.Serializer):
    reached_per_year = serializers.CharField()
    coverage_percent = serializers.FloatField()
    coverage_status = serializers.CharField()
    bidder_average_per_month = serializers.CharField()


class EvaluationLevelsSerializer(serializers.Serializer):
    green = EvaluationLevelSerializer()
    yellow = EvaluationLevelSerializer(required=False)
    red = EvaluationLevelSerializer()


class EvaluationAggregatesSerializer(serializers.Serializer):
    bidding_procedure = serializers.CharField()
    bid_levels = serializers.IntegerField()
    recommended_level = serializers.IntegerField()
    bid_range_position = serializers.FloatField()
    coverage_status = serializers.CharField()
    target_per_year = serializers.CharField()
    coverage_percent = serializers.FloatField()
    bidder_average_per_month = serializers.CharField()
    levels = EvaluationLevelsSerializer()


class PublicEvaluationResponseSerializer(EvaluationAggregatesSerializer):
    capacity_shares = serializers.CharField()
    current_shares = serializers.CharField()
    utilization_percent = serializers.FloatField()


class AutoRenewedMemberSerializer(serializers.Serializer):
    member_id = serializers.CharField()
    member_name = serializers.CharField()
    monthly_reference = serializers.CharField()
    yearly_reference = serializers.CharField()


class ExtraPositionSerializer(serializers.Serializer):
    label = serializers.CharField()
    reached_per_year = serializers.CharField()
    applicable = serializers.BooleanField()


class ExtraPositionsSerializer(serializers.Serializer):
    membership = ExtraPositionSerializer()
    delivery_charge = ExtraPositionSerializer()


class RoundResultsResponseSerializer(EvaluationAggregatesSerializer):
    round_product_type_id = serializers.CharField(allow_null=True)
    include_auto_renewed = serializers.BooleanField()
    auto_renewed_per_year = serializers.CharField()
    auto_renewed = AutoRenewedMemberSerializer(many=True)
    extra_positions = ExtraPositionsSerializer()
    non_bidder_rate_per_share = serializers.CharField()
    reached_per_year = serializers.CharField()
    bidder_count = serializers.IntegerField()
    bidder_average_per_month = serializers.CharField()
    unconfirmed_bid_count = serializers.IntegerField()
    average_bid_locked_at = serializers.DateTimeField(allow_null=True)
    locked_bid_range_position = serializers.CharField(allow_null=True)
    locked_surcharge_percent = serializers.CharField()
    locked_surcharge_on_bids = serializers.BooleanField()
    locked_surcharge_on_average = serializers.BooleanField()
    bids = RoundStatsBidSerializer(many=True)


class MemberBidResponseSerializer(serializers.Serializer):
    round = RoundSerializer()
    biddable_product = BiddableProductSerializer(allow_null=True)
    bid = BidSerializer(allow_null=True)


class CreateContractsErrorSerializer(serializers.Serializer):
    bid_id = serializers.CharField()
    member_id = serializers.CharField()
    member_name = serializers.CharField()
    error = serializers.CharField()


class CreateContractsSubscriptionSerializer(serializers.Serializer):
    id = serializers.CharField()
    member_id = serializers.CharField()
    product_id = serializers.CharField()


class CreateContractsResponseSerializer(serializers.Serializer):
    errors = CreateContractsErrorSerializer(many=True)
    subscriptions = CreateContractsSubscriptionSerializer(many=True)
