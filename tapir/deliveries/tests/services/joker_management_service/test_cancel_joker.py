from unittest.mock import Mock

from django.test import SimpleTestCase

from tapir.deliveries.services.joker_management_service import JokerManagementService


class TestJokerManagementServiceCancelJoker(SimpleTestCase):
    def test_cancelJoker_default_callsDelete(self):
        joker = Mock()

        JokerManagementService.cancel_joker(joker)

        joker.delete.assert_called_once_with()
