import datetime
import logging
import smtplib

from django.conf import settings
from django.core.cache import cache as redis_cache
from django.core.mail import get_connection, EmailMultiAlternatives
from django.core.mail.backends.base import BaseEmailBackend
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from tapir.mail.addressed_recipient import AddressedRecipient
from tapir.mail.config import BccProvider, ExternalConfig
from tapir.mail.models import EmailConfigurationDispatch, EmailDispatch, ReleaseStatus
from tapir.mail.services.email import build_email
from tapir.mail.services.layout import render_email_mjml
from tapir.mail.services.mjml import mjml2html
from tapir.mail.services.recipient_list_provider import (
    RecipientListProvider,
)
from tapir.mail.services.token import (
    find_tokens,
    replace_tokens,
    resolve_recipient_tokens,
    TOKEN_TYPE_RECIPIENT,
    TOKEN_TYPE_DYNAMIC,
    resolve_dynamic_tokens,
)
from tapir.mail.services.tracking import get_tracking_url
from tapir.mail.services.triggers import trigger_registry
from tapir.mail.triggers.time_trigger import TimeTrigger

LOG = logging.getLogger(__name__)


class ResolveAndCreateEmailDispatches:
    """
    This class is responsible for resolving the Segment data and creating EmailDispatches for EmailConfigurationDispatches that are due to be sent.
    """

    MAX_RETRIES = 10

    @classmethod
    def resolve_and_create(cls):
        lock = redis_cache.lock(
            "resolve_and_create_email_dispatches", timeout=60 * 3
        )  # 3 minutes
        if not lock.acquire(blocking=False):
            LOG.error(
                "Could not acquire lock for resolve_and_create_email_dispatches lock"
            )
            return

        try:
            config_dispatches = (
                cls._get_email_configuration_dispatches_that_should_be_sent().order_by(
                    "scheduled_time"
                )[:10]
            )
            if not config_dispatches:
                return

            cache = {}
            for config_dispatch in config_dispatches:
                cache_key = f"dispatch_retry_count_{config_dispatch.id}"
                try:
                    cls._create_email_dispatches(
                        config_dispatch=config_dispatch, cache=cache
                    )
                    redis_cache.delete(cache_key)
                except Exception as e:
                    retry_count = redis_cache.get(cache_key, 0) + 1
                    redis_cache.set(
                        cache_key, retry_count, timeout=60 * 30
                    )  # 30 minutes

                    if retry_count > cls.MAX_RETRIES:
                        LOG.error(
                            f"Retried {cls.MAX_RETRIES} times. Giving up and setting EmailConfigurationVersion#{config_dispatch.email_configuration_version.id}-{config_dispatch.email_configuration_version.email_configuration.name} to ERROR."
                        )
                        config_dispatch.email_configuration_version.status = (
                            ReleaseStatus.ERROR
                        )
                        config_dispatch.email_configuration_version.save()
                        redis_cache.delete(cache_key)
                    else:
                        LOG.exception(
                            f"Error while creating email dispatches for EmailConfigurationDispatch#{config_dispatch.id}. Retrying... Error: {e}"
                        )

        finally:
            lock.release()

    @classmethod
    @transaction.atomic
    def _create_email_dispatches(
        cls, config_dispatch: EmailConfigurationDispatch, cache: dict
    ):
        recipients = (
            RecipientListProvider.get_recipient_list_from_email_configuration_dispatch(
                email_configuration_dispatch=config_dispatch, cache=cache
            )
        )

        effective_content = render_email_mjml(
            config_dispatch.email_configuration_version
        )

        recipient_tokens = find_tokens(
            effective_content,
            token_type=TOKEN_TYPE_RECIPIENT,
        )

        dynamic_tokens = find_tokens(
            effective_content,
            token_type=TOKEN_TYPE_DYNAMIC,
        )

        EmailDispatch.objects.bulk_create(
            [
                cls._build_email_dispatch(
                    config_dispatch=config_dispatch,
                    addressed_recipient=addressed_recipient,
                    recipient_tokens=recipient_tokens,
                    dynamic_tokens=dynamic_tokens,
                    cache=cache,
                )
                for addressed_recipient in recipients
            ]
        )

        config_dispatch.is_sent = True
        config_dispatch.save()

    @staticmethod
    def _build_email_dispatch(
        config_dispatch: EmailConfigurationDispatch,
        addressed_recipient: AddressedRecipient,
        recipient_tokens,
        dynamic_tokens,
        cache: dict,
    ):
        recipient = addressed_recipient.recipient
        resolved_tokens = resolve_recipient_tokens(
            tokens_to_resolve=recipient_tokens, recipient=recipient, cache=cache
        ) | resolve_dynamic_tokens(
            tokens_to_resolve=dynamic_tokens, recipient=recipient, cache=cache
        )
        for token, value in addressed_recipient.token_overrides.items():
            if token in resolved_tokens:
                resolved_tokens[token] = value

        return EmailDispatch(
            email_configuration_dispatch=config_dispatch,
            recipient=addressed_recipient.email,
            recipient_tokens=resolved_tokens,
            additional_tokens=config_dispatch.additional_tokens,
            created_at=config_dispatch.scheduled_time,
        )

    @staticmethod
    def _get_email_configuration_dispatches_that_should_be_sent():
        return EmailConfigurationDispatch.objects.filter(
            is_sent=False,
            scheduled_time__lte=timezone.now(),
            email_configuration_version__status=ReleaseStatus.RELEASED,
        )


