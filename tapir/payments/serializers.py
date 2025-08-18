from rest_framework import serializers

from tapir.wirgarten.models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"

    amount = serializers.FloatField()
