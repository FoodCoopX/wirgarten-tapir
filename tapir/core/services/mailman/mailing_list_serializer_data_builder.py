from mailmanclient import MailingList

from tapir.core.services.mailman.mailing_list_settings_updater import (
    MailingListSettingsUpdater,
)


class MailingListSerializerDataBuilder:
    @classmethod
    def build_serializer_data(cls, mailing_list: MailingList):
        return {
            "name": mailing_list.fqdn_listname,
            "nb_recipients": len(mailing_list.members) + len(mailing_list.requests),
            "advertised": mailing_list.settings["advertised"],
            "moderated": MailingListSettingsUpdater.is_moderated(mailing_list),
            "description": mailing_list.settings["description"],
        }

    @classmethod
    def build_admin_serializer_data(cls, mailing_list: MailingList):
        return {
            **cls.build_serializer_data(mailing_list),
            "nb_held_messages": mailing_list.get_held_count(),
        }