class SendEmailBatch:
    """
    This class is responsible for sending a batch of EmailDispatches.
    """

    @classmethod
    def send_email_dispatches(cls, batch_size=None):
        lock = redis_cache.lock("send_email_task_lock", timeout=1800)
        if not lock.acquire(blocking=False):
            LOG.error("Could not acquire lock for send_email_task_lock")
            return

        try:
            if not batch_size:
                batch_size = getattr(settings, "EMAIL_DISPATCH_BATCH_SIZE", 50)

            batch = (
                EmailDispatch.objects.filter(sent_time=None, error_message=None)
                .filter(Q(not_before=None) | Q(not_before__lte=timezone.now()))
                .exclude(
                    Q(
                        email_configuration_version__isnull=True,
                        email_configuration_dispatch__email_configuration_version__status=ReleaseStatus.ERROR,
                    )
                    | Q(email_configuration_version__status=ReleaseStatus.ERROR)
                )
                .order_by("created_at")
                .prefetch_related("email_configuration_dispatch")
                .prefetch_related(
                    "email_configuration_dispatch__email_configuration_version"
                )
                .prefetch_related("email_configuration_version")[:batch_size]
            )
            cls._send_batch(batch)
        finally:
            lock.release()

    @classmethod
    def _send_batch(cls, email_dispatches):
        if not email_dispatches:
            LOG.warning("Nothing to do in send_batch")
            return

        emails = cls._prepare_emails(email_dispatches)

        if not emails:
            LOG.warning(
                f"No emails to send in batch for EmailConfigurationDispatch#{email_dispatches[0].email_configuration_dispatch.id}"
            )
            return

        sent_emails = {}
        try:
            with get_connection() as connection:
                for email_message, email_dispatch in emails:
                    success = cls.send_single_mail(
                        email_message=email_message,
                        email_dispatch=email_dispatch,
                        connection=connection,
                    )
                    if success:
                        sent_emails[email_message] = email_dispatch
        except Exception as e:
            LOG.exception(f"Error with SMTP connection: {e}")
            dispatches_to_update = [
                email_dispatch
                for email_message, email_dispatch in emails
                if email_message not in sent_emails
                and email_dispatch.error_message is None
            ]
            for dispatch in dispatches_to_update:
                dispatch.error_message = str(e)
            EmailDispatch.objects.bulk_update(dispatches_to_update, ["error_message"])
            for dispatch in dispatches_to_update:
                RetryEmailDispatch.schedule_automatic_retry(dispatch, e)

        LOG.info(f"Sent {len(sent_emails)} emails in this batch")
        cls._post_send(sent_emails)

    @classmethod
    def send_single_mail(
        cls,
        email_message: EmailMultiAlternatives,
        email_dispatch: EmailDispatch,
        connection: BaseEmailBackend,
    ):
        email_message.dsn_envid = email_dispatch.id
        try:
            connection.send_messages([email_message])

            smtp_response = getattr(email_message, "smtp_response", None)
            if smtp_response:
                email_dispatch.smtp_response_code = smtp_response.code
                email_dispatch.smtp_response_message = smtp_response.message

            return True
        except Exception as e:
            LOG.exception(
                f"Error while sending email to {email_dispatch.recipient}: {e}"
            )
            smtp_response = getattr(email_message, "smtp_response", None)
            if smtp_response:
                email_dispatch.smtp_response_code = smtp_response.code
                email_dispatch.smtp_response_message = smtp_response.message
            email_dispatch.error_message = str(e)
            email_dispatch.save()
            RetryEmailDispatch.schedule_automatic_retry(email_dispatch, e)
            return False

    @classmethod
    def _prepare_emails(cls, email_dispatches):
        emails = []
        # Rendering MJML starts a node process, so each version is rendered only once
        # and the tokens are replaced in the resulting HTML.
        html_by_version_id = {}
        cache = {}
        for email_dispatch in email_dispatches:
            version = email_dispatch.get_email_configuration_version()

            try:
                if version.id not in html_by_version_id:
                    html_by_version_id[version.id] = mjml2html(
                        render_email_mjml(version)
                    )

                html = replace_tokens(
                    html_by_version_id[version.id],
                    email_dispatch.recipient_tokens,
                    email_dispatch.additional_tokens,
                    cache=cache,
                )

                email = build_email(
                    html=html,
                    subject=version.subject,
                    recipients=[email_dispatch.recipient],
                    tracking_url=get_tracking_url(email_dispatch),
                    tracking_id=email_dispatch.id,
                    bcc_provider=cls._get_bcc_provider(email_dispatch),
                )
                emails.append((email, email_dispatch))
            except Exception as e:
                LOG.exception(
                    f"Error while preparing email to {email_dispatch.recipient}: {e}"
                )
                with transaction.atomic():
                    email_dispatch.error_message = str(e)
                    email_dispatch.save()

        return emails

    @classmethod
    def _get_bcc_provider(cls, email_dispatch: EmailDispatch) -> BccProvider | None:
        for trigger_data in (
            email_dispatch.get_email_configuration_version().triggers or []
        ):
            trigger_class = trigger_registry.get(
                trigger_data["trigger_id"],
                None,
            )
            if trigger_class:
                if trigger_class == TimeTrigger:
                    return ExternalConfig.MASS_MAIL_BCC_PROVIDER
                else:
                    return ExternalConfig.TRANSACTIONAL_MAIL_BCC_PROVIDER
        return None

    @classmethod
    def _post_send(cls, emails):
        for email, email_dispatch in emails.items():
            try:
                with transaction.atomic():
                    for trigger_data in (
                        email_dispatch.get_email_configuration_version().triggers or []
                    ):
                        trigger_class = trigger_registry.get(
                            trigger_data["trigger_id"],
                            None,
                        )
                        if trigger_class:
                            trigger_class.after_mail_sent(email_dispatch)

                    email_dispatch.sent_time = timezone.now()
                    email_dispatch.save()
            except Exception as e:
                LOG.exception(
                    f"Error after sending email to {email_dispatch.recipient}: {e}"
                )
                with transaction.atomic():
                    email_dispatch.error_message = str(e)
                    email_dispatch.save()


