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
    user_can_update_contribution = serializers.BooleanField()


class UpdateMemberSolidarityContributionRequestSerializer(serializers.Serializer):
    amount = serializers.FloatField()
    member_id = serializers.CharField()
    start_contribution_now = serializers.BooleanField()


class UpdateMemberSolidarityContributionResponseSerializer(serializers.Serializer):
    contributions = SolidarityContributionSerializer(many=True)
    updated = serializers.BooleanField()
    error = serializers.CharField()
