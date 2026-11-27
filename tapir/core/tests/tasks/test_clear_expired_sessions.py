from unittest.mock import MagicMock, patch

from tapir.core.tasks import clear_expired_sessions
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestClearExpiredSessions(TapirUnitTest):
    @patch("tapir.core.tasks.call_command", autospec=True)
    def test_clearExpiredSessions_default_runsTheClearSessionsCommand(
        self, mock_call_command: MagicMock
    ):
        clear_expired_sessions()

        mock_call_command.assert_called_once_with("clearsessions")
