from mailmanclient import MailingList


class MailingListSubscriptionChecker:
    @classmethod
    def is_member_subscribed_to_list(cls, email: str, mailing_list: MailingList):
        return any(str(member.address) == email for member in mailing_list.members)

    @classmethod
    def is_member_waiting_for_confirmation(cls, email: str, mailing_list: MailingList):
        return any(request["email"] == email for request in mailing_list.requests)
