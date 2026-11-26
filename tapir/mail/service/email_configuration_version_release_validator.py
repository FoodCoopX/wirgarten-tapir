from tapir.mail.exceptions import TapirMailException
from tapir.mail.models import EmailConfigurationVersion


class EmailConfigurationVersionReleaseValidator:
    @classmethod
    def validate_version_can_be_released(cls, version: EmailConfigurationVersion):
        if version.triggers is None or len(version.triggers) == 0:
            raise TapirMailException("Kein Trigger")

        if version.subject is None or len(version.subject) == 0:
            raise TapirMailException("Kein Betreff")

        if version.content is None or len(version.content) == 0:
            raise TapirMailException("Kein Inhalt")

        if (
            len(version.dynamic_segments_additive)
            + version.static_segments_additive.count()
            + version.mail_categories_additive.count()
            == 0
        ):
            raise TapirMailException("Kein Empfänger")
