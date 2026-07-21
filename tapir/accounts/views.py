import base64
import json
from dataclasses import dataclass

from apps.accounts import errors as picking_errors
from apps.accounts import serializers as picking_serializers
from apps.accounts.errors import InvalidCredentials
from apps.accounts.services import auth_service as picking_auth_service
from apps.accounts.views import auth_views as picking_auth_views
from apps.shared import auth_cookies as picking_auth_cookies
from dateutil.relativedelta import relativedelta
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import FormView
from drf_spectacular.utils import extend_schema
from icecream import ic
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.accounts.config import EMAIL_CHANGE_LINK_VALIDITY_MINUTES
from tapir.accounts.forms import AdminMailChangeForm
from tapir.accounts.models import EmailChangeRequest, TapirUser
from tapir.accounts.services.mail_change_service import MailChangeService
from tapir.wirgarten.constants import Permission

# FIXME: this file has a dependency on tapir/wirgarten! Replace the send_email call as soon as the mail module is ready


@transaction.atomic
def change_email(request, **kwargs):
    data = json.loads(base64.b64decode(kwargs["token"]))
    user_id = data["user"]
    new_email = data["new_email"]
    matching_change_request = EmailChangeRequest.objects.filter(
        new_email=new_email, secret=data["secret"], user_id=user_id
    ).order_by("-created_at")
    cache = {}

    link_validity = relativedelta(minutes=EMAIL_CHANGE_LINK_VALIDITY_MINUTES)
    now = timezone.now()
    if matching_change_request.exists() and now < (
        matching_change_request[0].created_at + link_validity
    ):
        user = TapirUser.objects.get(id=user_id)
        MailChangeService.apply_mail_change(user=user, new_email=new_email, cache=cache)
        return HttpResponseRedirect(
            reverse_lazy("wirgarten:member_detail", kwargs={"pk": user.id})
            + "?email_changed=true"
        )

    return HttpResponseRedirect(reverse_lazy("accounts:link_expired"))


class AdminApplyMailChangeView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    permission_required = Permission.Accounts.MANAGE
    form_class = AdminMailChangeForm

    def __init__(self):
        super().__init__()
        self.cache = {}

    def form_valid(self, form):
        self.user = get_object_or_404(TapirUser, id=form.cleaned_data["user_id"])
        new_email = form.cleaned_data["new_email"]
        MailChangeService.apply_mail_change(
            user=self.user, new_email=new_email, cache=self.cache
        )

        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("wirgarten:member_detail", kwargs={"pk": self.user.id})


class CsrfExemptSessionAuthentication(SessionAuthentication):

    def enforce_csrf(self, request):
        return


@dataclass
class Tenant:
    id: str
    name: str
    schema_name: str


class PickingLogin(APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]

    @extend_schema(
        responses={200: picking_serializers.LoginResponseSerializer},
        request=picking_serializers.LoginRequestSerializer,
    )
    def post(self, request):
        serializer = picking_serializers.LoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not request.user.is_authenticated or not request.user.has_perm(
            Permission.Coop.MANAGE
        ):
            ic(
                "USER NOT LOGGED IN",
                request,
                request.user,
                request.user.is_authenticated,
                request.user.has_perm(Permission.Coop.MANAGE),
            )
            raise InvalidCredentials("USER NOT LOGGED IN")

        tenant = Tenant(
            id="TAPIR_DEFAULT_TENANT_ID",
            name="TAPIR_DEFAULT_TENANT_NAME",
            schema_name="TAPIR_DEFAULT_SCHEMA_NAME",
        )
        login_result = picking_auth_service._issue_login_tokens(
            user=request.user, tenant=tenant
        )
        response = Response(
            picking_auth_views._login_payload(result=login_result, tenant=tenant)
        )
        picking_auth_cookies.set_tenant_refresh_cookie(response, login_result.refresh)
        return response


class PickingRefresh(APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]

    @extend_schema(
        responses={200: picking_serializers.RefreshResponseSerializer},
        request=None,
    )
    def post(self, request):
        refresh_token = picking_auth_cookies.get_tenant_refresh_token(request)
        if not refresh_token:
            ic(request, request.COOKIES)
            raise picking_errors.RefreshTokenMissing("Refresh token is required")

        result = picking_auth_service.refresh_access_token(
            refresh_token=refresh_token, tenant_schema=None
        )
        response_data = {"access": result["access"]}
        response = Response(response_data)
        if result["refresh"]:
            picking_auth_cookies.set_tenant_refresh_cookie(response, result["refresh"])
        return response
