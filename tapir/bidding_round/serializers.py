from rest_framework import serializers

from tapir.bidding_round.config import OPTIONS_BIDDING_ROUND_PROCEDURE
from tapir.pickup_locations.serializers import PublicPickupLocationSerializer


class RoundProductPriceInputSerializer(serializers.Serializer):
    product_id = serializers.CharField()
    reference_value = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    min_amount = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )


class RoundCreateSerializer(serializers.Serializer):
    growing_period_id = serializers.CharField(required=False, allow_null=True)
    name = serializers.CharField()
    bidding_procedure = serializers.ChoiceField(choices=OPTIONS_BIDDING_ROUND_PROCEDURE)
    bid_levels = serializers.IntegerField(required=False, min_value=1, max_value=3)
    end_at = serializers.DateTimeField()
    start_at = serializers.DateTimeField(required=False, allow_null=True)
    include_auto_renewed = serializers.BooleanField(required=False)
    comment = serializers.CharField(required=False, allow_blank=True)
    product_type_id = serializers.CharField(required=False, allow_null=True)
    target_amount_per_year = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    prices = RoundProductPriceInputSerializer(many=True, required=False)


class RoundConfigSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    comment = serializers.CharField(required=False, allow_blank=True)
    start_at = serializers.DateTimeField(required=False, allow_null=True)
    end_at = serializers.DateTimeField(required=False)
    include_auto_renewed = serializers.BooleanField(required=False)
    bidding_procedure = serializers.ChoiceField(
        choices=OPTIONS_BIDDING_ROUND_PROCEDURE, required=False
    )
    bid_levels = serializers.IntegerField(required=False, min_value=1, max_value=3)
    product_type_id = serializers.CharField(required=False, allow_null=True)
    target_amount_per_year = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    prices = RoundProductPriceInputSerializer(many=True, required=False)


class BidSubmitSerializer(serializers.Serializer):
    items = serializers.ListField(child=serializers.DictField(), required=True)
    pickup_location_id = serializers.CharField(required=False, allow_null=True)


class BidCapacityCheckItemSerializer(serializers.Serializer):
    product_id = serializers.CharField()
    quantity = serializers.IntegerField(min_value=1)


class BiddingRoundCapacityCheckRequestSerializer(serializers.Serializer):
    items = serializers.ListField(
        child=BidCapacityCheckItemSerializer(), max_length=20, required=True
    )
    pickup_location_id = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )


class BiddingRoundCapacityCheckResponseSerializer(serializers.Serializer):
    sufficient = serializers.BooleanField()
    message = serializers.CharField(required=False, allow_blank=True)


class BidAdminItemSerializer(serializers.Serializer):
    round_product_id = serializers.UUIDField()
    product_id = serializers.CharField()
    quantity = serializers.IntegerField()
    amount_1 = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    amount_2 = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    amount_3 = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class BidAdminSerializer(serializers.Serializer):
    member_id = serializers.CharField(required=False)
    items = BidAdminItemSerializer(many=True, required=False)
    pickup_location_id = serializers.CharField(required=False, allow_null=True)
    entered_by_admin = serializers.BooleanField(required=False)
    admin_confirmed = serializers.BooleanField(required=False)


class ConfirmBidsSerializer(serializers.Serializer):
    bid_ids = serializers.ListField(child=serializers.UUIDField(), required=False)


class CreateContractsSerializer(serializers.Serializer):
    bid_ids = serializers.ListField(child=serializers.UUIDField(), required=False)
    bid_level = serializers.IntegerField(required=False, min_value=1, max_value=3)
    create_auto_renewed_contracts = serializers.BooleanField(
        required=False, default=False
    )
    auto_renewed_member_ids = serializers.ListField(
        child=serializers.CharField(), required=False
    )


class CheckContractsSerializer(serializers.Serializer):
    bid_ids = serializers.ListField(child=serializers.UUIDField(), required=False)


class LockAverageBidSerializer(serializers.Serializer):
    position = serializers.FloatField(min_value=0, max_value=100)
    surcharge_percent = serializers.FloatField(
        required=False, min_value=0, max_value=100, default=0
    )
    surcharge_on_bids = serializers.BooleanField(required=False, default=False)
    surcharge_on_average = serializers.BooleanField(required=False, default=False)


