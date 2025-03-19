from rest_framework import serializers


class CancellationDataSerializer(serializers.Serializer):
    is_in_trial = serializers.BooleanField()
    subscription_end_date = serializers.DateField(required=False)
