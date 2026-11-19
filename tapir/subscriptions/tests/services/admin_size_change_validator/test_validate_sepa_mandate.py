from django.core.exceptions import ValidationError

from tapir.subscriptions.services.admin_size_change_validator import (
    AdminSizeChangeValidator,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestAdminSizeChangeValidatorValidateSepaMandate(TapirUnitTest):
    def test_validateSepaMandate_ibanEnteredWithoutConfirmation_raisesValidationError(
        self,
    ):
        with self.assertRaisesMessage(ValidationError, "SEPA-Mandat"):
            AdminSizeChangeValidator.validate_sepa_mandate(
                iban="NL76RABO8675663943", sepa_mandate_confirmed=False
            )

    def test_validateSepaMandate_ibanEnteredWithConfirmation_doesNotRaise(self):
        AdminSizeChangeValidator.validate_sepa_mandate(
            iban="NL76RABO8675663943", sepa_mandate_confirmed=True
        )

    def test_validateSepaMandate_noIbanEntered_doesNotRaise(self):
        AdminSizeChangeValidator.validate_sepa_mandate(
            iban=" ", sepa_mandate_confirmed=False
        )
