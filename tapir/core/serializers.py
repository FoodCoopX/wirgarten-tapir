from rest_framework import serializers


class MemberMailCategoryRequestSerializer(serializers.Serializer):
    categories_registered_to = serializers.DictField(child=serializers.BooleanField())
    member_id = serializers.CharField()
