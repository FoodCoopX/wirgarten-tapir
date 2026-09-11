import uuid
from unittest.mock import patch, Mock

from django.http import Http404
from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.waiting_list.services.waiting_list_entry_confirmation_validator import (
    WaitingListEntryConfirmationValidator,
)
from tapir.wirgarten.models import WaitingListEntry


class TestGetEntryByIdAndValidateLinkKey(TapirUnitTest):
    @patch(
        "tapir.waiting_list.services.waiting_list_entry_confirmation_validator.get_object_or_404",
        autospec=True,
    )
    def test_getEntryByIdAndValidateLinkKey_default_returnsEntry(
        self, mock_get_object_or_404: Mock
    ):
        link_key = uuid.uuid4()
        waiting_list_entry = WaitingListEntry(
            id="test_id", confirmation_link_key=link_key
        )
        mock_get_object_or_404.return_value = waiting_list_entry

        result = (
            WaitingListEntryConfirmationValidator.get_entry_by_id_and_validate_link_key(
                entry_id="test_id", link_key=str(link_key)
            )
        )

        self.assertEqual(waiting_list_entry, result)

    @patch(
        "tapir.waiting_list.services.waiting_list_entry_confirmation_validator.get_object_or_404",
        autospec=True,
    )
    def test_getEntryByIdAndValidateLinkKey_uuidIsInvalid_raises404Error(
        self, mock_get_object_or_404: Mock
    ):
        link_key = uuid.uuid4()
        waiting_list_entry = WaitingListEntry(
            id="test_id", confirmation_link_key=link_key
        )
        mock_get_object_or_404.return_value = waiting_list_entry

        with self.assertRaises(Http404) as error:
            WaitingListEntryConfirmationValidator.get_entry_by_id_and_validate_link_key(
                entry_id="test_id", link_key="invalid_key"
            )

        self.assertEqual(
            "Unknown entry (id:test_id, key:invalid_key)", error.exception.args[0]
        )

    @patch(
        "tapir.waiting_list.services.waiting_list_entry_confirmation_validator.get_object_or_404",
        autospec=True,
    )
    def test_getEntryByIdAndValidateLinkKey_keyDoesntFit_raises404Error(
        self, mock_get_object_or_404: Mock
    ):
        valid_link_key = uuid.uuid4()
        invalid_link_key = uuid.uuid4()
        waiting_list_entry = WaitingListEntry(
            id="test_id", confirmation_link_key=valid_link_key
        )
        mock_get_object_or_404.return_value = waiting_list_entry

        with self.assertRaises(Http404) as error:
            WaitingListEntryConfirmationValidator.get_entry_by_id_and_validate_link_key(
                entry_id="test_id", link_key=str(invalid_link_key)
            )

        self.assertEqual(
            f"Unknown entry (id:test_id, key:{invalid_link_key})",
            error.exception.args[0],
        )
