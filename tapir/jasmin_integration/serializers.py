from rest_framework import serializers


class TenantSettingsSerializer(serializers.Serializer):
    tenant_language = serializers.CharField()
    uploads_weekly_share_amount = serializers.BooleanField()


class JasminPlaceholderTenantSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    tenant_language = serializers.CharField()
    number_locale = serializers.CharField()
    settings = TenantSettingsSerializer()
    current_settings = TenantSettingsSerializer()
