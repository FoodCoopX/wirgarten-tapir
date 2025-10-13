from rest_framework import serializers

from tapir.deliveries.serializers import SubscriptionSerializer
from tapir.payments.models import MemberPaymentRhythm, MemberCredit
from tapir.subscriptions.serializers import (
    CoopShareTransactionSerializer,
    MemberSerializer,
)
from tapir.wirgarten.models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"

    amount = serializers.FloatField()


class ExtendedPaymentSerializer(serializers.Serializer):
    payment = PaymentSerializer()
    subscriptions = SubscriptionSerializer(many=True)
    coop_share_transactions = CoopShareTransactionSerializer(many=True)


class MemberCreditSerializer(serializers.ModelSerializer):
    class Meta:
        model = MemberCredit
        fields = "__all__"

    amount = serializers.FloatField()


class ExtendedMemberCreditSerializer(serializers.Serializer):
    credit = MemberCreditSerializer()
    member = MemberSerializer()
    member_url = serializers.URLField()
    mandate_ref = serializers.CharField()


class FuturePaymentsResponseSerializer(serializers.Serializer):
    payments = ExtendedPaymentSerializer(many=True)
    credits = MemberCreditSerializer(many=True)


class MemberPaymentRhythmSerializer(serializers.ModelSerializer):
    class Meta:
        model = MemberPaymentRhythm
        fields = "__all__"


class MemberPaymentRhythmDataSerializer(serializers.Serializer):
    current_rhythm = serializers.CharField()
    date_of_next_rhythm_change = serializers.DateField()
    allowed_rhythms = serializers.DictField(child=serializers.CharField())
    rhythm_history = MemberPaymentRhythmSerializer(many=True)

class MemberCreditCreateSerializer(serializers.Serializer):
    due_date = serializers.DateField()
    member_id = serializers.CharField()
    amount = serializers.FloatField()
    purpose = serializers.CharField()
    comment = serializers.CharField()