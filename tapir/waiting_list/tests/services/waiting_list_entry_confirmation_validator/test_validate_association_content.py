from unittest.mock import patch, Mock

from django.core.exceptions import ValidationError

from tapir.associations.models import AssociationMembershipType
from tapir.waiting_list.services.waiting_list_entry_confirmation_validator import (
    WaitingListEntryConfirmationValidator,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestValidateAssociationContent(TapirUnitTest):
    def test_validateAssociationContent_membershipTypeIdIsNone_raisesError(self):
        with self.assertRaises(ValidationError) as error_context:
            WaitingListEntryConfirmationValidator.validate_association_content(
                association_membership_type_id=None
            )

        self.assertEqual(
            "Keine Vereinsmitgliedschaft ausgewählt", error_context.exception.message
        )

    @patch.object(AssociationMembershipType, "objects", autospec=False)
    def test_validateAssociationContent_membershipTypeDoesntExist_raisesError(
        self, mock_objects: Mock
    ):
        mock_objects.filter.return_value.first.return_value = None

        with self.assertRaises(ValidationError) as error_context:
            WaitingListEntryConfirmationValidator.validate_association_content(
                association_membership_type_id="invalid_id"
            )

        self.assertEqual(
            "Unbekannte Vereinsmitgliedschafttyp-ID: invalid_id",
            error_context.exception.message,
        )

        mock_objects.filter.assert_called_once_with(id="invalid_id")
        mock_objects.filter.return_value.first.assert_called_once_with()

    @patch.object(AssociationMembershipType, "objects", autospec=False)
    def test_validateAssociationContent_membershipTypeExists_doesNothing(
        self, mock_objects: Mock
    ):
        mock_objects.filter.return_value.first.return_value = Mock()

        WaitingListEntryConfirmationValidator.validate_association_content(
            association_membership_type_id="invalid_id"
        )

        mock_objects.filter.assert_called_once_with(id="invalid_id")
        mock_objects.filter.return_value.first.assert_called_once_with()
