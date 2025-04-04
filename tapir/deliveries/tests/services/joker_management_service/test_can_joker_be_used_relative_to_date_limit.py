import datetime
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.wirgarten.tests import factories
from tapir.wirgarten.tests.test_utils import mock_timezone


class TestJokerManagementServiceCanJokerBeUsedRelativeToDateLimit(SimpleTestCase):
    def setUp(self):
        mock_timezone(self, factories.NOW)

    @patch.object(JokerManagementService, "get_date_limit_for_joker_changes")
    def test_canJokerBeUsedRelativeToDateLimit_dateLimitIsInTheFuture_returnsTrue(
        self, mock_get_date_limit_for_joker_changes: Mock
    ):
        reference_date = Mock()
        mock_get_date_limit_for_joker_changes.return_value = (
            factories.TODAY + datetime.timedelta(days=1)
        )

        self.assertTrue(
            JokerManagementService.can_joker_be_used_relative_to_date_limit(
                reference_date
            )
        )
        mock_get_date_limit_for_joker_changes.assert_called_once_with(reference_date)

    @patch.object(JokerManagementService, "get_date_limit_for_joker_changes")
    def test_canJokerBeUsedRelativeToDateLimit_dateLimitIsNotInTheFuture_returnsFalse(
        self, mock_get_date_limit_for_joker_changes: Mock
    ):
        reference_date = Mock()
        mock_get_date_limit_for_joker_changes.return_value = factories.TODAY

        self.assertFalse(
            JokerManagementService.can_joker_be_used_relative_to_date_limit(
                reference_date
            )
        )
        mock_get_date_limit_for_joker_changes.assert_called_once_with(reference_date)
