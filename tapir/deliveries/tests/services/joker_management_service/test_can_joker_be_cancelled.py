import datetime
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.wirgarten.tests import factories
from tapir.wirgarten.tests.test_utils import mock_timezone


class TestJokerManagementServiceCanJokerBeCancelled(SimpleTestCase):
    def setUp(self):
        mock_timezone(self, factories.NOW)

    @patch.object(JokerManagementService, "get_date_limit_for_joker_changes")
    def test_canJokerBeCancelled_dateLimitIsInTheFuture_returnsTrue(
        self, mock_get_date_limit_for_joker_changes: Mock
    ):
        joker = Mock()
        joker.date = Mock()
        mock_get_date_limit_for_joker_changes.return_value = factories.TODAY

        cache = {}
        self.assertTrue(
            JokerManagementService.can_joker_be_cancelled(joker, cache=cache)
        )
        mock_get_date_limit_for_joker_changes.assert_called_once_with(
            joker.date, cache=cache
        )

    @patch.object(JokerManagementService, "get_date_limit_for_joker_changes")
    def test_canJokerBeCancelled_dateLimitIsNotInTheFuture_returnsFalse(
        self, mock_get_date_limit_for_joker_changes: Mock
    ):
        joker = Mock()
        joker.date = Mock()
        mock_get_date_limit_for_joker_changes.return_value = (
            factories.TODAY - datetime.timedelta(days=1)
        )

        cache = {}
        self.assertFalse(
            JokerManagementService.can_joker_be_cancelled(joker, cache=cache)
        )
        mock_get_date_limit_for_joker_changes.assert_called_once_with(
            joker.date, cache=cache
        )
