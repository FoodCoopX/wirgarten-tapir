import factory.random
from django.conf import settings
from mailmanclient import MailingList

from tapir.core.services.mailman.mailing_list_settings_updater import (
    MailingListSettingsUpdater,
)
from tapir.core.services.mailman.tapir_mailman_client import TapirMailmanClient
from tapir.wirgarten.models import Member


class MailingListGenerator:
    NB_CONFIRMED_MEMBERS_PER_LIST = 3
    NB_INVITED_MEMBERS_PER_LIST = 1
    NB_CONFIRMED_EXTERNALS_PER_LIST = 2
    NB_INVITED_EXTERNALS_PER_LIST = 1

    @classmethod
    def generate_mailing_lists(cls):
        if not settings.MAILING_LISTS_ENABLED:
            return

        cache = {}
        TapirMailmanClient.ensure_instance_domain_exists(cache=cache)
        domain = TapirMailmanClient.get_domain(cache=cache)
        member_emails = list(
            Member.objects.order_by("email").values_list("email", flat=True)
        )

        for moderated in [False, True]:
            for advertised in [False, True]:
                list_name = "-".join(
                    [
                        "moderiert" if moderated else "unmoderiert",
                        "offen" if advertised else "geschlossen",
                    ]
                )
                mailing_list = domain.create_list(list_name=list_name)
                MailingListSettingsUpdater.update_settings(
                    mailing_list=mailing_list,
                    advertised=advertised,
                    description=f"Testliste: {'moderiert' if moderated else 'nicht moderiert'}, "
                    f"{'Selbstanmeldung möglich' if advertised else 'keine Selbstanmeldung'}",
                    moderated=moderated,
                )
                cls._subscribe_recipients(
                    mailing_list=mailing_list,
                    list_name=list_name,
                    member_emails=member_emails,
                )

    @classmethod
    def _subscribe_recipients(
        cls, mailing_list: MailingList, list_name: str, member_emails: list[str]
    ):
        chosen_member_emails = factory.random.randgen.sample(
            member_emails,
            cls.NB_CONFIRMED_MEMBERS_PER_LIST + cls.NB_INVITED_MEMBERS_PER_LIST,
        )
        confirmed_emails = chosen_member_emails[: cls.NB_CONFIRMED_MEMBERS_PER_LIST]
        invited_emails = chosen_member_emails[cls.NB_CONFIRMED_MEMBERS_PER_LIST :]

        confirmed_emails += [
            f"extern-{list_name}-{index}@example.com"
            for index in range(cls.NB_CONFIRMED_EXTERNALS_PER_LIST)
        ]
        invited_emails += [
            f"extern-eingeladen-{list_name}-{index}@example.com"
            for index in range(cls.NB_INVITED_EXTERNALS_PER_LIST)
        ]

        for email in confirmed_emails:
            mailing_list.subscribe(
                address=email,
                pre_verified=True,
                pre_confirmed=True,
                pre_approved=True,
                send_welcome_message=False,
            )
        for email in invited_emails:
            mailing_list.subscribe(address=email, invitation=True)

    @staticmethod
    def delete_all_mailing_lists():
        if not settings.MAILING_LISTS_ENABLED:
            return

        cache = {}
        TapirMailmanClient.ensure_instance_domain_exists(cache=cache)
        for mailing_list in TapirMailmanClient.get_domain(cache=cache).lists:
            mailing_list.delete()