# --- Response serializers (schema only) ---

MONEY_FIELD_KWARGS = {"max_digits": 12, "decimal_places": 2}


class RoundProductPriceSerializer(serializers.Serializer):
    product_id = serializers.CharField()
    product_name = serializers.CharField()
    reference_value = serializers.CharField(allow_null=True)
    min_amount = serializers.CharField(allow_null=True)


class RoundProductSerializer(serializers.Serializer):
    product_type_id = serializers.CharField()
    product_type_name = serializers.CharField()
    target_amount_per_year = serializers.CharField(allow_null=True)
    prices = RoundProductPriceSerializer(many=True)


class RoundSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    display_name = serializers.CharField()
    status = serializers.CharField()
    bidding_procedure = serializers.CharField()
    bid_levels = serializers.IntegerField()
    start_at = serializers.DateTimeField(allow_null=True)
    end_at = serializers.DateTimeField()
    include_auto_renewed = serializers.BooleanField()
    contracts_created_at = serializers.DateTimeField(allow_null=True)
    growing_period_id = serializers.CharField(allow_null=True)
    comment = serializers.CharField()
    has_bids = serializers.BooleanField()
    average_bid_locked_at = serializers.DateTimeField(allow_null=True)
    locked_traffic_light_position = serializers.DecimalField(
        allow_null=True, **MONEY_FIELD_KWARGS
    )
    locked_average_bid_per_share_per_month = serializers.DecimalField(
        allow_null=True, **MONEY_FIELD_KWARGS
    )
    locked_average_bid_per_share_per_year = serializers.DecimalField(
        allow_null=True, **MONEY_FIELD_KWARGS
    )
    locked_bidder_average_per_share_per_month = serializers.DecimalField(
        allow_null=True, **MONEY_FIELD_KWARGS
    )
    locked_bidder_average_per_share_per_year = serializers.DecimalField(
        allow_null=True, **MONEY_FIELD_KWARGS
    )
    locked_surcharge_percent = serializers.DecimalField(**MONEY_FIELD_KWARGS)
    locked_surcharge_on_bids = serializers.BooleanField()
    locked_surcharge_on_average = serializers.BooleanField()
    product = RoundProductSerializer(allow_null=True)


class BidItemSerializer(serializers.Serializer):
    round_product_id = serializers.UUIDField()
    product_type_name = serializers.CharField()
    product_id = serializers.CharField()
    product_name = serializers.CharField()
    quantity = serializers.IntegerField()
    amount_1 = serializers.CharField(allow_null=True)
    amount_2 = serializers.CharField(allow_null=True)
    amount_3 = serializers.CharField(allow_null=True)
    effective_amount = serializers.CharField()
    amount_per_year = serializers.CharField()


class BidSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    member_id = serializers.CharField()
    pickup_location_id = serializers.CharField(allow_null=True)
    pickup_location_name = serializers.CharField(allow_null=True)
    entered_by_admin = serializers.BooleanField()
    admin_confirmed = serializers.DateTimeField(allow_null=True)
    updated_at = serializers.DateTimeField(allow_null=True)
    total_per_year = serializers.CharField()
    items = BidItemSerializer(many=True)


class BidProductVariantSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    reference_value = serializers.CharField(allow_null=True)
    min_amount = serializers.CharField(allow_null=True)


class BiddableProductSerializer(serializers.Serializer):
    id = serializers.CharField()
    product_type_id = serializers.CharField()
    product_type_name = serializers.CharField()
    products = BidProductVariantSerializer(many=True)


class PickupLocationUtilizationSerializer(serializers.Serializer):
    capacity = serializers.CharField()
    demand = serializers.CharField()
    fill_percent = serializers.FloatField(allow_null=True)
    is_full = serializers.BooleanField()


class PickupLocationWithChargeSerializer(PublicPickupLocationSerializer):
    yearly_delivery_charge = serializers.CharField()
    utilization = PickupLocationUtilizationSerializer(allow_null=True)

    class Meta(PublicPickupLocationSerializer.Meta):
        fields = PublicPickupLocationSerializer.Meta.fields + [
            "yearly_delivery_charge",
            "utilization",
        ]


class BidOptionsSerializer(serializers.Serializer):
    quantity_enabled = serializers.BooleanField()
    multiple_positions_enabled = serializers.BooleanField()


