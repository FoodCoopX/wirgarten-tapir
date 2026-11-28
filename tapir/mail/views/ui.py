from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import TemplateView
from tapir.mail.config import MAIL_URL_PREFIX
from tapir.wirgarten.constants import Permission


class MailUiView(PermissionRequiredMixin, TemplateView):
    permission_required = Permission.Email.MANAGE
    template_name = "tapir_mail/ui.html"

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["env_vars"] = {
            "REACT_APP_API_ROOT": f"{settings.SITE_URL}/{MAIL_URL_PREFIX}",
            "REACT_APP_BASENAME": f"/{MAIL_URL_PREFIX}",
        }
        return context_data
