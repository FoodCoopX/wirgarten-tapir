from tapir.accounts.services.unverified_members_service import (
    UnverifiedMembersService,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestEstimateSendingDurationSeconds(TapirUnitTest):
    def test_estimateSendingDurationSeconds_default_returnsCountTimesPause(self):
        self.assertEqual(
            10 * UnverifiedMembersService.SECONDS_BETWEEN_MAILS,
            UnverifiedMembersService.estimate_sending_duration_seconds(member_count=10),
        )
