from decimal import Decimal

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from tapir.bidding_round.config import OPTIONS_BIDDING_ROUND_PROCEDURE
from tapir.bidding_round.models import Bid, BiddingRound
from tapir.pickup_locations.serializers import PublicPickupLocationSerializer
from tapir.wirgarten.models import Product


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


class BidSubmitSerializer(serializers.Serializer):
    product_id = serializers.CharField()
    quantity = serializers.IntegerField(
        required=False, min_value=1, max_value=5, default=1
    )
    amount_1 = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    amount_2 = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    amount_3 = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    sepa_allowed = serializers.BooleanField(required=False, default=False)
    account_owner = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    iban = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    payment_rhythm = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    privacy_policy_read = serializers.BooleanField(required=False, default=False)
    cancellation_policy_read = serializers.BooleanField(required=False, default=False)
    contract_accepted = serializers.BooleanField(required=False, default=False)
    feedback = serializers.CharField(allow_blank=True, required=False)


class BidAdminSerializer(serializers.Serializer):
    product_id = serializers.CharField(required=False)
    quantity = serializers.IntegerField(required=False, min_value=1, max_value=5)
    amount_1 = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    amount_2 = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    amount_3 = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    entered_by_admin = serializers.BooleanField(required=False)
    admin_confirmed = serializers.BooleanField(required=False)


class BidAdminCreateSerializer(BidAdminSerializer):
    member_id = serializers.CharField()
    product_id = serializers.CharField()


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
    create_auto_renewed_contracts = serializers.BooleanField(
        required=False, default=False
    )
    auto_renewed_member_ids = serializers.ListField(
        child=serializers.CharField(), required=False
    )


class CheckContractsSerializer(serializers.Serializer):
    bid_ids = serializers.ListField(child=serializers.CharField(), required=False)


class StandardPriceAlignResultSerializer(serializers.Serializer):
    product_id = serializers.CharField()
    product_name = serializers.CharField()
    price = serializers.CharField()
    valid_from = serializers.DateField()


class StandardPriceAlignResponseSerializer(serializers.Serializer):
    results = StandardPriceAlignResultSerializer(many=True)


class RollbackMembersSerializer(serializers.Serializer):
    member_ids = serializers.ListField(child=serializers.CharField(), required=False)
    all = serializers.BooleanField(required=False, default=False)
    force = serializers.BooleanField(required=False, default=False)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate(self, attrs):
        has_selection = bool(attrs.get("member_ids"))
        if attrs.get("all") == has_selection:
            raise serializers.ValidationError(
                "Genau eines von all oder member_ids angeben."
            )
        if attrs.get("force") and not attrs.get("reason", "").strip():
            raise serializers.ValidationError(
                "Eine erzwungene Rücknahme braucht eine Begründung."
            )
        return attrs


class RollbackResultSerializer(serializers.Serializer):
    member_id = serializers.CharField()
    member_name = serializers.CharField()
    state = serializers.CharField()
    subscriptions_deleted = serializers.IntegerField()
    subscriptions_restored = serializers.IntegerField()
    contributions_restored = serializers.IntegerField()
    detail = serializers.CharField()


class RoundProductPriceSerializer(serializers.Serializer):
    product_id = serializers.CharField()
    product_name = serializers.CharField()
    reference_value = serializers.CharField(allow_null=True)
    min_amount = serializers.CharField(allow_null=True)
    size = serializers.CharField(allow_null=True)


