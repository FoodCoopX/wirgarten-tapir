from unittest.mock import patch, Mock

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from tapir.bestell_wizard.services.bestell_wizard_order_validator import (
    BestellWizardOrderValidator,
)
from tapir.coop.services.personal_data_validator import PersonalDataValidator
from tapir.solidarity_contribution.services.solidarity_validator import (
    SolidarityValidator,
)
from tapir.subscriptions.services.tapir_order_builder import TapirOrderBuilder


class TestValidateOrderAndUserData(SimpleTestCase):
    @patch.object(
        PersonalDataValidator, "validate_personal_data_new_member", autospec=True
    )
    def test_validateOrderAndUserData_sepaNotAllowed_raisesValidationError(
        self, mock_validate_personal_data_new_member: Mock
    ):
        data = {
            "personal_data": {
                "email": "test_mail",
                "phone_number": "test_phone_number",
                "iban": "test_iban",
                "account_owner": "test_account_owner",
            },
            "payment_rhythm": "test_payment_rhythm",
            "sepa_allowed": False,
        }
        cache = Mock()

        with self.assertRaises(ValidationError) as error:
            BestellWizardOrderValidator.validate_order_and_user_data(
                validated_serializer_data=data, contract_start_date=Mock(), cache=cache
            )

        self.assertEqual("SEPA-Mandat muss erlaubt sein", error.exception.message)

        mock_validate_personal_data_new_member.assert_called_once_with(
            email="test_mail",
            phone_number="test_phone_number",
            iban="test_iban",
            account_owner="test_account_owner",
            cache=cache,
            check_waiting_list=True,
            payment_rhythm="test_payment_rhythm",
        )

    @patch.object(BestellWizardOrderValidator, "is_contract_required", autospec=True)
    @patch.object(
        PersonalDataValidator, "validate_personal_data_new_member", autospec=True
    )
    def test_validateOrderAndUserData_contractRequiredButNotAccepted_raisesValidationError(
        self,
        mock_validate_personal_data_new_member: Mock,
        mock_is_contract_required: Mock,
    ):
        data = {
            "personal_data": {
                "email": "test_mail",
                "phone_number": "test_phone_number",
                "iban": "test_iban",
                "account_owner": "test_account_owner",
            },
            "payment_rhythm": "test_payment_rhythm",
            "sepa_allowed": True,
            "contract_accepted": False,
        }
        cache = Mock()
        mock_is_contract_required.return_value = True

        with self.assertRaises(ValidationError) as error:
            BestellWizardOrderValidator.validate_order_and_user_data(
                validated_serializer_data=data, contract_start_date=Mock(), cache=cache
            )

        self.assertEqual(
            "Vertragsgrundsätze müssen akzeptiert sein", error.exception.message
        )

        mock_validate_personal_data_new_member.assert_called_once_with(
            email="test_mail",
            phone_number="test_phone_number",
            iban="test_iban",
            account_owner="test_account_owner",
            cache=cache,
            check_waiting_list=True,
            payment_rhythm="test_payment_rhythm",
        )
        mock_is_contract_required.assert_called_once_with(cache=cache)

    @patch(
        "tapir.bestell_wizard.services.bestell_wizard_order_validator.legal_status_is_cooperative",
        autospec=True,
    )
    @patch.object(BestellWizardOrderValidator, "validate_order", autospec=True)
    @patch.object(BestellWizardOrderValidator, "is_contract_required", autospec=True)
    @patch.object(
        PersonalDataValidator, "validate_personal_data_new_member", autospec=True
    )
    def test_validateOrderAndUserData_contractNotRequiredAndNotAccepted_noErrorRaised(
        self,
        mock_validate_personal_data_new_member: Mock,
        mock_is_contract_required: Mock,
        mock_validate_order: Mock,
        mock_legal_status_is_cooperative: Mock,
    ):
        pickup_location_ids = Mock()
        contract_start_date = Mock()
        data = {
            "personal_data": {
                "email": "test_mail",
                "phone_number": "test_phone_number",
                "iban": "test_iban",
                "account_owner": "test_account_owner",
            },
            "payment_rhythm": "test_payment_rhythm",
            "sepa_allowed": True,
            "contract_accepted": False,
            "shopping_cart_order": {},
            "solidarity_contribution": 0,
            "pickup_location_ids": pickup_location_ids,
        }
        cache = Mock()
        mock_is_contract_required.return_value = False
        mock_legal_status_is_cooperative.return_value = False

        BestellWizardOrderValidator.validate_order_and_user_data(
            validated_serializer_data=data,
            contract_start_date=contract_start_date,
            cache=cache,
        )

        mock_validate_personal_data_new_member.assert_called_once_with(
            email="test_mail",
            phone_number="test_phone_number",
            iban="test_iban",
            account_owner="test_account_owner",
            cache=cache,
            check_waiting_list=True,
            payment_rhythm="test_payment_rhythm",
        )
        mock_is_contract_required.assert_called_once_with(cache=cache)
        mock_validate_order.assert_called_once_with(
            pickup_location_ids=pickup_location_ids,
            contract_start_date=contract_start_date,
            order={},
            cache=cache,
        )
        mock_legal_status_is_cooperative.assert_called_once_with(cache=cache)

    @patch.object(
        TapirOrderBuilder,
        "build_tapir_order_from_shopping_cart_serializer",
        autospec=True,
    )
    @patch.object(
        BestellWizardOrderValidator, "is_cancellation_policy_required", autospec=True
    )
    @patch.object(BestellWizardOrderValidator, "is_contract_required", autospec=True)
    @patch.object(
        PersonalDataValidator, "validate_personal_data_new_member", autospec=True
    )
    def test_validateOrderAndUserData_cancellationPolicyRequiredButNotAccepted_validationErrorRaised(
        self,
        mock_validate_personal_data_new_member: Mock,
        mock_is_contract_required: Mock,
        mock_is_cancellation_policy_required: Mock,
        mock_build_tapir_order_from_shopping_cart_serializer: Mock,
    ):
        contract_start_date = Mock()
        shopping_cart = Mock()
        order = Mock()
        data = {
            "personal_data": {
                "email": "test_mail",
                "phone_number": "test_phone_number",
                "iban": "test_iban",
                "account_owner": "test_account_owner",
            },
            "payment_rhythm": "test_payment_rhythm",
            "sepa_allowed": True,
            "shopping_cart_order": shopping_cart,
            "cancellation_policy_read": False,
            "solidarity_contribution": 12,
        }
        cache = Mock()
        mock_is_contract_required.return_value = False
        mock_is_cancellation_policy_required.return_value = True
        mock_build_tapir_order_from_shopping_cart_serializer.return_value = order

        with self.assertRaises(ValidationError) as error:
            BestellWizardOrderValidator.validate_order_and_user_data(
                validated_serializer_data=data,
                contract_start_date=contract_start_date,
                cache=cache,
            )

        self.assertEqual(
            "Die Widerrufsbelehrung muss akzeptiert sein", error.exception.message
        )

        mock_validate_personal_data_new_member.assert_called_once_with(
            email="test_mail",
            phone_number="test_phone_number",
            iban="test_iban",
            account_owner="test_account_owner",
            cache=cache,
            check_waiting_list=True,
            payment_rhythm="test_payment_rhythm",
        )
        mock_is_contract_required.assert_called_once_with(cache=cache)
        mock_build_tapir_order_from_shopping_cart_serializer.assert_called_once_with(
            shopping_cart=shopping_cart, cache=cache
        )
        mock_is_cancellation_policy_required.assert_called_once_with(
            order=order, solidarity_contribution=12
        )

    @patch(
        "tapir.bestell_wizard.services.bestell_wizard_order_validator.legal_status_is_cooperative",
        autospec=True,
    )
    @patch.object(BestellWizardOrderValidator, "validate_order", autospec=True)
    @patch.object(
        TapirOrderBuilder,
        "build_tapir_order_from_shopping_cart_serializer",
        autospec=True,
    )
    @patch.object(
        BestellWizardOrderValidator, "is_cancellation_policy_required", autospec=True
    )
    @patch.object(BestellWizardOrderValidator, "is_contract_required", autospec=True)
    @patch.object(
        PersonalDataValidator, "validate_personal_data_new_member", autospec=True
    )
    def test_validateOrderAndUserData_cancellationPolicyNotRequiredAndNotAccepted_noErrorRaised(
        self,
        mock_validate_personal_data_new_member: Mock,
        mock_is_contract_required: Mock,
        mock_is_cancellation_policy_required: Mock,
        mock_build_tapir_order_from_shopping_cart_serializer: Mock,
        mock_validate_order: Mock,
        mock_legal_status_is_cooperative: Mock,
    ):
        pickup_location_ids = Mock()
        contract_start_date = Mock()
        shopping_cart = Mock()
        order = Mock()
        data = {
            "personal_data": {
                "email": "test_mail",
                "phone_number": "test_phone_number",
                "iban": "test_iban",
                "account_owner": "test_account_owner",
            },
            "payment_rhythm": "test_payment_rhythm",
            "sepa_allowed": True,
            "shopping_cart_order": shopping_cart,
            "cancellation_policy_read": False,
            "solidarity_contribution": 12,
            "pickup_location_ids": pickup_location_ids,
        }
        cache = Mock()
        mock_is_contract_required.return_value = False
        mock_is_cancellation_policy_required.return_value = False
        mock_build_tapir_order_from_shopping_cart_serializer.return_value = order
        mock_legal_status_is_cooperative.return_value = False

        BestellWizardOrderValidator.validate_order_and_user_data(
            validated_serializer_data=data,
            contract_start_date=contract_start_date,
            cache=cache,
        )

        mock_validate_personal_data_new_member.assert_called_once_with(
            email="test_mail",
            phone_number="test_phone_number",
            iban="test_iban",
            account_owner="test_account_owner",
            cache=cache,
            check_waiting_list=True,
            payment_rhythm="test_payment_rhythm",
        )
        mock_is_contract_required.assert_called_once_with(cache=cache)
        mock_build_tapir_order_from_shopping_cart_serializer.assert_called_once_with(
            shopping_cart=shopping_cart, cache=cache
        )
        mock_is_cancellation_policy_required.assert_called_once_with(
            order=order, solidarity_contribution=12
        )
        mock_validate_order.assert_called_once_with(
            pickup_location_ids=pickup_location_ids,
            contract_start_date=contract_start_date,
            order=order,
            cache=cache,
        )
        mock_legal_status_is_cooperative.assert_called_once_with(cache=cache)

    @patch.object(
        SolidarityValidator, "is_the_ordered_solidarity_allowed", autospec=True
    )
    @patch.object(BestellWizardOrderValidator, "validate_order", autospec=True)
    @patch.object(
        TapirOrderBuilder,
        "build_tapir_order_from_shopping_cart_serializer",
        autospec=True,
    )
    @patch.object(
        BestellWizardOrderValidator, "is_cancellation_policy_required", autospec=True
    )
    @patch.object(BestellWizardOrderValidator, "is_contract_required", autospec=True)
    @patch.object(
        PersonalDataValidator, "validate_personal_data_new_member", autospec=True
    )
    def test_validateOrderAndUserData_solidarityNotAllowed_raisesValidationError(
        self,
        mock_validate_personal_data_new_member: Mock,
        mock_is_contract_required: Mock,
        mock_is_cancellation_policy_required: Mock,
        mock_build_tapir_order_from_shopping_cart_serializer: Mock,
        mock_validate_order: Mock,
        mock_is_the_ordered_solidarity_allowed: Mock,
    ):
        pickup_location_ids = Mock()
        contract_start_date = Mock()
        shopping_cart = Mock()
        order = Mock()
        data = {
            "personal_data": {
                "email": "test_mail",
                "phone_number": "test_phone_number",
                "iban": "test_iban",
                "account_owner": "test_account_owner",
            },
            "payment_rhythm": "test_payment_rhythm",
            "sepa_allowed": True,
            "shopping_cart_order": shopping_cart,
            "solidarity_contribution": 12,
            "pickup_location_ids": pickup_location_ids,
        }
        cache = Mock()
        mock_is_contract_required.return_value = False
        mock_is_cancellation_policy_required.return_value = False
        mock_build_tapir_order_from_shopping_cart_serializer.return_value = order
        mock_is_the_ordered_solidarity_allowed.return_value = False

        with self.assertRaises(ValidationError) as error:
            BestellWizardOrderValidator.validate_order_and_user_data(
                validated_serializer_data=data,
                contract_start_date=contract_start_date,
                cache=cache,
            )

        self.assertEqual(
            "Solidarbeitrag ungültig oder zu niedrig", error.exception.message
        )

        mock_validate_personal_data_new_member.assert_called_once_with(
            email="test_mail",
            phone_number="test_phone_number",
            iban="test_iban",
            account_owner="test_account_owner",
            cache=cache,
            check_waiting_list=True,
            payment_rhythm="test_payment_rhythm",
        )
        mock_is_contract_required.assert_called_once_with(cache=cache)
        mock_build_tapir_order_from_shopping_cart_serializer.assert_called_once_with(
            shopping_cart=shopping_cart, cache=cache
        )
        mock_is_cancellation_policy_required.assert_called_once_with(
            order=order, solidarity_contribution=12
        )
        mock_validate_order.assert_called_once_with(
            pickup_location_ids=pickup_location_ids,
            contract_start_date=contract_start_date,
            order=order,
            cache=cache,
        )
        mock_is_the_ordered_solidarity_allowed.assert_called_once_with(
            amount=12, start_date=contract_start_date, cache=cache
        )

    @patch.object(BestellWizardOrderValidator, "validate_coop_content", autospec=True)
    @patch(
        "tapir.bestell_wizard.services.bestell_wizard_order_validator.legal_status_is_cooperative",
        autospec=True,
    )
    @patch.object(
        SolidarityValidator, "is_the_ordered_solidarity_allowed", autospec=True
    )
    @patch.object(BestellWizardOrderValidator, "validate_order", autospec=True)
    @patch.object(
        TapirOrderBuilder,
        "build_tapir_order_from_shopping_cart_serializer",
        autospec=True,
    )
    @patch.object(
        BestellWizardOrderValidator, "is_cancellation_policy_required", autospec=True
    )
    @patch.object(BestellWizardOrderValidator, "is_contract_required", autospec=True)
    @patch.object(
        PersonalDataValidator, "validate_personal_data_new_member", autospec=True
    )
    def test_validateOrderAndUserData_statusIsCooperative_validatesCoopContent(
        self,
        mock_validate_personal_data_new_member: Mock,
        mock_is_contract_required: Mock,
        mock_is_cancellation_policy_required: Mock,
        mock_build_tapir_order_from_shopping_cart_serializer: Mock,
        mock_validate_order: Mock,
        mock_is_the_ordered_solidarity_allowed: Mock,
        mock_legal_status_is_cooperative: Mock,
        mock_validate_coop_content: Mock,
    ):
        pickup_location_ids = Mock()
        contract_start_date = Mock()
        shopping_cart = Mock()
        order = Mock()
        data = {
            "personal_data": {
                "email": "test_mail",
                "phone_number": "test_phone_number",
                "iban": "test_iban",
                "account_owner": "test_account_owner",
            },
            "payment_rhythm": "test_payment_rhythm",
            "sepa_allowed": True,
            "shopping_cart_order": shopping_cart,
            "solidarity_contribution": 12,
            "pickup_location_ids": pickup_location_ids,
        }
        cache = Mock()
        mock_is_contract_required.return_value = False
        mock_is_cancellation_policy_required.return_value = False
        mock_build_tapir_order_from_shopping_cart_serializer.return_value = order
        mock_is_the_ordered_solidarity_allowed.return_value = True
        mock_legal_status_is_cooperative.return_value = True

        BestellWizardOrderValidator.validate_order_and_user_data(
            validated_serializer_data=data,
            contract_start_date=contract_start_date,
            cache=cache,
        )

        mock_validate_personal_data_new_member.assert_called_once_with(
            email="test_mail",
            phone_number="test_phone_number",
            iban="test_iban",
            account_owner="test_account_owner",
            cache=cache,
            check_waiting_list=True,
            payment_rhythm="test_payment_rhythm",
        )
        mock_is_contract_required.assert_called_once_with(cache=cache)
        mock_build_tapir_order_from_shopping_cart_serializer.assert_called_once_with(
            shopping_cart=shopping_cart, cache=cache
        )
        mock_is_cancellation_policy_required.assert_called_once_with(
            order=order, solidarity_contribution=12
        )
        mock_validate_order.assert_called_once_with(
            pickup_location_ids=pickup_location_ids,
            contract_start_date=contract_start_date,
            order=order,
            cache=cache,
        )
        mock_is_the_ordered_solidarity_allowed.assert_called_once_with(
            amount=12, start_date=contract_start_date, cache=cache
        )
        mock_legal_status_is_cooperative.assert_called_once_with(cache=cache)
        mock_validate_coop_content.assert_called_once_with(
            validated_data=data, order=order, cache=cache
        )

    @patch.object(BestellWizardOrderValidator, "validate_coop_content", autospec=True)
    @patch(
        "tapir.bestell_wizard.services.bestell_wizard_order_validator.legal_status_is_cooperative",
        autospec=True,
    )
    @patch.object(
        SolidarityValidator, "is_the_ordered_solidarity_allowed", autospec=True
    )
    @patch.object(BestellWizardOrderValidator, "validate_order", autospec=True)
    @patch.object(
        TapirOrderBuilder,
        "build_tapir_order_from_shopping_cart_serializer",
        autospec=True,
    )
    @patch.object(
        BestellWizardOrderValidator, "is_cancellation_policy_required", autospec=True
    )
    @patch.object(BestellWizardOrderValidator, "is_contract_required", autospec=True)
    @patch.object(
        PersonalDataValidator, "validate_personal_data_new_member", autospec=True
    )
    def test_validateOrderAndUserData_statusIsNotCooperative_DoesntValidateCoopContent(
        self,
        mock_validate_personal_data_new_member: Mock,
        mock_is_contract_required: Mock,
        mock_is_cancellation_policy_required: Mock,
        mock_build_tapir_order_from_shopping_cart_serializer: Mock,
        mock_validate_order: Mock,
        mock_is_the_ordered_solidarity_allowed: Mock,
        mock_legal_status_is_cooperative: Mock,
        mock_validate_coop_content: Mock,
    ):
        pickup_location_ids = Mock()
        contract_start_date = Mock()
        shopping_cart = Mock()
        order = Mock()
        data = {
            "personal_data": {
                "email": "test_mail",
                "phone_number": "test_phone_number",
                "iban": "test_iban",
                "account_owner": "test_account_owner",
            },
            "payment_rhythm": "test_payment_rhythm",
            "sepa_allowed": True,
            "shopping_cart_order": shopping_cart,
            "solidarity_contribution": 12,
            "pickup_location_ids": pickup_location_ids,
        }
        cache = Mock()
        mock_is_contract_required.return_value = False
        mock_is_cancellation_policy_required.return_value = False
        mock_build_tapir_order_from_shopping_cart_serializer.return_value = order
        mock_is_the_ordered_solidarity_allowed.return_value = True
        mock_legal_status_is_cooperative.return_value = False

        BestellWizardOrderValidator.validate_order_and_user_data(
            validated_serializer_data=data,
            contract_start_date=contract_start_date,
            cache=cache,
        )

        mock_validate_personal_data_new_member.assert_called_once_with(
            email="test_mail",
            phone_number="test_phone_number",
            iban="test_iban",
            account_owner="test_account_owner",
            cache=cache,
            check_waiting_list=True,
            payment_rhythm="test_payment_rhythm",
        )
        mock_is_contract_required.assert_called_once_with(cache=cache)
        mock_build_tapir_order_from_shopping_cart_serializer.assert_called_once_with(
            shopping_cart=shopping_cart, cache=cache
        )
        mock_is_cancellation_policy_required.assert_called_once_with(
            order=order, solidarity_contribution=12
        )
        mock_validate_order.assert_called_once_with(
            pickup_location_ids=pickup_location_ids,
            contract_start_date=contract_start_date,
            order=order,
            cache=cache,
        )
        mock_is_the_ordered_solidarity_allowed.assert_called_once_with(
            amount=12, start_date=contract_start_date, cache=cache
        )
        mock_legal_status_is_cooperative.assert_called_once_with(cache=cache)
        mock_validate_coop_content.assert_not_called()
