from tapir.coop.services.member_search_service import MemberSearchService
from tapir.utils.tests_utils import mock_parameter_value
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
        mock_parameter_value(
            cache=self.cache,
            key=ParameterKeys.MEMBER_NUMBER_PREFIX,
            value="",
        )
        mock_parameter_value(
            cache=self.cache,
            key=ParameterKeys.MEMBER_NUMBER_ZERO_PAD_LENGTH,
            value=0,
        )
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
        mock_parameter_value(
            cache=self.cache,
            key=ParameterKeys.MEMBER_NUMBER_PREFIX,
            value="BT",
        )
        mock_parameter_value(
            cache=self.cache,
            key=ParameterKeys.MEMBER_NUMBER_ZERO_PAD_LENGTH,
            value=4,
        )

        result = self.filter_members("BT0017")

        self.assertEqual(
            [self.target_member.id],
            list(result.values_list("id", flat=True)),
        )

    def test_filterQueryset_paddedMemberNumberSubstring_returnsMatchingMember(self):
        mock_parameter_value(
            cache=self.cache,
            key=ParameterKeys.MEMBER_NUMBER_PREFIX,
            value="BT",
        )
        mock_parameter_value(
            cache=self.cache,
            key=ParameterKeys.MEMBER_NUMBER_ZERO_PAD_LENGTH,
            value=4,
        )
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

    def test_filterQueryset_noMatch_returnsEmptyQueryset(self):
        result = self.filter_members("Nonexistent Name")

        self.assertEqual([], list(result.values_list("id", flat=True)))

    def test_filterQueryset_partialTokenMatchOnly_returnsEmptyQueryset(self):
        result = self.filter_members("Max Schmidt")

        self.assertEqual([], list(result.values_list("id", flat=True)))

    def test_filterQueryset_emptySearchValue_returnsUnfilteredQueryset(self):
        result = self.filter_members("   ")

        self.assertEqual(2, result.count())
