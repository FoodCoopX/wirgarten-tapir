from rest_framework import serializers

from tapir.solidarity_contribution.models import SolidarityContribution


class SolidarityContributionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SolidarityContribution
        fields = "__all__"


class MemberSolidarityContributionsResponseSerializer(serializers.Serializer):
    contributions = SolidarityContributionSerializer(many=True)
    change_valid_from = serializers.DateField()
    user_can_set_lower_value = serializers.BooleanField()
