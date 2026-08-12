import datetime

from tapir.accounts.models import UpdateTapirUserLogEntry
from tapir.coop.services.member_number_service import MemberNumberService
from tapir.core.config import LEGAL_STATUS_COOPERATIVE
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, CoopShareTransactionFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestAssignMemberNumberIfEligible(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_assignMemberNumberIfEligible_eligible_assignsNumberSavesAndReturnsTrue(
        self,
    ):
        member = MemberFactory.create()
        member.member_no = None
        member.save()

        self._set_parameter(
            key=ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, value=False
        )

        result = MemberNumberService.assign_member_number_if_eligible(
            member, cache={}, actor=None
        )

        self.assertTrue(result)
        member.refresh_from_db()
        self.assertIsNotNone(member.member_no)
        self.assertTrue(UpdateTapirUserLogEntry.objects.exists())

    def test_assignMemberNumberIfEligible_notEligible_doesNothingAndReturnsFalse(self):
        self._set_parameter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS, value=LEGAL_STATUS_COOPERATIVE
        )
        member = MemberFactory.create()
        member.member_no = None
        member.save()

        mock_timezone(test=self, now=datetime.datetime(year=2020, month=1, day=1))
        CoopShareTransactionFactory.create(
            member=member, valid_at=datetime.date(year=2021, month=1, day=1)
        )

        result = MemberNumberService.assign_member_number_if_eligible(
            member, cache={}, actor=None
        )

        self.assertFalse(result)
        member.refresh_from_db()
        self.assertIsNone(member.member_no)
        self.assertFalse(UpdateTapirUserLogEntry.objects.exists())
