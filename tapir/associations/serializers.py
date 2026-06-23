from rest_framework.serializers import ModelSerializer

from tapir.associations.models import AssociationMembershipType


class AssociationMembershipTypeSerializer(ModelSerializer):
    class Meta:
        model = AssociationMembershipType
        fields = "__all__"
