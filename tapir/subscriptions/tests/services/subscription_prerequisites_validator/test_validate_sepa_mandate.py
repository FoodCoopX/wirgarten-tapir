from django.core.exceptions import ValidationError

from tapir.subscriptions.services.subscription_prerequisites_validator import (
    SubscriptionPrerequisitesValidator,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestSubscriptionPrerequisitesValidatorValidateSepaMandate(TapirUnitTest):
    def test_validateSepaMandate_ibanEnteredWithoutConfirmation_raisesValidationError(
        self,
    ):
        with self.assertRaisesMessage(ValidationError, "SEPA-Mandat"):
            SubscriptionPrerequisitesValidator.validate_sepa_mandate(
                iban="NL76RABO8675663943", sepa_mandate_confirmed=False
            )

    def test_validateSepaMandate_ibanEnteredWithConfirmation_doesNotRaise(self):
        SubscriptionPrerequisitesValidator.validate_sepa_mandate(
            iban="NL76RABO8675663943", sepa_mandate_confirmed=True
        )

    def test_validateSepaMandate_noIbanEntered_doesNotRaise(self):
        SubscriptionPrerequisitesValidator.validate_sepa_mandate(
            iban=" ", sepa_mandate_confirmed=False
        )
