from rest_framework import serializers


class MemberImportUploadSerializer(serializers.Serializer):
    file = serializers.FileField()


class MemberImportApplySerializer(serializers.Serializer):
    token = serializers.CharField()


class MemberImportRowSerializer(serializers.Serializer):
    line = serializers.IntegerField()
    status = serializers.CharField()
    error = serializers.CharField(allow_blank=True)


class MemberImportResultSerializer(serializers.Serializer):
    rows = MemberImportRowSerializer(many=True)
    errors = serializers.ListField(child=serializers.CharField())
    applied = serializers.BooleanField()
    can_apply = serializers.BooleanField(read_only=True)


class MemberImportPreviewSerializer(serializers.Serializer):
    token = serializers.CharField(allow_null=True)
    result = MemberImportResultSerializer()
