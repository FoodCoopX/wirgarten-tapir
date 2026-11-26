from django.contrib.auth.decorators import permission_required
from django.utils.decorators import method_decorator
from django.views import generic

from tapir.mail.config import MAIL_URL_PREFIX
from tapir.wirgarten.constants import Permission


@method_decorator(permission_required(Permission.Email.MANAGE), name="dispatch")
class TapirMailView(generic.TemplateView):
    template_name = "wirgarten/email/tapir_mail_iframe.html"
    extra_context = {"mail_url_prefix": MAIL_URL_PREFIX}