class BidTextsSerializer(serializers.Serializer):
    product_label = serializers.CharField()
    variant_label = serializers.CharField()
    quantity_label = serializers.CharField()
    amount_label = serializers.CharField()
    reference_value_hint = serializers.CharField()
    simple_explanation = serializers.CharField()
    traffic_light_explanation = serializers.CharField()
    simple_levels_explanation = serializers.CharField()
    level_1_label = serializers.CharField()
    level_2_label = serializers.CharField()
    level_3_label = serializers.CharField()
    green_label = serializers.CharField()
    yellow_label = serializers.CharField()
    red_label = serializers.CharField()
    pickup_location_label = serializers.CharField()
    live_yearly_label = serializers.CharField()
    monthly_hint = serializers.CharField()
    monthly_unit = serializers.CharField()
    confirm_text = serializers.CharField()
    success_text = serializers.CharField()
    error_text = serializers.CharField()


class RoundTextsSerializer(serializers.Serializer):
    intro_title = serializers.CharField()
    intro_text = serializers.CharField()
    ended_text = serializers.CharField()
    login_title = serializers.CharField()
    login_text = serializers.CharField()
    stats_title = serializers.CharField()
    stats_text = serializers.CharField()
    stats_explanation = serializers.CharField()
    stats_traffic_light_slider_hint = serializers.CharField()
    stats_simple_levels_slider_hint = serializers.CharField()
    pickup_location_title = serializers.CharField()
    pickup_location_text = serializers.CharField()
    summary_title = serializers.CharField()
    submit_label = serializers.CharField()
    bid = BidTextsSerializer()


class PublicDataResponseSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
    url_enabled = serializers.BooleanField(required=False)
    url = serializers.CharField(allow_null=True, required=False)
    display_name = serializers.CharField(required=False)
    round = RoundSerializer(allow_null=True, required=False)
    round_status = serializers.CharField(required=False)
    texts = RoundTextsSerializer(required=False)
    biddable_product = BiddableProductSerializer(allow_null=True, required=False)
    pickup_locations = PickupLocationWithChargeSerializer(many=True, required=False)
    bid_options = BidOptionsSerializer(required=False)
    is_authenticated = serializers.BooleanField(required=False)
    current_pickup_location_id = serializers.CharField(allow_null=True, required=False)
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


class RoundStatsTotalsSerializer(serializers.Serializer):
    target_per_year = serializers.DecimalField(allow_null=True, **MONEY_FIELD_KWARGS)
    reached_per_year = serializers.DecimalField(allow_null=True, **MONEY_FIELD_KWARGS)
    percent = serializers.FloatField(allow_null=True)
    deficit = serializers.DecimalField(allow_null=True, **MONEY_FIELD_KWARGS)
    traffic_light = serializers.CharField(allow_null=True)
    target_shares = serializers.DecimalField(allow_null=True, **MONEY_FIELD_KWARGS)
    reached_shares = serializers.DecimalField(allow_null=True, **MONEY_FIELD_KWARGS)
    shares_percent = serializers.FloatField(allow_null=True)
    shares_deficit = serializers.DecimalField(allow_null=True, **MONEY_FIELD_KWARGS)
    shares_traffic_light = serializers.CharField(allow_null=True)


class RoundStatsEntrySerializer(RoundStatsTotalsSerializer):
    product_type_id = serializers.CharField()
    product_type_name = serializers.CharField()


class ExtraPositionSerializer(serializers.Serializer):
    label = serializers.CharField()
    reached_per_year = serializers.DecimalField(**MONEY_FIELD_KWARGS)
    applicable = serializers.BooleanField()


class ExtraPositionsSerializer(serializers.Serializer):
    membership = ExtraPositionSerializer()
    delivery_charge = ExtraPositionSerializer()


class AverageBidSerializer(serializers.Serializer):
    target_per_year = serializers.DecimalField(**MONEY_FIELD_KWARGS)
    capacity_shares = serializers.DecimalField(**MONEY_FIELD_KWARGS)
    amount_per_share_per_month = serializers.DecimalField(
        allow_null=True, **MONEY_FIELD_KWARGS
    )
    amount_per_share_per_year = serializers.DecimalField(
        allow_null=True, **MONEY_FIELD_KWARGS
    )


