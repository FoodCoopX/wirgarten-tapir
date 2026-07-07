from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError

from tapir.associations.models import AssociationMembershipType
from tapir.bestell_wizard.services.bestell_wizard_order_validator import (
    BestellWizardOrderValidator,
)
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.factories import ProductFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestValidateAssociationContent(TapirUnitTest):
    def test_validateAssociationContent_noTypeSelected_raisesValidationError(self):
        with self.assertRaises(ValidationError) as error:
            BestellWizardOrderValidator.validate_association_content(
                {}, order=Mock(), cache=Mock()
            )

        self.assertEqual(
            "Keine Vereinsmitgliedschaft ausgewählt", error.exception.message
        )

    @patch.object(AssociationMembershipType, "objects")
    def test_validateAssociationContent_typeDoesntExist_raisesValidationError(
        self, mock_type_objects: Mock
    ):
        mock_type_objects.filter.return_value.first.return_value = None

        with self.assertRaises(ValidationError) as error:
            BestellWizardOrderValidator.validate_association_content(
                {"association_membership_type_id": "test_membership_type_id"},
                order=Mock(),
                cache=Mock(),
            )

        self.assertEqual(
            "Unbekannte Vereinsmitgliedschafttyp-ID: test_membership_type_id",
            error.exception.message,
        )
        mock_type_objects.filter.assert_called_once_with(id="test_membership_type_id")

    @patch.object(AssociationMembershipType, "objects")
    def test_validateAssociationContent_orderIsEmptyButSupportingMembershipNotEnabled_raisesValidationError(
        self, mock_type_objects: Mock
    ):
        mock_type_objects.filter.return_value.first.return_value = Mock()
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.ASSOCIATIONS_ALLOW_SUPPORTING_MEMBERSHIP,
            value=False,
        )

        with self.assertRaises(ValidationError) as error:
            BestellWizardOrderValidator.validate_association_content(
                {"association_membership_type_id": "test_membership_type_id"},
                order={},
                cache=cache,
            )

        self.assertEqual(
            "Fördermitgliedschaften sind nicht erlaubt, es muss mindestens 1 Product ausgewählt werden",
            error.exception.message,
        )
        mock_type_objects.filter.assert_called_once_with(id="test_membership_type_id")

    @patch.object(AssociationMembershipType, "objects")
    def test_validateAssociationContent_orderIsEmptyAndSupportingMembershipEnabled_doNothing(
        self, mock_type_objects: Mock
    ):
        mock_type_objects.filter.return_value.first.return_value = Mock()
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.ASSOCIATIONS_ALLOW_SUPPORTING_MEMBERSHIP,
            value=True,
        )

        BestellWizardOrderValidator.validate_association_content(
            {"association_membership_type_id": "test_membership_type_id"},
            order={},
            cache=cache,
        )

        mock_type_objects.filter.assert_called_once_with(id="test_membership_type_id")

    @patch.object(AssociationMembershipType, "objects")
    def test_validateAssociationContent_orderIsNotEmptyAndSupportingMembershipNotEnabled_doNothing(
        self, mock_type_objects: Mock
    ):
        mock_type_objects.filter.return_value.first.return_value = Mock()
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.ASSOCIATIONS_ALLOW_SUPPORTING_MEMBERSHIP,
            value=False,
        )

        BestellWizardOrderValidator.validate_association_content(
            {"association_membership_type_id": "test_membership_type_id"},
            order={ProductFactory.build(): 2},
            cache=cache,
        )

        mock_type_objects.filter.assert_called_once_with(id="test_membership_type_id")
