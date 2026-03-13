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


class MemberBankDataResponseSerializer(serializers.Serializer):
    iban = serializers.CharField()
    account_owner = serializers.CharField()
    organisation_name = serializers.CharField()


class UpdateMemberBankDataRequestSerializer(serializers.Serializer):
    member_id = serializers.CharField()
    iban = serializers.CharField()
    account_owner = serializers.CharField()
    sepa_consent = serializers.BooleanField()


class MemberProfilePersonalDataResponseSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    phone_number = serializers.CharField()
    street = serializers.CharField()
    street_2 = serializers.CharField(allow_blank=True)
    postcode = serializers.CharField()
    city = serializers.CharField()
    is_student = serializers.BooleanField(required=False)
    can_edit_student = serializers.BooleanField()


class MemberProfilePersonalDataRequestSerializer(serializers.Serializer):
    member_id = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    phone_number = serializers.CharField()
    street = serializers.CharField()
    street_2 = serializers.CharField(allow_blank=True)
    postcode = serializers.CharField()
    city = serializers.CharField()
    is_student = serializers.BooleanField(required=False)
