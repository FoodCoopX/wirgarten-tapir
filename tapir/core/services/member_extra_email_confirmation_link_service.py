from django.core.signing import BadSignature, TimestampSigner
from django.http import Http404

from tapir.core.config import EXTRA_EMAIL_CONFIRMATION_LINK_VALIDITY
from tapir.wirgarten.models import MemberExtraEmail


class MemberExtraEmailConfirmationLinkService:
    SALT = "tapir.core.member_extra_email_confirmation"

    @classmethod
    def build_token(cls, extra_email: MemberExtraEmail) -> str:
        return TimestampSigner(salt=cls.SALT).sign(extra_email.id)

    @classmethod
    def get_extra_email_from_token(cls, token: str) -> MemberExtraEmail:
        try:
            extra_email_id = TimestampSigner(salt=cls.SALT).unsign(
                token,
                max_age=EXTRA_EMAIL_CONFIRMATION_LINK_VALIDITY,
            )
        except BadSignature:
            # also raised for expired links (SignatureExpired)
            raise Http404("Der Link ist ungültig oder abgelaufen.")

        extra_email = MemberExtraEmail.objects.filter(id=extra_email_id).first()
        if extra_email is None:
            raise Http404("Der Link ist ungültig oder abgelaufen.")
        return extra_email
