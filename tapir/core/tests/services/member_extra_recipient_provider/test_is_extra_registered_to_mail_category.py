from django.utils import timezone

from tapir.core.services.member_extra_recipient_provider import (
    MemberExtraRecipientProvider,
)
from tapir.mail.models import InternalRecipientCategoryRegistration, MailCategoryMode
from tapir.mail.tests.factories import MailCategoryFactory
from tapir.wirgarten.tests.factories import MemberExtraEmailFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestIsExtraRegisteredToMailCategory(TapirIntegrationTest):
    def test_isExtraRegisteredToMailCategory_noRegistration_followsTheExtraDefaults(
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
                    MemberExtraRecipientProvider.is_extra_registered_to_mail_category(
                        extra_email=extra_email, mail_category=mail_category
                    )
                )

                self.assertEqual(expected, result)

    def test_isExtraRegisteredToMailCategory_extraHasRegistration_followsTheRegistrationEvenForAlwaysOn(
        self,
    ):
        extra_email = MemberExtraEmailFactory.create(confirmed_on=timezone.now())
        mail_category = MailCategoryFactory.create(mode=MailCategoryMode.ALWAYS_ON)
        InternalRecipientCategoryRegistration.objects.create(
            member_extra_email=extra_email,
            mail_category=mail_category,
            is_registered=False,
        )

        result = MemberExtraRecipientProvider.is_extra_registered_to_mail_category(
            extra_email=extra_email, mail_category=mail_category
        )

        self.assertFalse(result)
