from apps.accounts import serializers as jasmin_serializers
from apps.accounts.errors import InvalidCredentials as JasminInvalidCredentials
from apps.accounts.errors import InvalidToken as JasminInvalidToken
from apps.accounts.services import auth_service as jasmin_auth_service
from apps.accounts.views import auth_views as jasmin_auth_views
from apps.shared import auth_cookies as jasmin_auth_cookies
from django.db import transaction
from django.http import HttpRequest
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from tapir.core.services.jasmin_synchronisation_service import (
    JasminSynchronisationService,
    JasminSynchronisationException,
)
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.jasmin_integration.models import JasminTenant, JasminTenantSettings
from tapir.jasmin_integration.serializers import (
    JasminTenantSerializer,
    JasminTenantSettingsSerializer,
)
from tapir.wirgarten.constants import Permission


def get_tenant():
    tenant, _ = JasminTenant.objects.get_or_create(defaults={"schema_name": "public"})
    return tenant


class JasminTemplateView(TemplateView):
    template_name = "core/jasmin_iframe.html"

    @transaction.atomic
    def get(self, request: HttpRequest, *args, **kwargs):
        try:
            JasminSynchronisationService.synchronise_everything()
        except JasminSynchronisationException as error:
            self.extra_context = {"synchronisation_error": error.message}
        return super().get(request, *args, **kwargs)


class JasminCurrentTenantView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        responses={200: JasminTenantSerializer},
        parameters=[],
    )
    def get(self, request, *args, **kwargs):
        tenant = get_tenant()
        return Response(JasminTenantSerializer(tenant).data)


class JasminTenantViewSet(ModelViewSet):
    queryset = JasminTenant.objects.all()
    serializer_class = JasminTenantSerializer
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]


class JasminUpdateCurrentSettingsView(APIView):
    def put(self, request, *args, **kwargs):
        serializer = JasminTenantSettingsSerializer(
            instance=JasminTenantSettings.objects.get(),
            data=request.data["settings"],
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response("OK")


class JasminLoginView(APIView):
    @extend_schema(
        responses={200: jasmin_serializers.LoginResponseSerializer},
        request=jasmin_serializers.LoginRequestSerializer,
    )
    def post(self, request):
        serializer = jasmin_serializers.LoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not request.user.is_authenticated or not request.user.has_perm(
            Permission.Coop.MANAGE
        ):
            raise JasminInvalidCredentials("USER NOT LOGGED IN")

        tenant = get_tenant()

        login_result = jasmin_auth_service._issue_login_tokens(
            user=request.user, tenant=tenant
        )
        response = Response(
            jasmin_auth_views._login_payload(result=login_result, tenant=tenant)
        )
        jasmin_auth_cookies.set_tenant_refresh_cookie(response, login_result.refresh)
        return response


class JasminRefreshVew(APIView):
    @extend_schema(
        responses={200: jasmin_serializers.LoginResponseSerializer},
        request=None,
    )
    def post(self, request):
        # Jasmin's login system isn't used, the Tapir session decides: instead of
        # validating Jasmin's refresh cookie, every refresh issues new tokens for the
        # current Tapir user. The response also carries the user like the login
        # response does, so that Jasmin's frontend knows the user's roles without
        # going through its login page.
        if not request.user.is_authenticated or not request.user.has_perm(
            Permission.Coop.MANAGE
        ):
            raise JasminInvalidToken("USER NOT LOGGED IN")

        tenant = get_tenant()

        login_result = jasmin_auth_service._issue_login_tokens(
            user=request.user, tenant=tenant
        )
        return Response(
            jasmin_auth_views._login_payload(result=login_result, tenant=tenant)
        )
