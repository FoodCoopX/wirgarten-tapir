from decimal import Decimal

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from tapir.bidding_round.config import OPTIONS_BIDDING_ROUND_PROCEDURE
from tapir.bidding_round.models import Bid, BiddingRound
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


class BidSubmitSerializer(serializers.Serializer):
    product_id = serializers.CharField()
    quantity = serializers.IntegerField(
        required=False, min_value=1, max_value=5, default=1
    )
    amount_1 = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    amount_2 = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    amount_3 = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class CreateContractsSerializer(serializers.Serializer):
    bid_ids = serializers.ListField(child=serializers.CharField(), required=False)
    bid_level = serializers.IntegerField(required=False, min_value=1, max_value=3)


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
    status = serializers.CharField()
    bidding_procedure = serializers.CharField()
    bid_levels = serializers.IntegerField()
    start_at = serializers.DateTimeField(allow_null=True)
    end_at = serializers.DateTimeField()
    contracts_created_at = serializers.DateTimeField(allow_null=True)
    growing_period_id = serializers.CharField(allow_null=True)
    comment = serializers.CharField()
    has_bids = serializers.SerializerMethodField()
    product = RoundProductSerializer(source="*", allow_null=True)

    class Meta:
        model = BiddingRound
        fields = [
            "id",
            "name",
            "status",
            "bidding_procedure",
            "bid_levels",
            "start_at",
            "end_at",
            "contracts_created_at",
            "growing_period_id",
            "comment",
            "has_bids",
            "product",
        ]

    @extend_schema_field(serializers.BooleanField())
    def get_has_bids(self, bidding_round):
        if hasattr(bidding_round, "has_bids"):
            return bidding_round.has_bids
        return bidding_round.bids.exists()


class BidSerializer(serializers.ModelSerializer):
    id = serializers.CharField()
    member_id = serializers.CharField()
    pickup_location_id = serializers.SerializerMethodField()
    product_id = serializers.CharField()
    product_name = serializers.CharField(source="product.name")
    amount_1 = serializers.DecimalField(max_digits=8, decimal_places=2, allow_null=True)
    updated_at = serializers.DateTimeField(allow_null=True)
    quantity = serializers.IntegerField()
    amount_2 = serializers.DecimalField(max_digits=8, decimal_places=2, allow_null=True)
    amount_3 = serializers.DecimalField(max_digits=8, decimal_places=2, allow_null=True)
    amount_per_year = serializers.SerializerMethodField()
    total_per_year = serializers.SerializerMethodField()

    class Meta:
        model = Bid
        fields = [
            "id",
            "member_id",
            "pickup_location_id",
            "updated_at",
            "product_id",
            "product_name",
            "quantity",
            "amount_1",
            "amount_2",
            "amount_3",
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

    def get_amount_per_year(self, bid):
        from tapir.bidding_round.services.bidding_round_stats_service import (
            BiddingRoundStatsService,
        )

        return str(
            BiddingRoundStatsService.get_counting_amount(bid) * bid.quantity * 12
        )

    def get_total_per_year(self, bid):
        return self.get_amount_per_year(bid)


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
    submit_label = serializers.CharField()
    bid = BidTextsSerializer()


class PublicDataResponseSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
    url_enabled = serializers.BooleanField(required=False)
    url = serializers.CharField(allow_null=True, required=False)
    round = RoundSerializer(allow_null=True, required=False)
    round_status = serializers.CharField(required=False)
    texts = RoundTextsSerializer(required=False)
    biddable_product = BiddableProductSerializer(allow_null=True, required=False)
    is_authenticated = serializers.BooleanField(required=False)
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


class RoundStatsBidSerializer(serializers.ModelSerializer):
    bid_id = serializers.CharField(source="id")
    member_id = serializers.CharField()
    member_name = serializers.CharField(source="member")
    email = serializers.CharField(source="member.email")
    product_id = serializers.CharField()
    product_name = serializers.CharField(source="product.name")
    quantity = serializers.IntegerField()
    amount_1 = serializers.DecimalField(max_digits=8, decimal_places=2, allow_null=True)
    amount_2 = serializers.DecimalField(max_digits=8, decimal_places=2, allow_null=True)
    amount_3 = serializers.DecimalField(max_digits=8, decimal_places=2, allow_null=True)
    amount_per_month = serializers.SerializerMethodField()
    amount_per_year = serializers.SerializerMethodField()

    class Meta:
        model = Bid
        fields = [
            "bid_id",
            "member_id",
            "member_name",
            "email",
            "product_id",
            "product_name",
            "quantity",
            "amount_1",
            "amount_2",
            "amount_3",
            "amount_per_month",
            "amount_per_year",
        ]

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
        from tapir.bidding_round.services.bidding_round_stats_service import (
            BiddingRoundStatsService,
        )

        return str(
            BiddingRoundStatsService.get_bid_monthly_amount(
                bid, self.context.get("position"), bid.round
            )
            * 12
        )


class EvaluationLevelSerializer(serializers.Serializer):
    reached_per_year = serializers.CharField()
    coverage_percent = serializers.FloatField()
    coverage_status = serializers.CharField()
    bidder_average_per_month = serializers.CharField()


class EvaluationLevelsSerializer(serializers.Serializer):
    green = EvaluationLevelSerializer()
    yellow = EvaluationLevelSerializer(required=False)
    red = EvaluationLevelSerializer()


class RoundResultsResponseSerializer(serializers.Serializer):
    bidding_procedure = serializers.CharField()
    bid_levels = serializers.IntegerField()
    bid_range_position = serializers.FloatField()
    recommended_level = serializers.IntegerField()
    coverage_status = serializers.CharField()
    levels = EvaluationLevelsSerializer()
    target_per_year = serializers.CharField()
    reached_per_year = serializers.CharField()
    coverage_percent = serializers.FloatField()
    bidder_count = serializers.IntegerField()
    bidder_average_per_month = serializers.CharField()
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
