from rest_framework import serializers

from tapir.subscriptions.serializers import CoopShareTransactionSerializer


class MinimumNumberOfSharesResponseSerializer(serializers.Serializer):
    minimum_number_of_shares = serializers.IntegerField()


class GetCoopShareTransactionsResponseSerializer(serializers.Serializer):
    transactions = CoopShareTransactionSerializer(many=True)
    url_of_bestell_wizard = serializers.URLField()
