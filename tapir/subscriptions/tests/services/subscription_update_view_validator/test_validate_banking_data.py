import datetime
from unittest.mock import patch, Mock

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from tapir.coop.services.member_needs_banking_data_checker import (
    MemberNeedsBankingDataChecker,
)
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.subscriptions.services.subscription_update_view_validator import (
    SubscriptionUpdateViewValidator,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.test_utils import mock_timezone


@patch.object(
    MemberPaymentRhythmService, "get_allowed_rhythms", return_value=[], autospec=True
)
@patch.object(MemberPaymentRhythmService, "is_payment_rhythm_allowed", autospec=True)
@patch.object(TapirCache, "get_member_payment_rhythm_object", autospec=True)
@patch.object(
    MemberNeedsBankingDataChecker, "does_member_need_banking_data", autospec=True
)
class TestSubscriptionUpdateViewValidatorValidateBankingData(SimpleTestCase):
    def setUp(self):
        self.now = mock_timezone(
            test=self, now=datetime.datetime(year=2024, month=5, day=1)
        )

    def build_default_params(self):
        self.member = Mock()
        self.cache = Mock()
        return {
            "member": self.member,
            "account_owner": "test_account_owner",
            "iban": "NL76RABO8675663943",
            "payment_rhythm": "test_rhythm",
            "cache": self.cache,
        }

    def assert_raises_validation_error(self, error_message: str, **params):
        with self.assertRaises(ValidationError) as error:
            SubscriptionUpdateViewValidator.validate_banking_data(**params)

        self.assertEqual(error_message, error.exception.message)

    def test_validateBankingData_memberNeedsBankingDataAndInvalidIban_raisesValidationError(
        self,
        mock_does_member_need_banking_data: Mock,
        *other_mocks,
    ):
        mock_does_member_need_banking_data.return_value = True
        params = self.build_default_params()
        params["iban"] = "invalid_iban"

        self.assert_raises_validation_error(
            "%(country_code)s is not a valid country code for IBAN.", **params
        )

        mock_does_member_need_banking_data.assert_called_once_with(self.member)

        for mock in other_mocks:
            mock.assert_not_called()

    def test_validateBankingData_memberNeedsBankingDataAndEmptyAccountOwner_raisesValidationError(
        self,
        mock_does_member_need_banking_data: Mock,
        *other_mocks,
    ):
        mock_does_member_need_banking_data.return_value = True
        params = self.build_default_params()
        params["account_owner"] = ""

        self.assert_raises_validation_error(
            "Das Feld 'Kontoinhaber*in' muss ausgefüllt sein", **params
        )

        mock_does_member_need_banking_data.assert_called_once_with(self.member)

        for mock in other_mocks:
            mock.assert_not_called()

    def test_validateBankingData_memberDoesNotNeedBankingData_doesNotValidateIbanOrAccountOwner(
        self,
        mock_does_member_need_banking_data: Mock,
        mock_get_member_payment_rhythm_object: Mock,
        *other_mocks,
    ):
        mock_does_member_need_banking_data.return_value = False
        mock_get_member_payment_rhythm_object.return_value = Mock()
        params = self.build_default_params()
        params["iban"] = "invalid_iban"
        params["account_owner"] = ""
        params["payment_rhythm"] = None

        SubscriptionUpdateViewValidator.validate_banking_data(**params)

        mock_does_member_need_banking_data.assert_called_once_with(self.member)
        mock_get_member_payment_rhythm_object.assert_called_once_with(
            member=self.member, reference_date=self.now.date(), cache=self.cache
        )

        for mock in other_mocks:
            mock.assert_not_called()

    def test_validateBankingData_needsPaymentRhythmAndNoneProvided_raisesValidationError(
        self,
        mock_does_member_need_banking_data: Mock,
        mock_get_member_payment_rhythm_object: Mock,
        *other_mocks,
    ):
        mock_does_member_need_banking_data.return_value = False
        mock_get_member_payment_rhythm_object.return_value = None
        params = self.build_default_params()
        params["payment_rhythm"] = None

        self.assert_raises_validation_error("Das Zahlungsintervall fehlt", **params)

        mock_does_member_need_banking_data.assert_called_once_with(self.member)
        mock_get_member_payment_rhythm_object.assert_called_once_with(
            member=self.member, reference_date=self.now.date(), cache=self.cache
        )

        for mock in other_mocks:
            mock.assert_not_called()

    def test_validateBankingData_doesNotNeedPaymentRhythmAndNoneProvided_doesNotRaise(
        self,
        mock_does_member_need_banking_data: Mock,
        mock_get_member_payment_rhythm_object: Mock,
        *other_mocks,
    ):
        mock_does_member_need_banking_data.return_value = False
        mock_get_member_payment_rhythm_object.return_value = Mock()
        params = self.build_default_params()
        params["payment_rhythm"] = None

        SubscriptionUpdateViewValidator.validate_banking_data(**params)

        mock_does_member_need_banking_data.assert_called_once_with(self.member)
        mock_get_member_payment_rhythm_object.assert_called_once_with(
            member=self.member, reference_date=self.now.date(), cache=self.cache
        )

        for mock in other_mocks:
            mock.assert_not_called()

    def test_validateBankingData_paymentRhythmNotAllowed_raisesValidationError(
        self,
        mock_does_member_need_banking_data: Mock,
        mock_get_member_payment_rhythm_object: Mock,
        mock_is_payment_rhythm_allowed: Mock,
        mock_get_allowed_rhythms: Mock,
    ):
        mock_does_member_need_banking_data.return_value = False
        mock_get_member_payment_rhythm_object.return_value = Mock()
        mock_is_payment_rhythm_allowed.return_value = False
        params = self.build_default_params()

        self.assert_raises_validation_error(
            "Diese Zahlungsintervall test_rhythm is nicht erlaubt, erlaubt sind: []",
            **params,
        )

        mock_does_member_need_banking_data.assert_called_once_with(self.member)
        mock_get_member_payment_rhythm_object.assert_called_once_with(
            member=self.member, reference_date=self.now.date(), cache=self.cache
        )
        mock_is_payment_rhythm_allowed.assert_called_once_with(
            "test_rhythm", cache=self.cache
        )
        mock_get_allowed_rhythms.assert_called_once_with(cache=self.cache)

    def test_validateBankingData_paymentRhythmAllowed_doesNotRaise(
        self,
        mock_does_member_need_banking_data: Mock,
        mock_get_member_payment_rhythm_object: Mock,
        mock_is_payment_rhythm_allowed: Mock,
        mock_get_allowed_rhythms: Mock,
    ):
        mock_does_member_need_banking_data.return_value = False
        mock_get_member_payment_rhythm_object.return_value = Mock()
        mock_is_payment_rhythm_allowed.return_value = True
        params = self.build_default_params()

        SubscriptionUpdateViewValidator.validate_banking_data(**params)

        mock_does_member_need_banking_data.assert_called_once_with(self.member)
        mock_get_member_payment_rhythm_object.assert_called_once_with(
            member=self.member, reference_date=self.now.date(), cache=self.cache
        )
        mock_is_payment_rhythm_allowed.assert_called_once_with(
            "test_rhythm", cache=self.cache
        )

        mock_get_allowed_rhythms.assert_not_called()

    def test_validateBankingData_allValid_doesNotRaise(
        self,
        mock_does_member_need_banking_data: Mock,
        mock_get_member_payment_rhythm_object: Mock,
        mock_is_payment_rhythm_allowed: Mock,
        mock_get_allowed_rhythms: Mock,
    ):
        mock_does_member_need_banking_data.return_value = True
        mock_get_member_payment_rhythm_object.return_value = None
        mock_is_payment_rhythm_allowed.return_value = True
        params = self.build_default_params()

        SubscriptionUpdateViewValidator.validate_banking_data(**params)

        mock_does_member_need_banking_data.assert_called_once_with(self.member)
        mock_get_member_payment_rhythm_object.assert_called_once_with(
            member=self.member, reference_date=self.now.date(), cache=self.cache
        )
        mock_is_payment_rhythm_allowed.assert_called_once_with(
            "test_rhythm", cache=self.cache
        )

        mock_get_allowed_rhythms.assert_not_called()
