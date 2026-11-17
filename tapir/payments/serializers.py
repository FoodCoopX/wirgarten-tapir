from django.db.models import Sum, F
from django.urls import reverse
from rest_framework import serializers

from tapir.associations.serializers import AssociationMembershipSerializer
from tapir.deliveries.serializers import SubscriptionSerializer
from tapir.payments.models import (
    MemberPaymentRhythm,
    MemberCredit,
    PaymentExportExclusionPeriod,
)
from tapir.payments.services.payment_export_exclusion_period_service import (
    PaymentExportExclusionPeriodService,
)
from tapir.pickup_locations.serializers import PublicPickupLocationSerializer
from tapir.solidarity_contribution.serializers import SolidarityContributionSerializer
from tapir.subscriptions.serializers import (
    CoopShareTransactionSerializer,
    MemberSerializer,
)
from tapir.wirgarten.models import Member, Payment, PaymentTransaction


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"

    amount = serializers.FloatField()


class ExtendedPaymentSerializer(serializers.Serializer):
    payment = PaymentSerializer()
    subscriptions = SubscriptionSerializer(many=True)
    coop_share_transactions = CoopShareTransactionSerializer(many=True)
    solidarity_contributions = SolidarityContributionSerializer(many=True)
    delivery_charge_pickup_location = PublicPickupLocationSerializer(allow_null=True)
    delivery_dates = serializers.ListField(child=serializers.DateField())
    association_memberships = AssociationMembershipSerializer(many=True)
    number_of_instalments = serializers.IntegerField(allow_null=True)
    excluded_from_export = serializers.BooleanField()


class MemberCreditSerializer(serializers.ModelSerializer):
    class Meta:
        model = MemberCredit
        fields = [
            "id",
            "member",
            "amount",
            "purpose",
            "comment",
            "due_date",
            "settled_on",
        ]

    amount = serializers.FloatField()


class ExtendedMemberCreditSerializer(serializers.Serializer):
    credit = MemberCreditSerializer()
    member = MemberSerializer()
    member_url = serializers.URLField()
    mandate_ref = serializers.CharField()


class FuturePaymentsResponseSerializer(serializers.Serializer):
    payments = ExtendedPaymentSerializer(many=True)
    credits = MemberCreditSerializer(many=True)
    trial_period_enabled = serializers.BooleanField()


class MemberPaymentRhythmSerializer(serializers.ModelSerializer):
    class Meta:
        model = MemberPaymentRhythm
        exclude = ["updated_at", "created_at"]


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


class CabLoggedInUserChangeTargetsPaymentRhythmResponseSerializer(
    serializers.Serializer
):
    can_change = serializers.BooleanField()
    current_rhythm = serializers.CharField()


class MandateReferencePreviewResponseSerializer(serializers.Serializer):
    previews = serializers.DictField(child=serializers.CharField())
    error = serializers.CharField()


class PaymentIntendedUsePreviewResponseSerializer(serializers.Serializer):
    previews_new = serializers.ListField(child=serializers.CharField())
    previews_old = serializers.ListField(child=serializers.CharField())
    error = serializers.CharField()
    tokens = serializers.ListField(child=serializers.CharField())
    payments = PaymentSerializer(many=True)
    members = MemberSerializer(many=True)


class JokerCreditIntendedUsePreviewResponseSerializer(serializers.Serializer):
    previews_new = serializers.ListField(child=serializers.CharField())
    previews_old = serializers.ListField(child=serializers.CharField())
    error = serializers.CharField()
    tokens = serializers.ListField(child=serializers.CharField())
    credits = serializers.ListSerializer(child=serializers.FloatField())
    members = MemberSerializer(many=True)


class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = "__all__"

    payments_count = serializers.SerializerMethodField()
    payments_sum = serializers.SerializerMethodField()
    excluded_payments_count = serializers.SerializerMethodField()
    excluded_payments_sum = serializers.SerializerMethodField()
    csv_download_url = serializers.SerializerMethodField()
    xml_download_url = serializers.SerializerMethodField()

    @staticmethod
    def get_payments_count(transaction: PaymentTransaction) -> int:
        return transaction.payment_set.filter(excluded_from_export=False).count()

    @staticmethod
    def get_payments_sum(transaction: PaymentTransaction) -> float:
        return (
            transaction.payment_set.filter(excluded_from_export=False).aggregate(
                amount_sum=Sum(F("amount"))
            )["amount_sum"]
            or 0
        )

    @staticmethod
    def get_excluded_payments_count(transaction: PaymentTransaction) -> int:
        return transaction.payment_set.filter(excluded_from_export=True).count()

    @staticmethod
    def get_excluded_payments_sum(transaction: PaymentTransaction) -> float:
        return (
            transaction.payment_set.filter(excluded_from_export=True).aggregate(
                amount_sum=Sum(F("amount"))
            )["amount_sum"]
            or 0
        )

    @staticmethod
    def get_csv_download_url(transaction: PaymentTransaction) -> str:
        return reverse(
            "wirgarten:exported_files_download", args=[transaction.csv_file_id]
        )

    @staticmethod
    def get_xml_download_url(transaction: PaymentTransaction) -> str:
        if transaction.xml_file_id is None:
            return ""
        return reverse(
            "wirgarten:exported_files_download", args=[transaction.xml_file_id]
        )


class PaymentListSerializer(serializers.Serializer):
    # In PaymentTransactionDetailsSerializer, if we set directly
    # payments_by_mandate_ref = serializers.DictField(child=PaymentSerializer(many=True))
    # then the deserialization on the frontend size doesn't work
    payments = PaymentSerializer(many=True)


class PaymentTransactionDetailsSerializer(serializers.Serializer):
    payments_by_mandate_ref = serializers.DictField(child=PaymentListSerializer())
    members_by_mandate_ref = serializers.DictField(child=MemberSerializer())
    intended_use_by_mandate_ref = serializers.DictField(child=serializers.CharField())


class MemberNeedingBankingDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = [
            "member_no",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "member_url",
        ]

    member_url = serializers.SerializerMethodField()

    @staticmethod
    def get_member_url(member: Member) -> str:
        return member.get_absolute_url()


class PaymentExportExclusionPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentExportExclusionPeriod
        fields = ["id", "start_date", "end_date", "comment"]


class PaymentExportExclusionPeriodCreateRequestSerializer(serializers.Serializer):
    member_id = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField(allow_null=True)
    comment = serializers.CharField(allow_blank=True)


class PaymentExportExclusionPeriodUpdateRequestSerializer(serializers.Serializer):
    period_id = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField(allow_null=True)
    comment = serializers.CharField(allow_blank=True)


class PaymentExportExclusionPeriodOverviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentExportExclusionPeriod
        fields = [
            "id",
            "start_date",
            "end_date",
            "comment",
            "member_no",
            "first_name",
            "last_name",
            "member_url",
            "is_active",
        ]

    member_no = serializers.IntegerField(source="member.member_no", allow_null=True)
    first_name = serializers.CharField(source="member.first_name")
    last_name = serializers.CharField(source="member.last_name")
    member_url = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()

    @staticmethod
    def get_member_url(period: PaymentExportExclusionPeriod) -> str:
        return period.member.get_absolute_url()

    def get_is_active(self, period: PaymentExportExclusionPeriod) -> bool:
        return PaymentExportExclusionPeriodService.is_date_within_period(
            period=period, reference_date=self.context["today"]
        )
