from rest_framework import serializers

from tapir.solidarity_contribution.models import SolidarityContribution


class SolidarityContributionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SolidarityContribution
        fields = "__all__"
