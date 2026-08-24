from django.conf import settings
from django.core.exceptions import PermissionDenied


class MailingListsEnabledChecker:
    @staticmethod
    def check_mailing_lists_enabled():
        if not settings.MAILING_LISTS_ENABLED:
            raise PermissionDenied("Mailing lists are disabled on this server")
