from rest_framework import serializers

from tapir.subscriptions.serializers import CoopShareTransactionSerializer


class MinimumNumberOfSharesResponseSerializer(serializers.Serializer):
    minimum_number_of_shares = serializers.IntegerField()


class GetCoopShareTransactionsResponseSerializer(serializers.Serializer):
    transactions = CoopShareTransactionSerializer(many=True)
    url_of_bestell_wizard = serializers.URLField()


class ExistingMemberPurchasesSharesRequestSerializer(serializers.Serializer):
    member_id = serializers.CharField()
    number_of_shares_to_add = serializers.IntegerField()
    iban = serializers.CharField(required=False)
    account_owner = serializers.CharField(required=False)
    as_admin = serializers.BooleanField()
    start_date = serializers.DateField(required=False)