class FinancingProjectionLevelSerializer(serializers.Serializer):
    reached_per_year = serializers.DecimalField(**MONEY_FIELD_KWARGS)
    average_per_share_per_month = serializers.DecimalField(**MONEY_FIELD_KWARGS)


class FinancingProjectionLevelsSerializer(serializers.Serializer):
    green = FinancingProjectionLevelSerializer()
    yellow = FinancingProjectionLevelSerializer()
    red = FinancingProjectionLevelSerializer()


class FinancingProjectionSerializer(serializers.Serializer):
    target_per_year = serializers.DecimalField(**MONEY_FIELD_KWARGS)
    capacity_shares = serializers.DecimalField(**MONEY_FIELD_KWARGS)
    bid_shares = serializers.DecimalField(**MONEY_FIELD_KWARGS)
    auto_shares = serializers.DecimalField(**MONEY_FIELD_KWARGS)
    remaining_shares = serializers.DecimalField(**MONEY_FIELD_KWARGS)
    fixed_per_year = serializers.DecimalField(**MONEY_FIELD_KWARGS)
    auto_renew_per_year = serializers.DecimalField(**MONEY_FIELD_KWARGS)
    membership_per_year = serializers.DecimalField(**MONEY_FIELD_KWARGS)
    delivery_charge_per_year = serializers.DecimalField(**MONEY_FIELD_KWARGS)
    non_bidders_min_average = serializers.BooleanField()
    membership_included_in_product_type = serializers.BooleanField()
    levels = FinancingProjectionLevelsSerializer()


class AutoRenewedItemSerializer(serializers.Serializer):
    product_type_name = serializers.CharField()
    product_name = serializers.CharField()
    quantity = serializers.IntegerField()


class ResultsTableMemberSerializer(serializers.Serializer):
    member_id = serializers.CharField()
    member_name = serializers.CharField()
    member_email = serializers.CharField()
    has_bid = serializers.BooleanField()
    is_active_in_contract_period = serializers.BooleanField()
    is_auto_renewed = serializers.BooleanField()
    auto_renewed_items = AutoRenewedItemSerializer(many=True, required=False)
    auto_renewed_pickup_location_name = serializers.CharField(
        allow_null=True, required=False
    )
    auto_renewed_amount_per_year = serializers.DecimalField(
        allow_null=True, **MONEY_FIELD_KWARGS
    )
    auto_renewed_amount_per_month = serializers.DecimalField(
        allow_null=True, **MONEY_FIELD_KWARGS
    )
    bid = BidSerializer(allow_null=True)


class ResultsTablePickupLocationSerializer(serializers.Serializer):
    pickup_location_id = serializers.CharField()
    pickup_location_name = serializers.CharField()
    capacity = serializers.DecimalField(**MONEY_FIELD_KWARGS)
    demand = serializers.DecimalField(**MONEY_FIELD_KWARGS)
    fill_percent = serializers.FloatField(allow_null=True)


class ResultsTableSerializer(serializers.Serializer):
    members = ResultsTableMemberSerializer(many=True)
    pickup_locations = ResultsTablePickupLocationSerializer(many=True, required=False)


class ContractItemSerializer(serializers.Serializer):
    product_type_name = serializers.CharField()
    product_name = serializers.CharField()
    quantity = serializers.IntegerField()


class ContractRowSerializer(serializers.Serializer):
    member_id = serializers.CharField()
    member_name = serializers.CharField()
    member_email = serializers.CharField()
    type = serializers.CharField()
    items = ContractItemSerializer(many=True)
    pickup_location_name = serializers.CharField(allow_blank=True)
    standard_amount_per_month = serializers.DecimalField(**MONEY_FIELD_KWARGS)
    standard_amount_per_year = serializers.DecimalField(**MONEY_FIELD_KWARGS)
    contribution_amount_per_month = serializers.DecimalField(**MONEY_FIELD_KWARGS)
    contribution_amount_per_year = serializers.DecimalField(**MONEY_FIELD_KWARGS)
    amount_per_month = serializers.DecimalField(**MONEY_FIELD_KWARGS)
    amount_per_year = serializers.DecimalField(**MONEY_FIELD_KWARGS)
    is_created = serializers.BooleanField()


