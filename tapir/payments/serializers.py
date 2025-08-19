from rest_framework import serializers

from tapir.deliveries.serializers import SubscriptionSerializer
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
