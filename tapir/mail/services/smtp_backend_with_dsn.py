import email
import logging
import smtplib
from dataclasses import dataclass

from django.core.mail.backends.smtp import EmailBackend

LOG = logging.getLogger(__name__)


@dataclass
class SmtpResponse:
    code: int
    message: str


class SmtpBackendWithDsn(EmailBackend):
    def _send(self, original_message):
        """Send one message, capturing the SMTP response and requesting DSN if supported."""
        if not original_message.recipients():
            return False

        from_email = self.prep_address(original_message.from_email)
        recipients = [self.prep_address(addr) for addr in original_message.recipients()]
        prepared_message = original_message.message(policy=email.policy.SMTP)

        try:
            dsn_envid = getattr(prepared_message, "dsn_envid", None)
            server_supports_dsn = self.connection.has_extn("dsn")

            mail_options = []
            rcpt_options = []
            if server_supports_dsn:
                mail_options.append("RET=HDRS")
                rcpt_options.append("NOTIFY=SUCCESS,FAILURE,DELAY")
                if dsn_envid:
                    mail_options.append("ENVID=%s" % dsn_envid)

            self.connection.sendmail(
                from_addr=from_email,
                to_addrs=recipients,
                msg=prepared_message.as_bytes(),
                mail_options=mail_options,
                rcpt_options=rcpt_options,
            )

            original_message.smtp_response = SmtpResponse(
                code=250,
                message="No error detected",
            )
            return True

        except smtplib.SMTPResponseException as e:
            original_message.smtp_response = SmtpResponse(
                code=e.smtp_code,
                message=e.smtp_error.decode("utf-8", errors="replace"),
            )
            raise
