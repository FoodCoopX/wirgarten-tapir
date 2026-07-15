from rest_framework import serializers

from tapir.wirgarten.serializers import MemberExtraEmailSerializer


class MemberMailCategoryRequestSerializer(serializers.Serializer):
    categories_registered_to = serializers.DictField(child=serializers.BooleanField())
    member_id = serializers.CharField()


class MemberExtraMailDataSerializer(serializers.Serializer):
    extra_mails = MemberExtraEmailSerializer(many=True)
    explanation_text = serializers.CharField()


class MemberExtraEmailCreateRequest(serializers.Serializer):
    member_id = serializers.CharField()
    extra_email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()


class MemberExtraEmailUpdateRequest(serializers.Serializer):
    extra_email_id = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
