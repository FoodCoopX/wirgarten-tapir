from rest_framework import serializers

from tapir.deliveries.serializers import ProductSerializer, PickupLocationSerializer


class WaitingListEntrySerializer(serializers.Serializer):
    member_no = serializers.IntegerField()
    waiting_since = serializers.DateTimeField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email_address = serializers.EmailField()
    phone_number = serializers.CharField()
    street = serializers.CharField()
    street_2 = serializers.CharField()
    post_code = serializers.CharField()
    city = serializers.CharField()
    country = serializers.CharField()
    date_of_entry_in_cooperative = serializers.DateField()
    product = ProductSerializer(required=False)
    current_pickup_location = PickupLocationSerializer(required=False)
    pickup_location_wishes = PickupLocationSerializer(required=False, many=True)
    desired_start_date = serializers.DateField()
