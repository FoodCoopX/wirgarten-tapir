from tapir.accounts.models import TapirUser
from tapir.wirgarten.models import MemberExtraEmail, MemberExtraEmailDeletedLogEntry


class MemberExtraEmailAddressReleaser:
    @staticmethod
    def release_address(address: str, actor: TapirUser | None):
        for extra_email in MemberExtraEmail.objects.filter(
            email=address
        ).select_related("member"):
            MemberExtraEmailDeletedLogEntry().populate_email(
                email=extra_email.email, user=extra_email.member, actor=actor
            ).save()
            extra_email.delete()
