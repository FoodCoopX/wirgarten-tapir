from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from tapir.jasmin_integration.models import JasminTenant, JasminTenantSettings
from tapir.jasmin_integration.services import get_current_jasmin_tenant_settings


class JasminTenantSettingsSerializer(serializers.ModelSerializer):
    tenant_language = serializers.SerializerMethodField()

    class Meta:
        model = JasminTenantSettings
        fields = "__all__"

        read_only_fields = (
            "id",
            "valid_from",
            "created_at",
            "updated_at",
            "tenant_language",
        )

    @staticmethod
    def get_tenant_language(_) -> str:
        return "de"


class JasminTenantSerializer(serializers.ModelSerializer):
    current_settings = serializers.SerializerMethodField()
    settings = serializers.SerializerMethodField()

    class Meta:
        model = JasminTenant
        fields = "__all__"

        read_only_fields = (
            "id",
            "schema_name",
            "is_active",
            "created_at",
            "updated_at",
            "action_rate_limit_overrides",
        )

    @staticmethod
    @extend_schema_field(JasminTenantSettingsSerializer)
    def get_current_settings(_):
        return JasminTenantSettingsSerializer(get_current_jasmin_tenant_settings()).data

    @classmethod
    @extend_schema_field(JasminTenantSettingsSerializer)
    def get_settings(cls, _):
        return cls.get_current_settings(_)
