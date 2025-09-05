from rest_framework import serializers

from tapir.deliveries.serializers import (
    ProductSerializer,
    PickupLocationSerializer,
    SubscriptionSerializer,
)
from tapir.wirgarten.models import (
    WaitingListEntry,
    WaitingListProductWish,
    WaitingListPickupLocationWish,
)


class WaitingListProductWishSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaitingListProductWish
        fields = "__all__"

    product = ProductSerializer()


class WaitingListPickupLocationWishSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaitingListPickupLocationWish
        fields = "__all__"

    pickup_location = PickupLocationSerializer()


class WaitingListEntryDetailsSerializer(serializers.Serializer):
    id = serializers.CharField()
    link_key = serializers.CharField(required=False)
    member_no = serializers.IntegerField()
    member_already_exists = serializers.BooleanField()
    url_to_member_profile = serializers.CharField(required=False)
    waiting_since = serializers.DateTimeField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    phone_number = serializers.CharField()
    street = serializers.CharField()
    street_2 = serializers.CharField()
    postcode = serializers.CharField()
    city = serializers.CharField()
    country = serializers.CharField()
    birthdate = serializers.DateField(required=False)
    account_owner = serializers.CharField(required=False)
    iban = serializers.CharField(required=False)
    date_of_entry_in_cooperative = serializers.DateField(required=False)
    current_pickup_location = PickupLocationSerializer(required=False)
    current_products = ProductSerializer(required=False, many=True)
    pickup_location_wishes = WaitingListPickupLocationWishSerializer(
        required=False, many=True
    )
    product_wishes = WaitingListProductWishSerializer(required=False, many=True)
    desired_start_date = serializers.DateField(required=False)
    number_of_coop_shares = serializers.IntegerField()
    comment = serializers.CharField()
    category = serializers.CharField(required=False)
    current_subscriptions = SubscriptionSerializer(many=True, required=False)
    link_sent_date = serializers.DateTimeField(required=False)
    link = serializers.URLField(required=False)
    payment_rhythm = serializers.CharField(required=False)


class OptionalWaitingListEntryDetailsSerializer(serializers.Serializer):
    entry = WaitingListEntryDetailsSerializer(required=False)


class WaitingListEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = WaitingListEntry
        fields = "__all__"


class WaitingListEntryUpdateSerializer(serializers.Serializer):
    id = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    phone_number = serializers.CharField()
    street = serializers.CharField()
    street_2 = serializers.CharField(allow_blank=True)
    postcode = serializers.CharField()
    city = serializers.CharField()
    pickup_location_ids = serializers.ListField(child=serializers.CharField())
    shopping_cart = serializers.DictField(child=serializers.IntegerField())
    desired_start_date = serializers.DateField(required=False)
    comment = serializers.CharField(allow_blank=True)
    category = serializers.CharField(required=False, allow_blank=True)


class PublicWaitingListEntryNewMemberCreateSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    phone_number = serializers.CharField()
    street = serializers.CharField()
    street_2 = serializers.CharField(allow_blank=True)
    postcode = serializers.CharField()
    city = serializers.CharField()
    pickup_location_ids = serializers.ListField(child=serializers.CharField())
    shopping_cart = serializers.DictField(child=serializers.IntegerField())
    number_of_coop_shares = serializers.IntegerField()


class PublicWaitingListEntryExistingMemberCreateSerializer(serializers.Serializer):
    pickup_location_ids = serializers.ListField(child=serializers.CharField())
    shopping_cart = serializers.DictField(child=serializers.IntegerField())
    member_id = serializers.CharField()


class PublicConfirmWaitingListEntryRequestSerializer(serializers.Serializer):
    entry_id = serializers.CharField()
    link_key = serializers.CharField()
    birthdate = serializers.DateField()
    account_owner = serializers.CharField(allow_blank=True)
    iban = serializers.CharField(allow_blank=True)
    sepa_allowed = serializers.BooleanField()
    contract_accepted = serializers.BooleanField()
    number_of_coop_shares = serializers.IntegerField()
    payment_rhythm = serializers.CharField()
