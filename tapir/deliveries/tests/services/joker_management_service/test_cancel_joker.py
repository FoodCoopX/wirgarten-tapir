from unittest.mock import Mock

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.deliveries.services.joker_management_service import JokerManagementService


class TestJokerManagementServiceCancelJoker(TapirUnitTest):
    def test_cancelJoker_default_callsDelete(self):
        joker = Mock()

        JokerManagementService.cancel_joker(joker)

        joker.delete.assert_called_once_with()
