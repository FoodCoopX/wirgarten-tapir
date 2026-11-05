from rest_framework import serializers


class DepositConfigurationSerializer(serializers.Serializer):
    instalments_enabled = serializers.BooleanField()
    instalment_count = serializers.IntegerField()
    enabled = serializers.BooleanField()
    name = serializers.CharField()
    minimum = serializers.DecimalField(max_digits=8, decimal_places=2)
    increment = serializers.DecimalField(max_digits=8, decimal_places=2)
    supporters_required = serializers.BooleanField()
    allow_extra_signup = serializers.BooleanField()
    allow_extra_member = serializers.BooleanField()
    allow_hardship = serializers.BooleanField()
    hardship_label = serializers.CharField()
    hardship_text = serializers.CharField()


class DepositPaymentSerializer(serializers.Serializer):
    id = serializers.CharField()
    amount = serializers.DecimalField(max_digits=8, decimal_places=2)
    due_date = serializers.DateField()
    exported = serializers.BooleanField()
    instalment_number = serializers.IntegerField(allow_null=True)


class DepositBookingSerializer(serializers.Serializer):
    id = serializers.CharField()
    kind = serializers.CharField()
    amount = serializers.DecimalField(max_digits=8, decimal_places=2)
    date = serializers.DateField()
    note = serializers.CharField()


class DepositDetailsSerializer(serializers.Serializer):
    configuration = DepositConfigurationSerializer()
    exists = serializers.BooleanField()
    can_manage = serializers.BooleanField()
    can_increase = serializers.BooleanField()
    revision = serializers.IntegerField()
    agreed_amount = serializers.DecimalField(
        max_digits=8, decimal_places=2, allow_null=True
    )
    hardship_pending = serializers.BooleanField()
    exception_authorized = serializers.BooleanField()
    cancellation_date = serializers.DateField(allow_null=True)
    received = serializers.DecimalField(max_digits=12, decimal_places=2)
    refunded = serializers.DecimalField(max_digits=12, decimal_places=2)
    balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    pending = serializers.DecimalField(max_digits=12, decimal_places=2)
    committed = serializers.DecimalField(max_digits=12, decimal_places=2)
    refundable = serializers.DecimalField(max_digits=12, decimal_places=2)
    payments = DepositPaymentSerializer(many=True)
    bookings = DepositBookingSerializer(many=True)


class DepositChangeSerializer(serializers.Serializer):
    request_id = serializers.UUIDField()
    expected_revision = serializers.IntegerField(min_value=0)
    action = serializers.ChoiceField(
        choices=["increase", "agreement", "receipt", "refund", "reversal"]
    )
    amount = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=0)
    instalments = serializers.IntegerField(min_value=1, max_value=120, default=1)
    start_date = serializers.DateField(required=False)
    date = serializers.DateField(required=False)
    note = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=2000
    )

    def validate(self, attrs):
        if attrs["action"] == "increase" and ("start_date" in attrs or "date" in attrs):
            raise serializers.ValidationError(
                "Für Erhöhungen gelten die bestehenden Einzugstermine."
            )
        if attrs["action"] == "agreement" and "start_date" not in attrs:
            raise serializers.ValidationError(
                "Bitte den Beginn des vereinbarten Einzugs angeben."
            )
        if attrs["action"] in {"receipt", "refund", "reversal"} and "date" not in attrs:
            raise serializers.ValidationError("Bitte das Buchungsdatum angeben.")
        return attrs
