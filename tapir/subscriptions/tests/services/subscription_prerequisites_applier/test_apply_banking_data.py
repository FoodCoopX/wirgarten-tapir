import datetime
from unittest.mock import patch, MagicMock

from tapir.subscriptions.services.subscription_prerequisites_applier import (
    SubscriptionPrerequisitesApplier,
)
from tapir.wirgarten.models import Member
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest, mock_timezone


@patch.object(Member, "save", autospec=True)
class TestSubscriptionPrerequisitesApplierApplyBankingData(TapirUnitTest):
    def setUp(self):
        super().setUp()
        self.now = mock_timezone(
            test=self, now=datetime.datetime(year=2027, month=12, day=20)
        )

    def test_applyBankingData_dataGiven_setsDataAndSavesMember(
        self, mock_save: MagicMock
    ):
        member = MemberFactory.build(iban="", account_owner="", sepa_consent=None)

        SubscriptionPrerequisitesApplier.apply_banking_data(
            member=member,
            iban="test_iban",
            account_owner="test_account_owner",
            sepa_allowed=True,
            cache={},
        )

        self.assertEqual("test_iban", member.iban)
        self.assertEqual("test_account_owner", member.account_owner)
        self.assertEqual(self.now, member.sepa_consent)
        mock_save.assert_called_once_with(member)

    def test_applyBankingData_dataNotGiven_keepsExistingDataAndSavesMember(
        self, mock_save: MagicMock
    ):
        member = MemberFactory.build(
            iban="original_iban",
            account_owner="original_account_owner",
            sepa_consent=None,
        )

        SubscriptionPrerequisitesApplier.apply_banking_data(
            member=member,
            iban=" ",
            account_owner="",
            sepa_allowed=False,
            cache={},
        )

        self.assertEqual("original_iban", member.iban)
        self.assertEqual("original_account_owner", member.account_owner)
        self.assertIsNone(member.sepa_consent)
        mock_save.assert_called_once_with(member)
