from tapir.coop.services.member_search_service import MemberSearchService
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestFilterQueryset(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.cache = {}
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_PREFIX, "")
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ZERO_PAD_LENGTH, 0)
        self.target_member = MemberFactory.create(
            first_name="Max",
            last_name="Mustermann",
            email="max.mustermann@example.com",
            member_no=17,
        )
        self.other_member = MemberFactory.create(
            first_name="Anna",
            last_name="Schmidt",
            email="anna@example.com",
            member_no=1234,
        )

    def filter_members(self, search_value: str):
        return MemberSearchService.filter_queryset(
            Member.objects.all(), search_value=search_value, cache=self.cache
        )

    def test_filterQueryset_firstNameOnly_returnsMatchingMember(self):
        result = self.filter_members("Max")

        self.assertEqual(
            [self.target_member.id],
            list(result.values_list("id", flat=True)),
        )

    def test_filterQueryset_firstAndLastName_returnsMatchingMember(self):
        result = self.filter_members("Max Mustermann")

        self.assertEqual(
            [self.target_member.id],
            list(result.values_list("id", flat=True)),
        )

    def test_filterQueryset_emailSubstring_returnsMatchingMember(self):
        result = self.filter_members("mustermann@example")

        self.assertEqual(
            [self.target_member.id],
            list(result.values_list("id", flat=True)),
        )

    def test_filterQueryset_memberNumberDigits_returnsMatchingMember(self):
        result = self.filter_members("17")

        self.assertEqual(
            [self.target_member.id],
            list(result.values_list("id", flat=True)),
        )

    def test_filterQueryset_memberNumberPartialSubstring_returnsMatchingMember(self):
        result = self.filter_members("12")

        self.assertEqual(
            [self.other_member.id],
            list(result.values_list("id", flat=True)),
        )

    def test_filterQueryset_memberNumberWithPrefix_returnsMatchingMember(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_PREFIX, "BT")
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ZERO_PAD_LENGTH, 4)

        result = self.filter_members("BT0017")

        self.assertEqual(
            [self.target_member.id],
            list(result.values_list("id", flat=True)),
        )

    def test_filterQueryset_paddedMemberNumberSubstring_returnsMatchingMember(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_PREFIX, "BT")
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ZERO_PAD_LENGTH, 4)
        member = MemberFactory.create(
            first_name="Padded",
            last_name="Number",
            email="padded.number@example.com",
            member_no=118,
        )

        result = self.filter_members("011")

        self.assertEqual(
            [member.id],
            list(result.values_list("id", flat=True)),
        )

    def test_filterQueryset_prefixWithoutPadding_returnsMatchingMember(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_PREFIX, "BT")
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ZERO_PAD_LENGTH, 0)
        member = MemberFactory.create(
            first_name="Prefix",
            last_name="NoPad",
            email="prefix.nopad@example.com",
            member_no=118,
        )

        result = self.filter_members("BT118")

        self.assertEqual(
            [member.id],
            list(result.values_list("id", flat=True)),
        )

    def test_filterQueryset_memberNumberLongerThanPadLength_returnsMatchingMember(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_PREFIX, "")
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ZERO_PAD_LENGTH, 4)
        member = MemberFactory.create(
            first_name="Long",
            last_name="Number",
            email="long.number@example.com",
            member_no=12345,
        )

        result = self.filter_members("12345")

        self.assertEqual(
            [member.id],
            list(result.values_list("id", flat=True)),
        )

    def test_filterQueryset_formattedLongMemberNumberWithPrefix_returnsMatchingMember(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_PREFIX, "BT")
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ZERO_PAD_LENGTH, 3)
        member = MemberFactory.create(
            first_name="Théo",
            last_name="Test",
            email="theo.test@example.com",
            member_no=123456,
        )

        result = self.filter_members("BT123456")

        self.assertEqual(
            [member.id],
            list(result.values_list("id", flat=True)),
        )

    def test_filterQueryset_noMatch_returnsEmptyQueryset(self):
        result = self.filter_members("Nonexistent Name")

        self.assertEqual([], list(result.values_list("id", flat=True)))

    def test_filterQueryset_partialTokenMatchOnly_returnsEmptyQueryset(self):
        result = self.filter_members("Max Schmidt")

        self.assertEqual([], list(result.values_list("id", flat=True)))

    def test_filterQueryset_emptySearchValue_returnsUnfilteredQueryset(self):
        result = self.filter_members("   ")

        self.assertEqual(2, result.count())
