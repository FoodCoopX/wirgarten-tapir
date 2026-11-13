import logging
import time

from django.core.cache import cache as redis_cache
from redis.lock import Lock

from tapir.accounts.exceptions import VerificationEmailsAlreadySendingException
from tapir.accounts.models import TapirUser
from tapir.accounts.services.email_verification_service import (
    EmailVerificationService,
)
from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager
from tapir.generic_exports.services.member_segment_provider import (
    MemberSegmentProvider,
)
from tapir.log.models import TextLogEntry
from tapir.wirgarten.models import Member
from tapir.wirgarten.service.email import send_email

LOG = logging.getLogger(__name__)


class UnverifiedMembersService:
    SECONDS_BETWEEN_MAILS = 3
    LOCK_KEY = "send_verification_emails_lock"
    LOCK_TIMEOUT_MARGIN_SECONDS = 10 * 60

    @classmethod
    def get_active_unverified_members(cls, cache: dict) -> list[Member]:
        members = MemberSegmentProvider.get_queryset_active_members(
            cache=cache
        ).exclude(keycloak_id__in=cls._get_verified_keycloak_ids())
        return list(members.order_by("member_no", "last_name", "first_name"))

    @classmethod
    def estimate_sending_duration_seconds(cls, member_count: int) -> int:
        return member_count * cls.SECONDS_BETWEEN_MAILS

    @classmethod
    def _get_verified_keycloak_ids(cls) -> set[str]:
        keycloak_users = KeycloakUserManager.get_keycloak_client().get_users(
            query={"briefRepresentation": True}
        )
        return {
            keycloak_user["id"]
            for keycloak_user in keycloak_users
            if keycloak_user.get("emailVerified")
        }

    @classmethod
    def is_sending_in_progress(cls) -> bool:
        return cls._build_lock(timeout=None).locked()

    @classmethod
    def _build_lock(cls, timeout: int | None) -> Lock:
        return redis_cache.lock(cls.LOCK_KEY, timeout=timeout)

    @classmethod
    def send_verification_emails(
        cls, members: list[Member], actor: TapirUser | None
    ) -> list[tuple[Member, str]]:
        lock = cls._build_lock(
            timeout=cls.estimate_sending_duration_seconds(member_count=len(members))
            + cls.LOCK_TIMEOUT_MARGIN_SECONDS
        )
        if not lock.acquire(blocking=False):
            raise VerificationEmailsAlreadySendingException()
        try:
            return cls._send_verification_emails_without_lock(
                members=members, actor=actor
            )
        finally:
            lock.release()

    @classmethod
    def _send_verification_emails_without_lock(
        cls, members: list[Member], actor: TapirUser | None
    ) -> list[tuple[Member, str]]:
        failures = []
        for index, member in enumerate(members):
            if index > 0:
                time.sleep(cls.SECONDS_BETWEEN_MAILS)
            try:
                KeycloakUserManager.create_keycloak_user_if_necessary(
                    user=member, initial_password=None
                )
                EmailVerificationService.send_verification_email(
                    user=member, actor=actor
                )
            except Exception as error:
                LOG.exception(f"Failed to send verification email to {member}")
                failures.append((member, str(error)))
                TextLogEntry().populate(
                    text=f"Verifizierungs-Email konnte nicht gesendet werden: {error}",
                    user=member,
                    actor=actor,
                ).save()
        return failures

    @classmethod
    def send_report(
        cls,
        recipient: TapirUser,
        member_count: int,
        failures: list[tuple[Member, str]],
        cache: dict,
    ) -> None:
        content = (
            f"Hallo {recipient.first_name},\n\n"
            f"der Versand der Verifizierungs-Emails ist abgeschlossen: "
            f"{member_count - len(failures)} von {member_count} Mails wurden gesendet.\n"
        )
        if failures:
            content += (
                "\nAn folgende Mitglieder konnte die Mail nicht gesendet werden:\n"
            )
            content += "".join(f"- {member} : {error}\n" for member, error in failures)
        send_email(
            to_email=[recipient.email],
            subject="Versand der Verifizierungs-Emails abgeschlossen",
            content=content,
            attachments=[],
            cache=cache,
        )
