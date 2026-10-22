from mailmanclient import MailingList


class MailingListSerializerDataBuilder:
    @classmethod
    def build_serializer_data(cls, mailing_list: MailingList):
        return {
            "name": mailing_list.fqdn_listname,
            "nb_recipients": len(mailing_list.members) + len(mailing_list.requests),
            "advertised": mailing_list.settings["advertised"],
            "moderated": mailing_list.settings["default_member_action"] == "hold",
            "description": mailing_list.settings["description"],
        }
