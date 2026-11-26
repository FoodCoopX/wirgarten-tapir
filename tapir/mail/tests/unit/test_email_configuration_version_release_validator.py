from tapir.mail.exceptions import TapirMailException
from tapir.mail.services.email_configuration_version_release_validator import (
    EmailConfigurationVersionReleaseValidator,
)
from tapir.mail.tests.factories import (
    EmailConfigurationVersionFactory,
    StaticSegmentFactory,
    MailCategoryFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestEmailConfigurationVersionReleaseValidator(TapirIntegrationTest):
    def test_validateVersionCanBeReleased_noTriggers_exceptionRaised(self):
        version = EmailConfigurationVersionFactory.build()

        version.triggers = None
        with self.assertRaises(TapirMailException) as error_context_1:
            EmailConfigurationVersionReleaseValidator.validate_version_can_be_released(
                version
            )
        self.assertEqual(str(error_context_1.exception), "Kein Trigger")

        version.triggers = {}
        with self.assertRaises(TapirMailException) as error_context_2:
            EmailConfigurationVersionReleaseValidator.validate_version_can_be_released(
                version
            )
        self.assertEqual(str(error_context_2.exception), "Kein Trigger")

    def test_validateVersionCanBeReleased_noSubject_exceptionRaised(self):
        version = EmailConfigurationVersionFactory.build()

        version.subject = None
        with self.assertRaises(TapirMailException) as error_context_1:
            EmailConfigurationVersionReleaseValidator.validate_version_can_be_released(
                version
            )
        self.assertEqual(str(error_context_1.exception), "Kein Betreff")

        version.subject = ""
        with self.assertRaises(TapirMailException) as error_context_2:
            EmailConfigurationVersionReleaseValidator.validate_version_can_be_released(
                version
            )
        self.assertEqual(str(error_context_2.exception), "Kein Betreff")

    def test_validateVersionCanBeReleased_noContent_exceptionRaised(self):
        version = EmailConfigurationVersionFactory.build()

        version.content = None
        with self.assertRaises(TapirMailException) as error_context_1:
            EmailConfigurationVersionReleaseValidator.validate_version_can_be_released(
                version
            )
        self.assertEqual(str(error_context_1.exception), "Kein Inhalt")

        version.content = ""
        with self.assertRaises(TapirMailException) as error_context_2:
            EmailConfigurationVersionReleaseValidator.validate_version_can_be_released(
                version
            )
        self.assertEqual(str(error_context_2.exception), "Kein Inhalt")

    def test_validateVersionCanBeReleased_noRecipients_exceptionRaised(self):
        version = EmailConfigurationVersionFactory.create()

        with self.assertRaises(TapirMailException) as error_context:
            EmailConfigurationVersionReleaseValidator.validate_version_can_be_released(
                version
            )
        self.assertEqual(str(error_context.exception), "Kein Empfänger")

    def test_validateVersionCanBeReleased_hasAdditiveDynamicSegments_noExceptionRaised(
        self,
    ):
        version = EmailConfigurationVersionFactory.create()
        version.dynamic_segments_additive = ["test_segment"]

        EmailConfigurationVersionReleaseValidator.validate_version_can_be_released(
            version
        )

    def test_validateVersionCanBeReleased_hasAdditiveStaticSegments_noExceptionRaised(
        self,
    ):
        version = EmailConfigurationVersionFactory.create()

        version.static_segments_additive.add(StaticSegmentFactory.create())

        EmailConfigurationVersionReleaseValidator.validate_version_can_be_released(
            version
        )

    def test_validateVersionCanBeReleased_hasMailCategory_noExceptionRaised(
        self,
    ):
        version = EmailConfigurationVersionFactory.create()

        version.mail_categories_additive.add(MailCategoryFactory.create())

        EmailConfigurationVersionReleaseValidator.validate_version_can_be_released(
            version
        )
