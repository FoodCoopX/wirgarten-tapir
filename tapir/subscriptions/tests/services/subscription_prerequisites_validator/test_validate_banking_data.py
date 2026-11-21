from unittest.mock import patch, Mock

from django.core.exceptions import ValidationError

from tapir.coop.services.member_needs_banking_data_checker import (
    MemberNeedsBankingDataChecker,
)
from tapir.subscriptions.services.subscription_prerequisites_validator import (
    SubscriptionPrerequisitesValidator,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(
    MemberNeedsBankingDataChecker, "does_member_need_banking_data", autospec=True
)
class TestSubscriptionPrerequisitesValidatorValidateBankingData(TapirUnitTest):
    def build_default_params(self):
        self.member = Mock()
        return {
            "member": self.member,
            "account_owner": "test_account_owner",
            "iban": "NL76RABO8675663943",
        }

    def test_validateBankingData_memberNeedsBankingDataAndInvalidIban_raisesValidationError(
        self, mock_does_member_need_banking_data: Mock
    ):
        mock_does_member_need_banking_data.return_value = True
        params = self.build_default_params()
        params["iban"] = "invalid_iban"

        with self.assertRaisesMessage(
            ValidationError, "IN is not a valid country code for IBAN."
        ):
            SubscriptionPrerequisitesValidator.validate_banking_data(**params)

        mock_does_member_need_banking_data.assert_called_once_with(self.member)

    def test_validateBankingData_memberNeedsBankingDataAndEmptyAccountOwner_raisesValidationError(
        self, mock_does_member_need_banking_data: Mock
    ):
        mock_does_member_need_banking_data.return_value = True
        params = self.build_default_params()
        params["account_owner"] = ""

        with self.assertRaisesMessage(
            ValidationError, "Das Feld 'Kontoinhaber*in' muss ausgefüllt sein"
        ):
            SubscriptionPrerequisitesValidator.validate_banking_data(**params)

        mock_does_member_need_banking_data.assert_called_once_with(self.member)

    def test_validateBankingData_memberDoesNotNeedBankingData_doesNotValidateIbanOrAccountOwner(
        self, mock_does_member_need_banking_data: Mock
    ):
        mock_does_member_need_banking_data.return_value = False
        params = self.build_default_params()
        params["iban"] = "invalid_iban"
        params["account_owner"] = ""

        SubscriptionPrerequisitesValidator.validate_banking_data(**params)

        mock_does_member_need_banking_data.assert_called_once_with(self.member)

    def test_validateBankingData_allValid_doesNotRaise(
        self, mock_does_member_need_banking_data: Mock
    ):
        mock_does_member_need_banking_data.return_value = True
        params = self.build_default_params()

        SubscriptionPrerequisitesValidator.validate_banking_data(**params)

        mock_does_member_need_banking_data.assert_called_once_with(self.member)
