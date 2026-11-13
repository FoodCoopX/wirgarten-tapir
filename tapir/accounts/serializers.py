from django.urls import reverse
from rest_framework import serializers

from tapir.wirgarten.models import Member


class UnverifiedMemberSerializer(serializers.ModelSerializer):
    has_keycloak_account = serializers.SerializerMethodField()
    profile_url = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = [
            "id",
            "member_no",
            "first_name",
            "last_name",
            "email",
            "has_keycloak_account",
            "profile_url",
        ]

    @staticmethod
    def get_has_keycloak_account(member: Member) -> bool:
        return member.keycloak_id is not None

    @staticmethod
    def get_profile_url(member: Member) -> str:
        return reverse("wirgarten:member_detail", kwargs={"pk": member.id})


class SendVerificationEmailsResponseSerializer(serializers.Serializer):
    member_count = serializers.IntegerField()
    estimated_duration_seconds = serializers.IntegerField()


class UnverifiedMembersResponseSerializer(serializers.Serializer):
    members = UnverifiedMemberSerializer(many=True)
    estimated_duration_seconds = serializers.IntegerField()
    sending_in_progress = serializers.BooleanField()