class RoundProductSerializer(serializers.ModelSerializer):
    product_type_id = serializers.CharField()
    product_type_name = serializers.CharField(source="product_type.name")
    target_amount_per_year = serializers.CharField(allow_null=True)
    prices = serializers.SerializerMethodField()

    class Meta:
        model = BiddingRound
        fields = [
            "product_type_id",
            "product_type_name",
            "target_amount_per_year",
            "prices",
        ]

    @extend_schema_field(RoundProductPriceSerializer(many=True))
    def get_prices(self, bidding_round):
        prices_by_product = {
            price.product_id: price for price in bidding_round.prices.all()
        }
        products = Product.objects.filter(
            type_id=bidding_round.product_type_id, deleted=False
        )
        rows = []
        for product in products:
            price = prices_by_product.get(product.id)
            rows.append(
                {
                    "product_id": product.id,
                    "product_name": product.name,
                    "reference_value": (
                        str(price.reference_value)
                        if price is not None and price.reference_value is not None
                        else None
                    ),
                    "min_amount": (
                        str(price.min_amount)
                        if price is not None and price.min_amount is not None
                        else None
                    ),
                    "size": (
                        str(price.size)
                        if price is not None and price.size is not None
                        else None
                    ),
                }
            )
        return RoundProductPriceSerializer(rows, many=True).data


class RoundSerializer(serializers.ModelSerializer):
    id = serializers.CharField()
    name = serializers.CharField()
    display_name = serializers.SerializerMethodField()
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
    has_bids = serializers.SerializerMethodField()
    rollback_available = serializers.SerializerMethodField()
    rollback_untracked = serializers.SerializerMethodField()
    product = RoundProductSerializer(source="*", allow_null=True)

    class Meta:
        model = BiddingRound
        fields = [
            "id",
            "name",
            "display_name",
            "status",
            "bidding_procedure",
            "bid_levels",
            "include_auto_renewed",
            "average_bid_locked_at",
            "locked_bid_range_position",
            "locked_bidder_average_per_share_per_month",
            "locked_surcharge_percent",
            "locked_surcharge_on_bids",
            "locked_surcharge_on_average",
            "start_at",
            "end_at",
            "contracts_created_at",
            "growing_period_id",
            "comment",
            "has_bids",
            "rollback_available",
            "rollback_untracked",
            "product",
        ]

    def get_display_name(self, bidding_round):
        return self.context.get("display_name")

    @extend_schema_field(serializers.BooleanField())
    def get_has_bids(self, bidding_round):
        if hasattr(bidding_round, "has_bids"):
            return bidding_round.has_bids
        return bidding_round.bids.exists()

    def get_rollback_available(self, bidding_round):
        return self.context.get("rollback_available", False)

    def get_rollback_untracked(self, bidding_round):
        return self.context.get("rollback_untracked", False)


class RollbackMembersResponseSerializer(RoundSerializer):
    results = RollbackResultSerializer(many=True)

    class Meta(RoundSerializer.Meta):
        fields = RoundSerializer.Meta.fields + ["results"]


class BidSerializer(serializers.ModelSerializer):
    id = serializers.CharField()
    member_id = serializers.CharField()
    entered_by_admin = serializers.BooleanField()
    admin_confirmed = serializers.DateTimeField(allow_null=True)
    pickup_location_id = serializers.SerializerMethodField()
    pickup_location_name = serializers.SerializerMethodField()
    product_id = serializers.CharField()
    product_name = serializers.CharField(source="product.name")
    amount_1 = serializers.DecimalField(max_digits=8, decimal_places=2, allow_null=True)
    updated_at = serializers.DateTimeField(allow_null=True)
    quantity = serializers.IntegerField()
    amount_2 = serializers.DecimalField(max_digits=8, decimal_places=2, allow_null=True)
    amount_3 = serializers.DecimalField(max_digits=8, decimal_places=2, allow_null=True)
    effective_amount = serializers.SerializerMethodField()
    amount_per_year = serializers.SerializerMethodField()
    total_per_year = serializers.SerializerMethodField()

    class Meta:
        model = Bid
        fields = [
            "id",
            "member_id",
            "entered_by_admin",
            "admin_confirmed",
            "pickup_location_id",
            "pickup_location_name",
            "updated_at",
            "product_id",
            "product_name",
            "quantity",
            "amount_1",
            "amount_2",
            "amount_3",
            "effective_amount",
            "amount_per_year",
            "total_per_year",
        ]

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_pickup_location_id(self, bid):
        from tapir.pickup_locations.services.member_pickup_location_getter import (
            MemberPickupLocationGetter,
        )

        return MemberPickupLocationGetter.get_member_pickup_location_id_from_cache(
            member_id=bid.member_id,
            reference_date=bid.round.growing_period.start_date,
            cache=self.context.get("cache", {}),
        )

    def get_pickup_location_name(self, bid):
        from tapir.pickup_locations.services.member_pickup_location_getter import (
            MemberPickupLocationGetter,
        )

        pickup_location = MemberPickupLocationGetter.get_member_pickup_location(
            member=bid.member,
            reference_date=bid.round.growing_period.start_date,
            cache=self.context.get("cache", {}),
        )
        return pickup_location.name if pickup_location is not None else None

    def get_effective_amount(self, bid):
        from tapir.bidding_round.services.bidding_round_stats_service import (
            BiddingRoundStatsService,
        )

        return str(
            BiddingRoundStatsService.get_bid_monthly_amount(
                bid, self.context.get("position"), bid.round
            )
        )

    def get_amount_per_year(self, bid):
        return str(Decimal(self.get_effective_amount(bid)) * 12)

    def get_total_per_year(self, bid):
        return self.get_amount_per_year(bid)


class BidProductVariantSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    reference_value = serializers.CharField(allow_null=True)
    min_amount = serializers.CharField(allow_null=True)
    standard_price = serializers.CharField(allow_null=True)
    size = serializers.CharField(allow_null=True)
    current_quantity = serializers.IntegerField(allow_null=True)
    image_url = serializers.CharField(allow_null=True)


class BiddableProductSerializer(serializers.Serializer):
    id = serializers.CharField()
    product_type_id = serializers.CharField()
    product_type_name = serializers.CharField()
    capacity_id = serializers.CharField(allow_null=True)
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
    privacy_title = serializers.CharField()
    pickup_location_title = serializers.CharField()
    submit_label = serializers.CharField()
    final_submit_label = serializers.CharField()
    bid = BidTextsSerializer()


class CurrentPickupLocationSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    yearly_delivery_charge = serializers.CharField()


class BidOptionsSerializer(serializers.Serializer):
    quantity_enabled = serializers.BooleanField()
    carousel_enabled = serializers.BooleanField()


class PublicAssociationMembershipSerializer(serializers.Serializer):
    name = serializers.CharField()
    price = serializers.DecimalField(max_digits=8, decimal_places=2)


class PublicDataResponseSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
    url_enabled = serializers.BooleanField(required=False)
    url = serializers.CharField(allow_null=True, required=False)
    round = RoundSerializer(allow_null=True, required=False)
    round_status = serializers.CharField(required=False)
    texts = RoundTextsSerializer(required=False)
    biddable_product = BiddableProductSerializer(allow_null=True, required=False)
    is_authenticated = serializers.BooleanField(required=False)
    status_enabled = serializers.BooleanField(required=False)
    status_public_enabled = serializers.BooleanField(required=False)
    sepa_enabled = serializers.BooleanField(required=False)
    feedback_enabled = serializers.BooleanField(required=False)
    first_name = serializers.CharField(required=False, allow_null=True)
    association_membership = PublicAssociationMembershipSerializer(
        allow_null=True, required=False
    )
    account_owner = serializers.CharField(required=False, allow_null=True)
    iban = serializers.CharField(required=False, allow_null=True)
    payment_rhythm = serializers.CharField(required=False, allow_null=True)
    current_pickup_location = CurrentPickupLocationSerializer(
        allow_null=True, required=False
    )
    bid = BidSerializer(allow_null=True, required=False)
    bid_options = BidOptionsSerializer(required=False)


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


