import base64
import json
import secrets
from urllib.parse import urlencode

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views import View
from django.views.generic import FormView

from tapir.accounts.config import EMAIL_CHANGE_LINK_VALIDITY_MINUTES
from tapir.accounts.forms import AdminMailChangeForm
from tapir.accounts.models import EmailChangeRequest, TapirUser
from tapir.accounts.services.mail_change_service import MailChangeService
from tapir.wirgarten.constants import Permission


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


class PasswordChangeRedirectView(View):
    """
    Sends the user to Keycloak's "update password" page.

    This used to be done in the browser with keycloak.js, which Keycloak no longer
    serves from version 26 on. A plain redirect to the authorization endpoint with
    kc_action=UPDATE_PASSWORD does the same and works with Keycloak 23 and 26.
    """

    def get(self, request, *args, **kwargs):
        config = settings.KEYCLOAK_ADMIN_CONFIG
        redirect_uri = (
            request.build_absolute_uri(reverse("index")) + "?passwordchanged=true"
        )
        params = {
            "client_id": config["FRONTEND_CLIENT_ID"],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "response_mode": "fragment",
            "scope": "openid",
            "kc_action": "UPDATE_PASSWORD",
            "state": secrets.token_urlsafe(16),
        }
        public_url = config["PUBLIC_URL"].rstrip("/")
        realm = config["REALM_NAME"]
        return HttpResponseRedirect(
            f"{public_url}/realms/{realm}/protocol/openid-connect/auth?{urlencode(params)}"
        )
