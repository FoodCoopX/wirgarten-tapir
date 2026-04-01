from rest_framework import serializers

from tapir.wirgarten.models import MemberExtraEmail


class MemberExtraEmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = MemberExtraEmail
        exclude = ["created_at", "updated_at"]
