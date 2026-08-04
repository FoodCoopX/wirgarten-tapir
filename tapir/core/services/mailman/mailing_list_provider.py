from django.http import Http404

from tapir.core.services.mailman.mailman_request_sender import MailmanRequestSender


class MailingListProvider:
    @staticmethod
    def get_list_by_name_or_404(list_name: str, cache: dict):
        domain = MailmanRequestSender.get_domain(cache)
        for mailing_list in domain.lists:
            if mailing_list.fqdn_listname == list_name:
                return mailing_list

        raise Http404(f"Keine Liste mit Name {list_name} gefunden")
