from decimal import Decimal

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer

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


class AssociationMembershipSerializer(ModelSerializer):
    class Meta:
        model = AssociationMembership
        fields = "__all__"

    type = AssociationMembershipTypeSerializer()
