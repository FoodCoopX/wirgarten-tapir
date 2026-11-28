from django.utils import timezone

from tapir.core.services.internal_recipient_manager import InternalRecipientManager
from tapir.mail.models import InternalRecipientCategoryRegistration, MailCategoryMode
from tapir.mail.tests.factories import MailCategoryFactory
from tapir.wirgarten.tests.factories import MemberExtraEmailFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestIsExtraEmailRegisteredToMailCategory(TapirIntegrationTest):
    def test_isExtraEmailRegisteredToMailCategory_noRegistration_followsTheExtraDefaults(
        self,
    ):
        extra_email = MemberExtraEmailFactory.create(confirmed_on=timezone.now())
        for mode, expected in [
            (MailCategoryMode.ALWAYS_ON, True),
            (MailCategoryMode.OPTIONAL_DEFAULT_ON, True),
            (MailCategoryMode.OPTIONAL_DEFAULT_OFF, False),
        ]:
            with self.subTest(mode=mode):
                mail_category = MailCategoryFactory.create(mode=mode)

                result = (
                    InternalRecipientManager.is_extra_email_registered_to_mail_category(
                        extra_email=extra_email, mail_category=mail_category
                    )
                )

                self.assertEqual(expected, result)

    def test_isExtraEmailRegisteredToMailCategory_extraHasRegistration_followsTheRegistrationEvenForAlwaysOn(
        self,
    ):
        extra_email = MemberExtraEmailFactory.create(confirmed_on=timezone.now())
        mail_category = MailCategoryFactory.create(mode=MailCategoryMode.ALWAYS_ON)
        InternalRecipientCategoryRegistration.objects.create(
            member_extra_email=extra_email,
            mail_category=mail_category,
            is_registered=False,
        )

        result = InternalRecipientManager.is_extra_email_registered_to_mail_category(
            extra_email=extra_email, mail_category=mail_category
        )

        self.assertFalse(result)
