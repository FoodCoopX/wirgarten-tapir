from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.mail.models import MailCategoryMode, InternalRecipientCategoryRegistration
from tapir.mail.services.mail_category_recipients_resolver import (
    MailCategoryRecipientResolver,
)

from tapir.mail.tests.factories import (
    MailSegmentFactory,
    MailCategoryFactory,
    StaticSegmentRecipientFactory,
)
from tapir.mail.tests.test_utils import add_mail_segment_provider
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.models import Member
from tapir.wirgarten.tests.factories import MemberFactory


class TestMailCategoryRecipientResolver(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_resolveRecipients_noDynamicSegment_returnsStaticRecipientsOnly(self):
        mail_category = MailCategoryFactory.create(dynamic_segment_name="")
        external_recipient = StaticSegmentRecipientFactory.create(
            segment=mail_category.static_segment
        )
        MemberFactory.create()

        result = MailCategoryRecipientResolver.resolve_recipients(
            mail_category=mail_category
        )

        self.assertEqual([external_recipient], result)

    def test_resolveRecipients_hasDynamicSegment_returnsStaticAndDynamicRecipients(
        self,
    ):
        mail_category = MailCategoryFactory.create(
            dynamic_segment_name="test_segment", mode=MailCategoryMode.ALWAYS_ON
        )
        external_recipient = StaticSegmentRecipientFactory.create(
            segment=mail_category.static_segment
        )
        add_mail_segment_provider(
            self,
            lambda: {
                "test_segment": MailSegmentFactory.build(
                    get_queryset=Member.objects.all
                )
            },
        )
        internal_recipient = MemberFactory.create()

        result = MailCategoryRecipientResolver.resolve_recipients(
            mail_category=mail_category
        )

        self.assertEqual({internal_recipient, external_recipient}, set(result))

    def test_resolveRecipients_modeIsAlwaysOn_userIsAlwaysIncluded(
        self,
    ):
        mail_category = MailCategoryFactory.create(
            dynamic_segment_name="test_segment", mode=MailCategoryMode.ALWAYS_ON
        )
        add_mail_segment_provider(
            self,
            lambda: {
                "test_segment": MailSegmentFactory.build(
                    get_queryset=Member.objects.all
                )
            },
        )
        internal_recipient = MemberFactory.create()

        result = MailCategoryRecipientResolver.resolve_recipients(
            mail_category=mail_category
        )
        self.assertEqual([internal_recipient], result)

        InternalRecipientCategoryRegistration.objects.create(
            internal_recipient_id=internal_recipient.id,
            mail_category=mail_category,
            is_registered=True,
        )
        result = MailCategoryRecipientResolver.resolve_recipients(
            mail_category=mail_category
        )
        self.assertEqual([internal_recipient], result)

        InternalRecipientCategoryRegistration.objects.update(is_registered=False)
        result = MailCategoryRecipientResolver.resolve_recipients(
            mail_category=mail_category
        )
        self.assertEqual([internal_recipient], result)

    def test_resolveRecipients_modeIsDefaultOn_userOnlyExcludedIfExplicitlyUnregistered(
        self,
    ):
        mail_category = MailCategoryFactory.create(
            dynamic_segment_name="test_segment",
            mode=MailCategoryMode.OPTIONAL_DEFAULT_ON,
        )
        add_mail_segment_provider(
            self,
            lambda: {
                "test_segment": MailSegmentFactory.build(
                    get_queryset=Member.objects.all
                )
            },
        )
        internal_recipient = MemberFactory.create()

        result = MailCategoryRecipientResolver.resolve_recipients(
            mail_category=mail_category
        )
        self.assertEqual([internal_recipient], result)

        InternalRecipientCategoryRegistration.objects.create(
            internal_recipient_id=internal_recipient.id,
            mail_category=mail_category,
            is_registered=True,
        )
        result = MailCategoryRecipientResolver.resolve_recipients(
            mail_category=mail_category
        )
        self.assertEqual([internal_recipient], result)

        InternalRecipientCategoryRegistration.objects.update(is_registered=False)
        result = MailCategoryRecipientResolver.resolve_recipients(
            mail_category=mail_category
        )
        self.assertEqual([], result)

    def test_resolveRecipients_modeIsDefaultOff_userOnlyIncludedIfExplicitlyRegistered(
        self,
    ):
        mail_category = MailCategoryFactory.create(
            dynamic_segment_name="test_segment",
            mode=MailCategoryMode.OPTIONAL_DEFAULT_OFF,
        )
        add_mail_segment_provider(
            self,
            lambda: {
                "test_segment": MailSegmentFactory.build(
                    get_queryset=Member.objects.all
                )
            },
        )
        internal_recipient = MemberFactory.create()

        result = MailCategoryRecipientResolver.resolve_recipients(
            mail_category=mail_category
        )
        self.assertEqual([], result)

        InternalRecipientCategoryRegistration.objects.create(
            internal_recipient_id=internal_recipient.id,
            mail_category=mail_category,
            is_registered=True,
        )
        result = MailCategoryRecipientResolver.resolve_recipients(
            mail_category=mail_category
        )
        self.assertEqual([internal_recipient], result)

        InternalRecipientCategoryRegistration.objects.update(is_registered=False)
        result = MailCategoryRecipientResolver.resolve_recipients(
            mail_category=mail_category
        )
        self.assertEqual([], result)
