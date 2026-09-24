from mailmanclient import MailingList


class MailingListSerializerDataBuilder:
    @classmethod
    def build_serializer_data(cls, mailing_list: MailingList):
        return {
            "name": mailing_list.fqdn_listname,
            "nb_recipients": len(mailing_list.members) + len(mailing_list.requests),
            "advertised": mailing_list.settings["advertised"],
            "description": mailing_list.settings["description"],
        }
