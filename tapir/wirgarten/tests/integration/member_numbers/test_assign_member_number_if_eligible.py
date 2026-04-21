from tapir.coop.services.member_number_service import MemberNumberService
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestAssignMemberNumberIfEligible(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    @staticmethod
    def _create_member_without_number() -> Member:
        member = MemberFactory.create()
        member.member_no = None
        member.save()
        return member

    def test_assignMemberNumberIfEligible_eligible_assignsNumberAndReturnsTrue(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, False)
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_START_VALUE, 1)
        member = self._create_member_without_number()

        result = MemberNumberService.assign_member_number_if_eligible(member, cache={})

        self.assertTrue(result)
        self.assertIsNotNone(member.member_no)
        member.refresh_from_db()
        self.assertEqual(1, member.member_no)

    def test_assignMemberNumberIfEligible_notEligible_doesNothingAndReturnsFalse(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, False)
        member = MemberFactory.create(member_no=5)

        result = MemberNumberService.assign_member_number_if_eligible(member, cache={})

        self.assertFalse(result)
        member.refresh_from_db()
        self.assertEqual(5, member.member_no)

    def test_assignMemberNumberIfEligible_respectsStartValue_usesStartValueAsLowerBound(
        self,
    ):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, False)
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_START_VALUE, 500)
        member = self._create_member_without_number()

        result = MemberNumberService.assign_member_number_if_eligible(member, cache={})

        self.assertTrue(result)
        member.refresh_from_db()
        self.assertEqual(500, member.member_no)
