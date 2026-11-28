from unittest.mock import MagicMock, patch

from django.core import signing
from django.utils import timezone

from tapir.core.services.subscription_management_link_provider import (
    SubscriptionManagementLinkProvider,
)

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.mail.models import (
    StaticSegment,
    StaticSegmentRecipient,
    MailCategory,
    MailCategoryMode,
    InternalRecipientCategoryRegistration,
)
from tapir.mail.addressed_recipient import AddressedRecipient
from tapir.mail.services.segment import resolve_segments
from tapir.mail.tests.factories import (
    StaticSegmentRecipientFactory,
    MailSegmentFactory,
    MailCategoryFactory,
)
from tapir.mail.tests.test_utils import add_mail_segment_provider
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.mail.triggers.transactional_trigger import TransactionalTriggerData
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.factories import MemberFactory, MemberExtraEmailFactory


class TestSegments(TapirIntegrationTest):
    SEGMENT_ALL_USERS = "Test: all users"
    SEGMENT_COOP_MEMBERS = "Test: coop members"
    SEGMENT_NOT_COOP_MEMBERS = "Test: not coop members"

    STATIC_RECIPIENT_1 = "static1@example.com"
    STATIC_RECIPIENT_2 = "static2@example.com"

    COOP_MEMBER_IDS = ["1", "3"]

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        for member_id in ["1", "2", "3", "4"]:
            MemberFactory.create(id=member_id, email=f"mail{member_id}@test.net")

        # Create a static segment
        cls.static_segment = StaticSegment.objects.create(name="Static1")
        StaticSegmentRecipient.objects.create(
            segment=cls.static_segment, email=cls.STATIC_RECIPIENT_1
        )
        StaticSegmentRecipient.objects.create(
            segment=cls.static_segment, email=cls.STATIC_RECIPIENT_2
        )

    def setUp(self) -> None:
        def coop_members():
            return Member.objects.filter(id__in=self.COOP_MEMBER_IDS)

        def not_coop_members():
            return Member.objects.exclude(id__in=self.COOP_MEMBER_IDS)

        add_mail_segment_provider(
            self,
            lambda: {
                self.SEGMENT_ALL_USERS: MailSegmentFactory.build(
                    get_queryset=Member.objects.all
                ),
                self.SEGMENT_COOP_MEMBERS: MailSegmentFactory.build(
                    get_queryset=coop_members
                ),
                self.SEGMENT_NOT_COOP_MEMBERS: MailSegmentFactory.build(
                    get_queryset=not_coop_members
                ),
            },
        )

    def test_combineSegmentsWithFilters_addSegments_returnsCorrectList(self):
        result = resolve_segments(
            cache={}, dynamic_segment_names_additive=[self.SEGMENT_ALL_USERS]
        )
        self.assertSetEqual({r.recipient.id for r in result}, {"1", "2", "3", "4"})

    def test_combineSegmentsWithFilters_addAndRemoveSegments_returnsCorrectList(self):
        result = resolve_segments(
            cache={},
            dynamic_segment_names_additive=[self.SEGMENT_ALL_USERS],
            dynamic_segment_names_subtractive=[self.SEGMENT_NOT_COOP_MEMBERS],
        )
        self.assertSetEqual({r.recipient.id for r in result}, {"1", "3"})

    def test_combineSegmentsWithFilters_addDynamicAndStaticSegments_returnsCorrectList(
        self,
    ):
        result = resolve_segments(
            cache={},
            dynamic_segment_names_additive=[self.SEGMENT_NOT_COOP_MEMBERS],
            static_segment_ids_additive=[self.static_segment.id],
        )
        self.assertSetEqual(
            {
                (
                    r.email
                    if isinstance(r.recipient, StaticSegmentRecipient)
                    else r.recipient.id
                )
                for r in result
            },
            {"2", "4", self.STATIC_RECIPIENT_1, self.STATIC_RECIPIENT_2},
        )

    def test_combineSegmentsWithFilters_addStaticSegment_returnsCorrectList(self):
        result = resolve_segments(
            cache={}, static_segment_ids_additive=[self.static_segment.id]
        )
        self.assertSetEqual(
            {r.email for r in result},
            {self.STATIC_RECIPIENT_1, self.STATIC_RECIPIENT_2},
        )

    def test_resolveSegments_includesSubtractiveStaticSegment_recipientFromSubtractiveSegmentNotInList(
        self,
    ):
        subtractive_static_segment = StaticSegment.objects.create(name="subtractive")
        StaticSegmentRecipient.objects.create(
            segment=subtractive_static_segment,
            email=Member.objects.get(id="1").email,
        )

        result = resolve_segments(
            cache={},
            dynamic_segment_names_additive=[self.SEGMENT_COOP_MEMBERS],
            static_segment_ids_subtractive=[subtractive_static_segment.id],
        )
        self.assertSetEqual(
            {r.email for r in result},
            {Member.objects.get(id="3").email},
        )

    def test_resolveSegments_overrideRecipientByBaseQuerysetId_resultsContainOnlyRecipientWithEmailFromOverride(
        self,
    ):
        result = resolve_segments(
            cache={},
            dynamic_segment_names_additive=[self.SEGMENT_ALL_USERS],
            override_recipients=[
                {"recipient_id_in_base_queryset": "2"},
                {"recipient_id_in_base_queryset": "4"},
            ],
        )
        self.assertSetEqual({r.recipient.id for r in result}, {"2", "4"})

    def test_resolveSegments_recipientsOutsideTheBaseQueryset_resultContainsFirstGivenRecipient(
        self,
    ):
        result = resolve_segments(
            cache={},
            dynamic_segment_names_additive=[self.SEGMENT_ALL_USERS],
            override_recipients=[
                {
                    "recipient_outside_of_base_queryset": {
                        "email": "test@email.com",
                        "first_name": "Max",
                        "last_name": "Mustermann",
                    }
                }
            ],
        )
        self.assertEqual(1, len(result))
        self.assertEqual(
            AddressedRecipient.at_own_address(
                TransactionalTriggerData.RecipientOutsideOfBaseQueryset(
                    email="test@email.com",
                    first_name="Max",
                    last_name="Mustermann",
                )
            ),
            result[0],
        )

    def test_resolveSegments_mailCategory_returnsCorrectList(self):
        static_segment = StaticSegment.objects.create(
            name="Mail-Kategorie:test_category"
        )
        static_recipient = StaticSegmentRecipientFactory.create(segment=static_segment)

        mail_category = MailCategory.objects.create(
            name="test_category",
            static_segment=static_segment,
            mode=MailCategoryMode.ALWAYS_ON,
            dynamic_segment_name=self.SEGMENT_COOP_MEMBERS,
            available_for_external_recipients=True,
        )

        result = resolve_segments(
            cache={}, mail_category_ids_additive=[mail_category.id]
        )
        self.assertEqual(3, len(result))
        self.assertIn(AddressedRecipient.at_own_address(static_recipient), result)
        for user in Member.objects.filter(id__in=self.COOP_MEMBER_IDS):
            self.assertIn(AddressedRecipient.at_own_address(user), result)

    @patch.object(signing.time, "time", autospec=True, return_value=1_000_000)
    def test_resolveSegments_memberInDynamicSegmentHasConfirmedExtra_resultContainsMainAddressAndCopy(
        self, _: MagicMock
    ):
        member = self._create_confirmed_extra(member_id="1")

        result = resolve_segments(
            cache={}, dynamic_segment_names_additive=[self.SEGMENT_COOP_MEMBERS]
        )

        self.assertEqual(
            [
                AddressedRecipient.at_own_address(member),
                self._build_copy(member=member),
                AddressedRecipient.at_own_address(Member.objects.get(id="3")),
            ],
            sorted(result, key=lambda addressed: addressed.recipient.id),
        )

    def test_resolveSegments_extraAddressesDisabled_resultContainsNoCopy(self):
        self._create_confirmed_extra(member_id="1")
        self._set_parameter(key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, value=False)

        result = resolve_segments(
            cache={}, dynamic_segment_names_additive=[self.SEGMENT_COOP_MEMBERS]
        )

        self.assertSetEqual(
            {"mail1@test.net", "mail3@test.net"}, {r.email for r in result}
        )

    def test_resolveSegments_memberReachedThroughMailCategory_resultContainsNoCopy(
        self,
    ):
        member = self._create_confirmed_extra(member_id="1")
        mail_category = self._create_category_with_only_member_registered(member=member)

        result = resolve_segments(
            cache={}, mail_category_ids_additive=[mail_category.id]
        )

        self.assertEqual([AddressedRecipient.at_own_address(member)], result)

    @patch.object(signing.time, "time", autospec=True, return_value=1_000_000)
    def test_resolveSegments_memberInDynamicSegmentAndMailCategory_resultContainsEachAddressOnceWithCopy(
        self, _: MagicMock
    ):
        member = self._create_confirmed_extra(member_id="1")
        mail_category = self._create_category_with_only_member_registered(member=member)

        result = resolve_segments(
            cache={},
            dynamic_segment_names_additive=[self.SEGMENT_COOP_MEMBERS],
            mail_category_ids_additive=[mail_category.id],
        )

        self.assertEqual(
            [
                AddressedRecipient.at_own_address(member),
                self._build_copy(member=member),
                AddressedRecipient.at_own_address(Member.objects.get(id="3")),
            ],
            sorted(result, key=lambda addressed: addressed.recipient.id),
        )

    @patch.object(signing.time, "time", autospec=True, return_value=1_000_000)
    def test_resolveSegments_extraRegisteredToMailCategory_resultContainsExtra(
        self, _: MagicMock
    ):
        member = self._create_confirmed_extra(member_id="1")
        mail_category = self._create_category_with_only_member_registered(member=member)
        self._register_extra(member=member, mail_category=mail_category)

        result = resolve_segments(
            cache={}, mail_category_ids_additive=[mail_category.id]
        )

        self.assertEqual(
            [
                AddressedRecipient.at_own_address(member),
                self._build_copy(member=member),
            ],
            result,
        )

    def test_resolveSegments_extraInDynamicSegmentAndRegisteredToMailCategory_resultContainsExtraOnce(
        self,
    ):
        member = self._create_confirmed_extra(member_id="1")
        mail_category = self._create_category_with_only_member_registered(member=member)
        self._register_extra(member=member, mail_category=mail_category)

        result = resolve_segments(
            cache={},
            dynamic_segment_names_additive=[self.SEGMENT_COOP_MEMBERS],
            mail_category_ids_additive=[mail_category.id],
        )

        self.assertEqual(
            ["mail1@test.net", "extra@test.net", "mail3@test.net"],
            [r.email for r in sorted(result, key=lambda r: r.recipient.id)],
        )

    def test_resolveSegments_extraAddressInSubtractiveStaticSegment_copyNotInList(
        self,
    ):
        self._create_confirmed_extra(member_id="1")
        subtractive_static_segment = StaticSegment.objects.create(name="subtractive")
        StaticSegmentRecipient.objects.create(
            segment=subtractive_static_segment, email="extra@test.net"
        )

        result = resolve_segments(
            cache={},
            dynamic_segment_names_additive=[self.SEGMENT_COOP_MEMBERS],
            static_segment_ids_subtractive=[subtractive_static_segment.id],
        )

        self.assertSetEqual(
            {"mail1@test.net", "mail3@test.net"}, {r.email for r in result}
        )

    @patch.object(signing.time, "time", autospec=True, return_value=1_000_000)
    def test_resolveSegments_overrideRecipientByBaseQuerysetId_resultContainsRecipientAndItsCopies(
        self, _: MagicMock
    ):
        member = self._create_confirmed_extra(member_id="2")

        result = resolve_segments(
            cache={},
            dynamic_segment_names_additive=[self.SEGMENT_ALL_USERS],
            override_recipients=[{"recipient_id_in_base_queryset": "2"}],
        )

        self.assertEqual(
            [
                AddressedRecipient.at_own_address(member),
                self._build_copy(member=member),
            ],
            result,
        )

    def _create_confirmed_extra(self, member_id: str) -> Member:
        self._set_parameter(key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, value=True)
        member = Member.objects.get(id=member_id)
        MemberExtraEmailFactory.create(
            member=member,
            email="extra@test.net",
            first_name="Extra-FN",
            last_name="Extra-LN",
            confirmed_on=timezone.now(),
        )
        return member

    def _create_category_with_only_member_registered(
        self, member: Member
    ) -> MailCategory:
        mail_category = MailCategoryFactory.create(
            mode=MailCategoryMode.OPTIONAL_DEFAULT_OFF,
            dynamic_segment_name=self.SEGMENT_COOP_MEMBERS,
        )
        InternalRecipientCategoryRegistration.objects.create(
            member=member,
            mail_category=mail_category,
            is_registered=True,
        )
        return mail_category

    @staticmethod
    def _register_extra(member: Member, mail_category: MailCategory):
        InternalRecipientCategoryRegistration.objects.create(
            member_extra_email=member.memberextraemail_set.get(),
            mail_category=mail_category,
            is_registered=True,
        )

    @staticmethod
    def _build_copy(member: Member) -> AddressedRecipient:
        return AddressedRecipient(
            recipient=member,
            email="extra@test.net",
            token_overrides={
                "first_name": "Extra-FN",
                "last_name": "Extra-LN",
                SubscriptionManagementLinkProvider.TOKEN_NAME: SubscriptionManagementLinkProvider.build_link_for_address(
                    address="extra@test.net", cache={}
                ),
            },
        )
