from tapir.coop.services.member_number_service import MemberNumberService
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestComputeNextMemberNumber(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_computeNextMemberNumber_noExistingMembers_returnsStartValue(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_START_VALUE, 1000)
        self.assertFalse(Member.objects.exists())

        self.assertEqual(
            1000, MemberNumberService.compute_next_member_number(cache={})
        )

    def test_computeNextMemberNumber_existingMemberBelowStartValue_returnsStartValue(
        self,
    ):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_START_VALUE, 1000)
        MemberFactory.create(member_no=500)

        self.assertEqual(
            1000, MemberNumberService.compute_next_member_number(cache={})
        )

    def test_computeNextMemberNumber_existingMemberAboveStartValue_returnsMaxPlusOne(
        self,
    ):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_START_VALUE, 1)
        MemberFactory.create(member_no=42)

        self.assertEqual(
            43, MemberNumberService.compute_next_member_number(cache={})
        )