class RetryEmailDispatch:
    AUTOMATIC_RETRY_DELAYS = [
        datetime.timedelta(minutes=5),
        datetime.timedelta(minutes=30),
        datetime.timedelta(hours=2),
    ]

    @classmethod
    def _copy_email_dispatch(cls, email_dispatch: EmailDispatch):
        return EmailDispatch(
            email_configuration_dispatch=email_dispatch.email_configuration_dispatch,
            email_configuration_version=cls._get_released_version(email_dispatch),
            recipient=email_dispatch.recipient,
            recipient_tokens=email_dispatch.recipient_tokens,
            additional_tokens=email_dispatch.additional_tokens,
        )

    @staticmethod
    def is_temporary_failure(exception: Exception) -> bool:
        if isinstance(exception, smtplib.SMTPRecipientsRefused):
            return all(400 <= code < 500 for code, _ in exception.recipients.values())
        if isinstance(
            exception, (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected)
        ):
            return True
        if isinstance(exception, smtplib.SMTPResponseException):
            return 400 <= exception.smtp_code < 500
        if isinstance(exception, smtplib.SMTPException):
            return False
        return isinstance(exception, OSError)

    @classmethod
    def schedule_automatic_retry(cls, email_dispatch: EmailDispatch, exception):
        if not cls.is_temporary_failure(exception):
            return

        retry_count = email_dispatch.get_consecutive_automatic_retry_count()
        if retry_count >= len(cls.AUTOMATIC_RETRY_DELAYS):
            LOG.warning(
                f"EmailDispatch#{email_dispatch.id} reached the maximum number of automatic retries"
            )
            return

        cls.retry(
            email_dispatch,
            not_before=timezone.now() + cls.AUTOMATIC_RETRY_DELAYS[retry_count],
            is_automatic_retry=True,
        )

    @classmethod
    def _get_released_version(cls, email_dispatch: EmailDispatch):
        current_version = email_dispatch.get_email_configuration_version()
        return (
            current_version.email_configuration.versions.filter(
                status=ReleaseStatus.RELEASED
            )
            .order_by("-updated_at")
            .first()
            or current_version
        )

    @classmethod
    @transaction.atomic
    def retry(
        cls,
        email_dispatch: EmailDispatch,
        not_before=None,
        is_automatic_retry=False,
    ):
        most_recent_dispatch = email_dispatch
        while most_recent_dispatch.next_retry is not None:
            most_recent_dispatch = most_recent_dispatch.next_retry

        if (
            most_recent_dispatch.sent_time is None
            and most_recent_dispatch.error_message is None
            and most_recent_dispatch.bounce_message is None
        ):
            raise ValueError(
                f"EmailDispatch#{email_dispatch.id} has not been sent yet. Cannot retry."
                if most_recent_dispatch.id == email_dispatch.id
                else f"EmailDispatch#{email_dispatch.id} already has a pending retry: EmailDispatch#{most_recent_dispatch.id}"
            )

        LOG.info(f"Retrying EmailDispatch#{most_recent_dispatch.id}")

        retry_dispatch = cls._copy_email_dispatch(most_recent_dispatch)
        retry_dispatch.not_before = not_before
        retry_dispatch.is_automatic_retry = is_automatic_retry
        retry_dispatch.save()

        most_recent_dispatch.next_retry = retry_dispatch
        most_recent_dispatch.save()

        return retry_dispatch

    @classmethod
    @transaction.atomic
    def retry_all_failed(cls, email_configuration_dispatch: EmailConfigurationDispatch):
        failed_dispatches = email_configuration_dispatch.emaildispatch_set.filter(
            next_retry__isnull=True,  # Select only the most recent dispatches in each chain
        ).with_error(True)
        for email_dispatch in failed_dispatches:
            cls.retry(email_dispatch)

        LOG.info(
            f"Retried failed EmailDispatches for EmailConfigurationDispatch#{email_configuration_dispatch.id}"
        )

        return failed_dispatches.count()
