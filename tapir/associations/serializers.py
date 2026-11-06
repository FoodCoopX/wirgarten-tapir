from decimal import Decimal

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.fields import (
    SerializerMethodField,
    CharField,
    DateField,
    ListField,
    IntegerField,
)
from rest_framework.serializers import ModelSerializer, Serializer

from tapir.associations.models import (
    AssociationMembershipType,
    AssociationMembershipTypePrice,
    AssociationMembership,
)
from tapir.utils.services.tapir_cache import TapirCache


class AssociationMembershipTypePriceSerializer(ModelSerializer):
    class Meta:
        model = AssociationMembershipTypePrice
        fields = "__all__"

    price_as_float = serializers.SerializerMethodField()

    @staticmethod
    def get_price_as_float(price: AssociationMembershipTypePrice) -> float:
        return float(price.price.quantize(Decimal("0.01")))


class AssociationMembershipTypeSerializer(ModelSerializer):
    class Meta:
        model = AssociationMembershipType
        fields = "__all__"

    prices = SerializerMethodField()
    can_be_hard_deleted = SerializerMethodField()

    @extend_schema_field(AssociationMembershipTypePriceSerializer(many=True))
    def get_prices(
        self, membership_type: AssociationMembershipType
    ) -> list[AssociationMembershipTypePrice]:
        cache = self.context["cache"]
        return AssociationMembershipTypePriceSerializer(
            TapirCache.get_association_membership_type_prices(
                type_id=membership_type.id, cache=cache
            ),
            many=True,
        ).data

    def get_can_be_hard_deleted(
        self, membership_type: AssociationMembershipType
    ) -> bool:
        cache = self.context["cache"]
        at_least_one_membership_exists = any(
            membership.type_id == membership_type.id
            for membership in TapirCache.get_all_association_memberships(cache=cache)
        )
        return not at_least_one_membership_exists


class AssociationMembershipSerializer(ModelSerializer):
    class Meta:
        model = AssociationMembership
        fields = "__all__"

    type = AssociationMembershipTypeSerializer()


class AdminSetAssociationMembershipRequestSerializer(Serializer):
    member_id = CharField()
    membership_type_id = CharField()
    start_date = DateField()


class MemberAssociationMembershipDetailsSerializer(Serializer):
    memberships = AssociationMembershipSerializer(many=True)
    order_wizard_url = CharField(allow_null=True)
    contact_email = serializers.EmailField()


class ExistingMemberUpdatesAssociationMembershipRequest(Serializer):
    member_id = CharField()
    association_membership_type_id = CharField()
    iban = serializers.CharField(required=False, allow_blank=True)
    account_owner = serializers.CharField(required=False, allow_blank=True)


class SetAssociationMembershipEndDateRequestSerializer(Serializer):
    membership_id = CharField()
    end_date = DateField()


class GraphDatasetSerializer(Serializer):
    name = CharField()
    color = CharField()
    values = ListField(child=IntegerField())


class NumberOfAssociationMembersPerMonthResponseSerializer(Serializer):
    labels = ListField(child=CharField())
    datasets = GraphDatasetSerializer(many=True)


class AssociationDepositSettingsSerializer(Serializer):
    enabled = serializers.BooleanField()
    name = CharField()
    minimum = serializers.DecimalField(
        max_digits=8, decimal_places=2, coerce_to_string=False
    )
    increment = serializers.DecimalField(
        max_digits=8, decimal_places=2, coerce_to_string=False
    )
    supporting_members_required = serializers.BooleanField()
    allow_larger_signup = serializers.BooleanField()
    allow_member_increase = serializers.BooleanField()
    instalments_enabled = serializers.BooleanField()
    instalment_count = serializers.IntegerField()
    hardship_enabled = serializers.BooleanField()
    hardship_label = CharField()


class AssociationDepositScheduledPaymentSerializer(Serializer):
    amount = serializers.DecimalField(
        max_digits=8, decimal_places=2, coerce_to_string=False
    )
    due_date = DateField()
    instalment_number = IntegerField(allow_null=True)


class AssociationDepositPaymentDetailsSerializer(
    AssociationDepositScheduledPaymentSerializer
):
    id = CharField()
    status = CharField()


class AssociationDepositDetailsSerializer(Serializer):
    settings = AssociationDepositSettingsSerializer()
    visible = serializers.BooleanField()
    agreed_amount = serializers.DecimalField(
        max_digits=8, decimal_places=2, coerce_to_string=False, allow_null=True
    )
    received_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, coerce_to_string=False
    )
    committed_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, coerce_to_string=False
    )
    pending_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, coerce_to_string=False
    )
    refunded_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, coerce_to_string=False
    )
    retained_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, coerce_to_string=False
    )
    refund_requires_agreement = serializers.BooleanField()
    stopped_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, coerce_to_string=False
    )
    can_increase = serializers.BooleanField()
    state = CharField()
    overpayment_credit = serializers.DecimalField(
        max_digits=12, decimal_places=2, coerce_to_string=False, allow_null=True
    )
    payments = AssociationDepositPaymentDetailsSerializer(many=True)


class PreviewAssociationDepositIncreaseRequestSerializer(Serializer):
    member_id = CharField()
    total_amount = serializers.DecimalField(
        max_digits=8, decimal_places=2, coerce_to_string=False
    )


class IncreaseAssociationDepositRequestSerializer(
    PreviewAssociationDepositIncreaseRequestSerializer
):
    confirmation = CharField()


class AssociationDepositIncreasePreviewSerializer(Serializer):
    total_amount = serializers.DecimalField(
        max_digits=8, decimal_places=2, coerce_to_string=False
    )
    received_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, coerce_to_string=False
    )
    committed_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, coerce_to_string=False
    )
    pending_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, coerce_to_string=False
    )
    payments = AssociationDepositScheduledPaymentSerializer(many=True)
    confirmation = CharField()
