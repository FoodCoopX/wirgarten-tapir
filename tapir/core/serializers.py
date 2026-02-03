from rest_framework import serializers

from tapir.wirgarten.serializers import MemberExtraEmailSerializer


class MemberMailCategoryRequestSerializer(serializers.Serializer):
    categories_registered_to = serializers.DictField(child=serializers.BooleanField())
    member_id = serializers.CharField()


class MemberExtraMailDataSerializer(serializers.Serializer):
    extra_mails = MemberExtraEmailSerializer(many=True)
    explanation_text = serializers.CharField()
