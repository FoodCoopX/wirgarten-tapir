from dataclasses import dataclass

from django.http import HttpRequest
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.core.services.jasmin_synchronisation_service import (
    JasminSynchronisationService,
    JasminSynchronisationException,
)
from tapir.jasmin_integration.serializers import JasminPlaceholderTenantSerializer


class JasminTemplateView(TemplateView):
    template_name = "core/jasmin_iframe.html"

    def get(self, request: HttpRequest, *args, **kwargs):
        try:
            JasminSynchronisationService.synchronise_everything()
        except JasminSynchronisationException as error:
            self.extra_context = {"synchronisation_error": error.message}
        return super().get(request, *args, **kwargs)


@dataclass
class PlaceholderTenant:
    name: str
    schema_name: str
    id: str


tenant = PlaceholderTenant(
    name="placeholder", schema_name="public", id="placeholder_id"
)


class JasminCurrentTenantView(APIView):
    @extend_schema(
        responses={200: JasminPlaceholderTenantSerializer},
        parameters=[],
    )
    def get(self, request, *args, **kwargs):
        settings = {"uploads_weekly_share_amount": True, "tenant_language": "de"}
        return Response(
            JasminPlaceholderTenantSerializer(
                {
                    "id": tenant.id,
                    "name": tenant.name,
                    "tenant_language": "de",
                    "number_locale": "de-DE",
                    "settings": settings,
                    "current_settings": settings,
                }
            ).data
        )
