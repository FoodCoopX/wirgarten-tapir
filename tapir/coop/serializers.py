from rest_framework import serializers


class MinimumNumberOfSharesResponseSerializer(serializers.Serializer):
    minimum_number_of_shares = serializers.IntegerField()