class RoundStatsBidSerializer(serializers.ModelSerializer):
    bid_id = serializers.CharField(source="id")
    member_id = serializers.CharField()
    member_name = serializers.CharField(source="member")
    email = serializers.CharField(source="member.email")
    pickup_location_name = serializers.SerializerMethodField()
    product_id = serializers.CharField()
    product_name = serializers.CharField(source="product.name")
    quantity = serializers.IntegerField()
    amount_1 = serializers.DecimalField(max_digits=8, decimal_places=2, allow_null=True)
    amount_2 = serializers.DecimalField(max_digits=8, decimal_places=2, allow_null=True)
    amount_3 = serializers.DecimalField(max_digits=8, decimal_places=2, allow_null=True)
    entered_by_admin = serializers.BooleanField()
    admin_confirmed = serializers.DateTimeField(allow_null=True)
    updated_at = serializers.DateTimeField(allow_null=True)
    effective_amount = serializers.SerializerMethodField()
    amount_per_month = serializers.SerializerMethodField()
    amount_per_year = serializers.SerializerMethodField()

    class Meta:
        model = Bid
        fields = [
            "bid_id",
            "member_id",
            "member_name",
            "email",
            "pickup_location_name",
            "product_id",
            "product_name",
            "quantity",
            "amount_1",
            "amount_2",
            "amount_3",
            "entered_by_admin",
            "admin_confirmed",
            "updated_at",
            "effective_amount",
            "amount_per_month",
            "amount_per_year",
        ]

    def get_pickup_location_name(self, bid):
        from tapir.pickup_locations.services.member_pickup_location_getter import (
            MemberPickupLocationGetter,
        )

        pickup_location = MemberPickupLocationGetter.get_member_pickup_location(
            member=bid.member,
            reference_date=bid.round.growing_period.start_date,
            cache=self.context.get("cache", {}),
        )
        return pickup_location.name if pickup_location is not None else None

    def get_effective_amount(self, bid):
        return self.get_amount_per_month(bid)

    def get_amount_per_month(self, bid):
        from tapir.bidding_round.services.bidding_round_stats_service import (
            BiddingRoundStatsService,
        )

        return str(
            BiddingRoundStatsService.get_bid_monthly_amount(
                bid, self.context.get("position"), bid.round
            )
        )

    def get_amount_per_year(self, bid):
        return str(Decimal(self.get_amount_per_month(bid)) * 12)


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


class AutoRenewedItemSerializer(serializers.Serializer):
    product_type_name = serializers.CharField()
    product_name = serializers.CharField()
    quantity = serializers.IntegerField()


class AutoRenewedMemberSerializer(serializers.Serializer):
    member_id = serializers.CharField()
    member_name = serializers.CharField()
    member_email = serializers.CharField()
    items = AutoRenewedItemSerializer(many=True)
    pickup_location_id = serializers.CharField(allow_null=True)
    pickup_location_name = serializers.CharField(allow_null=True)
    shares = serializers.CharField()
    euro_per_year = serializers.CharField()
    euro_per_month = serializers.CharField()
    monthly_reference = serializers.CharField()
    yearly_reference = serializers.CharField()


class ExtraPositionSerializer(serializers.Serializer):
    label = serializers.CharField()
    reached_per_year = serializers.CharField()
    applicable = serializers.BooleanField()


class ExtraPositionsSerializer(serializers.Serializer):
    membership = ExtraPositionSerializer()
    delivery_charge = ExtraPositionSerializer()


class RoundStatsTotalsSerializer(serializers.Serializer):
    target_per_year = serializers.CharField(allow_null=True)
    reached_per_year = serializers.CharField(allow_null=True)
    percent = serializers.FloatField(allow_null=True)
    deficit = serializers.CharField(allow_null=True)
    coverage_status = serializers.CharField(allow_null=True)
    target_shares = serializers.CharField(allow_null=True)
    reached_shares = serializers.CharField(allow_null=True)
    shares_percent = serializers.FloatField(allow_null=True)
    shares_deficit = serializers.CharField(allow_null=True)
    shares_coverage_status = serializers.CharField(allow_null=True)


class RoundStatsEntrySerializer(RoundStatsTotalsSerializer):
    product_type_id = serializers.CharField()
    product_type_name = serializers.CharField()


class AverageBidSerializer(serializers.Serializer):
    target_per_year = serializers.CharField()
    capacity_shares = serializers.CharField()
    amount_per_share_per_month = serializers.CharField(allow_null=True)
    amount_per_share_per_year = serializers.CharField(allow_null=True)


