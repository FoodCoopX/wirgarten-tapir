from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.mail.models import (
    StaticSegment,
    StaticSegmentRecipient,
    MailCategory,
    MailCategoryMode,
)
from tapir.mail.service.segment import resolve_segments
from tapir.mail.tests.factories import StaticSegmentRecipientFactory, MailSegmentFactory
from tapir.mail.tests.test_utils import add_mail_segment_provider
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.mail.triggers.transactional_trigger import TransactionalTriggerData
from tapir.wirgarten.models import Member
from tapir.wirgarten.tests.factories import MemberFactory


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
            dynamic_segment_names_additive=[self.SEGMENT_ALL_USERS]
        )
        self.assertSetEqual({r.id for r in result}, {"1", "2", "3", "4"})

    def test_combineSegmentsWithFilters_addAndRemoveSegments_returnsCorrectList(self):
        result = resolve_segments(
            dynamic_segment_names_additive=[self.SEGMENT_ALL_USERS],
            dynamic_segment_names_subtractive=[self.SEGMENT_NOT_COOP_MEMBERS],
        )
        self.assertSetEqual({r.id for r in result}, {"1", "3"})

    def test_combineSegmentsWithFilters_addDynamicAndStaticSegments_returnsCorrectList(
        self,
    ):
        result = resolve_segments(
            dynamic_segment_names_additive=[self.SEGMENT_NOT_COOP_MEMBERS],
            static_segment_ids_additive=[self.static_segment.id],
        )
        self.assertSetEqual(
            {
                r.email if isinstance(r, StaticSegmentRecipient) else r.id
                for r in result
            },
            {"2", "4", self.STATIC_RECIPIENT_1, self.STATIC_RECIPIENT_2},
        )

    def test_combineSegmentsWithFilters_addStaticSegment_returnsCorrectList(self):
        result = resolve_segments(static_segment_ids_additive=[self.static_segment.id])
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
            dynamic_segment_names_additive=[self.SEGMENT_ALL_USERS],
            override_recipients=[
                {"recipient_id_in_base_queryset": "2"},
                {"recipient_id_in_base_queryset": "4"},
            ],
        )
        self.assertSetEqual({r.id for r in result}, {"2", "4"})

    def test_resolveSegments_recipientsOutsideTheBaseQueryset_resultContainsFirstGivenRecipient(
        self,
    ):
        result = resolve_segments(
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
            TransactionalTriggerData.RecipientOutsideOfBaseQueryset(
                email="test@email.com",
                first_name="Max",
                last_name="Mustermann",
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

        result = resolve_segments(mail_category_ids_additive=[mail_category.id])
        self.assertEqual(3, len(result))
        self.assertIn(static_recipient, result)
        for user in Member.objects.filter(id__in=self.COOP_MEMBER_IDS):
            self.assertIn(user, result)
