from rest_framework import serializers

from tapir.deliveries.serializers import ProductSerializer, PickupLocationSerializer


class WaitingListEntrySerializer(serializers.Serializer):
    id = serializers.CharField()
    member_no = serializers.IntegerField()
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
    date_of_entry_in_cooperative = serializers.DateField(required=False)
    current_pickup_location = PickupLocationSerializer(required=False)
    current_products = ProductSerializer(required=False, many=True)
    pickup_location_wishes = PickupLocationSerializer(required=False, many=True)
    product_wishes = ProductSerializer(required=False, many=True)
    desired_start_date = serializers.DateField(required=False)
    number_of_coop_shares = serializers.IntegerField()