class FinancingProjectionLevelSerializer(serializers.Serializer):
    reached_per_year = serializers.CharField()
    average_per_share_per_month = serializers.CharField()


class FinancingProjectionLevelsSerializer(serializers.Serializer):
    green = FinancingProjectionLevelSerializer()
    yellow = FinancingProjectionLevelSerializer()
    red = FinancingProjectionLevelSerializer()


class FinancingProjectionSerializer(serializers.Serializer):
    target_per_year = serializers.CharField()
    capacity_shares = serializers.CharField()
    bid_shares = serializers.CharField()
    auto_shares = serializers.CharField()
    remaining_shares = serializers.CharField()
    fixed_per_year = serializers.CharField()
    auto_renew_per_year = serializers.CharField()
    membership_per_year = serializers.CharField()
    delivery_charge_per_year = serializers.CharField()
    membership_included_in_product_type = serializers.BooleanField()
    levels = FinancingProjectionLevelsSerializer()


class ResultsTableMemberSerializer(serializers.Serializer):
    member_id = serializers.CharField()
    member_name = serializers.CharField()
    member_email = serializers.CharField()
    has_bid = serializers.BooleanField()
    is_active_in_contract_period = serializers.BooleanField()
    is_auto_renewed = serializers.BooleanField()
    auto_renewed_items = AutoRenewedItemSerializer(many=True)
    auto_renewed_pickup_location_name = serializers.CharField(allow_null=True)
    auto_renewed_amount_per_year = serializers.CharField(allow_null=True)
    auto_renewed_amount_per_month = serializers.CharField(allow_null=True)
    bid = BidSerializer(allow_null=True)


class ResultsTablePickupLocationSerializer(serializers.Serializer):
    pickup_location_id = serializers.CharField()
    pickup_location_name = serializers.CharField()
    capacity = serializers.CharField()
    demand = serializers.CharField()
    fill_percent = serializers.FloatField(allow_null=True)


class ResultsTableSerializer(serializers.Serializer):
    members = ResultsTableMemberSerializer(many=True)
    pickup_locations = ResultsTablePickupLocationSerializer(many=True)


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
    standard_amount_per_month = serializers.CharField()
    standard_amount_per_year = serializers.CharField()
    contribution_amount_per_month = serializers.CharField()
    contribution_amount_per_year = serializers.CharField()
    amount_per_month = serializers.CharField()
    amount_per_year = serializers.CharField()
    bid_amounts = serializers.ListField(child=serializers.CharField(), required=False)
    bid_effective_amount = serializers.CharField(allow_null=True)
    non_bidder_floor_per_month = serializers.CharField(allow_null=True)
    previous_amount_per_month = serializers.CharField(allow_null=True)
    is_created = serializers.BooleanField()
    rollback_state = serializers.CharField()


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


class RoundResultsResponseSerializer(EvaluationAggregatesSerializer):
    display_name = serializers.CharField()
    stats = RoundStatsEntrySerializer(many=True)
    totals = RoundStatsTotalsSerializer()
    average_bid = AverageBidSerializer()
    auto_renewed_enabled = serializers.BooleanField()
    financing_projection = FinancingProjectionSerializer()
    results_table = ResultsTableSerializer()
    biddable_product = BiddableProductSerializer(allow_null=True)
    pickup_locations = PickupLocationWithChargeSerializer(many=True)
    bid_options = BidOptionsSerializer()
    contracts = ContractRowSerializer(many=True)
    growing_period_id = serializers.CharField(allow_null=True)
    contracts_created_at = serializers.DateTimeField(allow_null=True)
    rollback_available = serializers.BooleanField()
    rollback_untracked = serializers.BooleanField()
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
    product_name = serializers.CharField(allow_blank=True)
    error = serializers.CharField()


class CreateContractsSubscriptionSerializer(serializers.Serializer):
    id = serializers.CharField()
    member_id = serializers.CharField()
    product_id = serializers.CharField()


class CreateContractsResponseSerializer(serializers.Serializer):
    errors = CreateContractsErrorSerializer(many=True)
    subscriptions = CreateContractsSubscriptionSerializer(many=True)
