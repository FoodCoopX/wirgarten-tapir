from drf_spectacular.utils import extend_schema_field
from icecream import ic
from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer

from tapir.associations.models import (
    AssociationMembershipType,
    AssociationMembershipTypePrice,
)
from tapir.utils.services.tapir_cache import TapirCache


class AssociationMembershipTypePriceSerializer(ModelSerializer):
    class Meta:
        model = AssociationMembershipTypePrice
        fields = "__all__"


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
        ic(cache)
        return AssociationMembershipTypePriceSerializer(
            TapirCache.get_association_membership_type_prices(
                type_id=membership_type.id, cache=cache
            ),
            many=True,
        ).data
