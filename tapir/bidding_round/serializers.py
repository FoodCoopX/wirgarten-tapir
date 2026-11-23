from rest_framework import serializers


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


class BidSubmitSerializer(serializers.Serializer):
    product_id = serializers.CharField()
    quantity = serializers.IntegerField(
        required=False, min_value=1, max_value=5, default=1
    )
    amount_1 = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class CreateContractsSerializer(serializers.Serializer):
    bid_ids = serializers.ListField(child=serializers.CharField(), required=False)


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
    status = serializers.CharField()
    start_at = serializers.DateTimeField(allow_null=True)
    end_at = serializers.DateTimeField()
    contracts_created_at = serializers.DateTimeField(allow_null=True)
    growing_period_id = serializers.CharField(allow_null=True)
    comment = serializers.CharField()
    has_bids = serializers.BooleanField()
    product = RoundProductSerializer(allow_null=True)


class BidSerializer(serializers.Serializer):
    id = serializers.CharField()
    member_id = serializers.CharField()
    pickup_location_id = serializers.CharField(allow_null=True)
    updated_at = serializers.DateTimeField(allow_null=True)
    product_id = serializers.CharField()
    product_name = serializers.CharField()
    quantity = serializers.IntegerField()
    amount_1 = serializers.CharField(allow_null=True)
    amount_per_year = serializers.CharField()
    total_per_year = serializers.CharField()


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


class RoundStatsBidSerializer(serializers.Serializer):
    bid_id = serializers.CharField()
    member_id = serializers.CharField()
    member_name = serializers.CharField()
    email = serializers.CharField()
    product_id = serializers.CharField()
    product_name = serializers.CharField()
    quantity = serializers.IntegerField()
    amount_1 = serializers.CharField(allow_null=True)
    amount_per_month = serializers.CharField()
    amount_per_year = serializers.CharField()


class RoundResultsResponseSerializer(serializers.Serializer):
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
