from tapir.wirgarten.models import Member


class MemberNeedsBankingDataChecker:
    @classmethod
    def does_member_need_banking_data(cls, member: Member):
        return not member.iban or not member.account_owner or not member.sepa_consent
