import base64
import json

from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils import timezone

from tapir.accounts.config import EMAIL_CHANGE_LINK_VALIDITY_MINUTES
from tapir.accounts.models import EmailChangeRequest, TapirUser
from tapir.accounts.services.mail_change_service import MailChangeService


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

    return HttpResponseRedirect(reverse_lazy("link_expired"))