class RoundResultsResponseSerializer(serializers.Serializer):
    display_name = serializers.CharField()
    stats = RoundStatsEntrySerializer(many=True)
    totals = RoundStatsTotalsSerializer()
    extra_positions = ExtraPositionsSerializer()
    average_bid = AverageBidSerializer()
    include_auto_renewed = serializers.BooleanField()
    auto_renewed_enabled = serializers.BooleanField()
    bidding_procedure = serializers.CharField()
    bid_levels = serializers.IntegerField()
    recommended_level = serializers.IntegerField()
    traffic_light_position = serializers.FloatField()
    financing_projection = FinancingProjectionSerializer()
    results_table = ResultsTableSerializer()
    biddable_product = BiddableProductSerializer(allow_null=True)
    pickup_locations = PickupLocationWithChargeSerializer(many=True)
    bid_options = BidOptionsSerializer()
    contracts_created_at = serializers.DateTimeField(allow_null=True)
    average_bid_locked_at = serializers.DateTimeField(allow_null=True)
    locked_traffic_light_position = serializers.DecimalField(
        allow_null=True, **MONEY_FIELD_KWARGS
    )
    locked_average_bid_per_share_per_month = serializers.DecimalField(
        allow_null=True, **MONEY_FIELD_KWARGS
    )
    locked_average_bid_per_share_per_year = serializers.DecimalField(
        allow_null=True, **MONEY_FIELD_KWARGS
    )
    locked_bidder_average_per_share_per_month = serializers.DecimalField(
        allow_null=True, **MONEY_FIELD_KWARGS
    )
    locked_bidder_average_per_share_per_year = serializers.DecimalField(
        allow_null=True, **MONEY_FIELD_KWARGS
    )
    locked_surcharge_percent = serializers.DecimalField(**MONEY_FIELD_KWARGS)
    locked_surcharge_on_bids = serializers.BooleanField()
    locked_surcharge_on_average = serializers.BooleanField()
    growing_period_id = serializers.CharField(allow_null=True)
    contracts = ContractRowSerializer(many=True)


class PublicEvaluationLevelSerializer(serializers.Serializer):
    reached_per_year = serializers.DecimalField(**MONEY_FIELD_KWARGS)
    current_total_per_year = serializers.DecimalField(**MONEY_FIELD_KWARGS)
    current_coverage_percent = serializers.FloatField()
    bidder_average_per_month = serializers.DecimalField(**MONEY_FIELD_KWARGS)


class PublicEvaluationLevelsSerializer(serializers.Serializer):
    green = PublicEvaluationLevelSerializer()
    yellow = PublicEvaluationLevelSerializer()
    red = PublicEvaluationLevelSerializer()


class PublicEvaluationResponseSerializer(serializers.Serializer):
    bidding_procedure = serializers.CharField()
    bid_levels = serializers.IntegerField()
    recommended_level = serializers.IntegerField()
    traffic_light_position = serializers.DecimalField(**MONEY_FIELD_KWARGS)
    target_per_year = serializers.DecimalField(**MONEY_FIELD_KWARGS)
    capacity_shares = serializers.DecimalField(**MONEY_FIELD_KWARGS)
    current_shares = serializers.DecimalField(**MONEY_FIELD_KWARGS)
    utilization_percent = serializers.FloatField()
    levels = PublicEvaluationLevelsSerializer()


class CreateContractsErrorSerializer(serializers.Serializer):
    bid_id = serializers.UUIDField()
    member_id = serializers.CharField()
    member_name = serializers.CharField()
    product_name = serializers.CharField(allow_blank=True)
    error = serializers.CharField()


class CreateContractsSubscriptionSerializer(serializers.Serializer):
    id = serializers.CharField()
    member_id = serializers.CharField()
    product_id = serializers.CharField()


class CreateContractsResponseSerializer(serializers.Serializer):
    errors = CreateContractsErrorSerializer(many=True)
    subscriptions = CreateContractsSubscriptionSerializer(many=True)


class MemberBidResponseSerializer(serializers.Serializer):
    round = RoundSerializer()
    biddable_product = BiddableProductSerializer(allow_null=True)
    pickup_locations = PickupLocationWithChargeSerializer(many=True)
    bid = BidSerializer(allow_null=True)
