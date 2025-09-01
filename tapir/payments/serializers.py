from rest_framework import serializers

from tapir.deliveries.serializers import SubscriptionSerializer
from tapir.payments.models import MemberPaymentRhythm
from tapir.subscriptions.serializers import CoopShareTransactionSerializer
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


class MemberPaymentRhythmSerializer(serializers.ModelSerializer):
    class Meta:
        model = MemberPaymentRhythm
        fields = "__all__"


class MemberPaymentRhythmDataSerializer(serializers.Serializer):
    current_rhythm = serializers.CharField()
    date_of_next_rhythm_change = serializers.DateField()
    allowed_rhythms = serializers.DictField(child=serializers.CharField())
    rhythm_history = MemberPaymentRhythmSerializer(many=True)
