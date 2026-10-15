from apps.accounts import serializers as jasmin_serializers
from apps.accounts.errors import InvalidCredentials as JasminInvalidCredentials
from apps.accounts.errors import InvalidToken as JasminInvalidToken
from apps.shared import auth_cookies as jasmin_auth_cookies
from core.exception_handler import jasmin_exception_handler
from django.db import transaction
from django.http import HttpRequest
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.core.services.jasmin_synchronisation_service import (
    JasminSynchronisationService,
    JasminSynchronisationException,
)
from tapir.jasmin_integration import jasmin_compat
from tapir.jasmin_integration.authentication import (
    CsrfExemptSessionAuthentication,
)
from tapir.wirgarten.constants import Permission


def can_use_jasmin(user) -> bool:
    return user.is_authenticated and user.has_perm(Permission.Coop.MANAGE)


class JasminTemplateView(TemplateView):
    template_name = "core/jasmin_iframe.html"

    def get(self, request: HttpRequest, *args, **kwargs):
        try:
            with transaction.atomic():
                warnings = JasminSynchronisationService.synchronise_everything(
                    user=request.user
                )
            self.extra_context = {"synchronisation_warnings": warnings}
        except JasminSynchronisationException as error:
            self.extra_context = {"synchronisation_error": error.message}
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Written to Jasmin's localStorage before Jasmin starts in the iframe, so
        # that Jasmin skips its login page. Replaces whatever user is cached there,
        # in case another user logged in to Tapir in the same browser.
        context["jasmin_auth_metadata_local_storage_key"] = (
            jasmin_compat.AUTH_METADATA_LOCAL_STORAGE_KEY
        )
        context["jasmin_auth_metadata"] = (
            jasmin_compat.build_auth_metadata(
                user=self.request.user, tenant=self.request.tenant
            )
            if can_use_jasmin(self.request.user)
            else None
        )
        return context


class JasminAuthApiView(APIView):
    # The Tapir session decides who gets Jasmin tokens. The views check it
    # themselves, so that a refused user gets the 401 Jasmin's frontend expects.
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [AllowAny]

    def get_exception_handler(self):
        # Jasmin's errors carry their HTTP status (401 for an invalid token, which
        # Jasmin's frontend reads as "logged out"), but only Jasmin's exception
        # handler knows them: Tapir's default handler turns them into 500s.
        return jasmin_exception_handler


class JasminLoginView(JasminAuthApiView):
    @extend_schema(
        responses={200: jasmin_serializers.LoginResponseSerializer},
        request=jasmin_serializers.LoginRequestSerializer,
    )
    def post(self, request):
        serializer = jasmin_serializers.LoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not can_use_jasmin(request.user):
            raise JasminInvalidCredentials("USER NOT LOGGED IN")

        payload, refresh_token = jasmin_compat.issue_login_payload(
            user=request.user, tenant=request.tenant
        )
        response = Response(payload)
        jasmin_auth_cookies.set_tenant_refresh_cookie(response, refresh_token)
        return response


class JasminRefreshVew(JasminAuthApiView):
    @extend_schema(
        responses={200: jasmin_serializers.LoginResponseSerializer},
        request=None,
    )
    def post(self, request):
        # Jasmin's login system isn't used, the Tapir session decides: instead of
        # validating Jasmin's refresh cookie, every refresh issues new tokens for the
        # current Tapir user. Jasmin's frontend already knows the user from
        # localStorage, see JasminTemplateView.
        if not can_use_jasmin(request.user):
            raise JasminInvalidToken("USER NOT LOGGED IN")

        payload, _ = jasmin_compat.issue_login_payload(
            user=request.user, tenant=request.tenant
        )
        return Response(payload)
