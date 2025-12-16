from tapir.wirgarten.models import Member


class MemberNeedsBankingDataChecker:
    @classmethod
    def does_member_need_banking_data(cls, member: Member):
        return (
            member.iban is None
            or member.account_owner is None
            or member.sepa_consent is None
        )
