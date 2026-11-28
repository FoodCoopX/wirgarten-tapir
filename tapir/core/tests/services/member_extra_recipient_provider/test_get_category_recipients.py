from django.test import override_settings
from django.utils import timezone

from tapir.core.services.member_extra_recipient_provider import (
    MemberExtraRecipientProvider,
)
from tapir.core.services.subscription_management_link_provider import (
    SubscriptionManagementLinkProvider,
)
from tapir.core.services.subscription_management_token_signer import (
    SubscriptionManagementTokenSigner,
)
from tapir.mail.addressed_recipient import AddressedRecipient
from tapir.mail.models import (
    InternalRecipientCategoryRegistration,
    MailCategory,
    MailCategoryMode,
)
from tapir.mail.tests.factories import MailCategoryFactory, MailSegmentFactory
from tapir.mail.tests.test_utils import add_mail_segment_provider
from tapir.wirgarten.models import Member, MemberExtraEmail
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberExtraEmailFactory, MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetCategoryRecipients(TapirIntegrationTest):
    SEGMENT_NAME = "test_segment"

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        self._set_parameter(key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, value=True)
        self.member_in_segment = MemberFactory.create()
        self.member_outside_segment = MemberFactory.create()
        add_mail_segment_provider(
            self,
            lambda: {
                self.SEGMENT_NAME: MailSegmentFactory.build(
                    get_queryset=lambda: Member.objects.filter(
                        id=self.member_in_segment.id
                    )
                )
            },
        )

    def test_getCategoryRecipients_featureDisabled_returnsEmptyList(self):
        self._set_parameter(key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, value=False)
        self._create_confirmed_extra(member=self.member_in_segment)
        mail_category = self._create_category(mode=MailCategoryMode.ALWAYS_ON)

        result = MemberExtraRecipientProvider.get_category_recipients(
            mail_category=mail_category, cache={}
        )

        self.assertEqual([], result)

    def test_getCategoryRecipients_categoryHasNoDynamicSegment_returnsEmptyList(self):
        self._create_confirmed_extra(member=self.member_in_segment)
        mail_category = MailCategoryFactory.create(
            mode=MailCategoryMode.ALWAYS_ON, dynamic_segment_name=""
        )

        result = MemberExtraRecipientProvider.get_category_recipients(
            mail_category=mail_category, cache={}
        )

        self.assertEqual([], result)

    @override_settings(SITE_URL="https://tapir.example")
    def test_getCategoryRecipients_default_returnsConfirmedExtrasOfMembersInSegmentWithTokenOverrides(
        self,
    ):
        extra_email = self._create_confirmed_extra(member=self.member_in_segment)
        self._create_confirmed_extra(member=self.member_outside_segment)
        MemberExtraEmailFactory.create(member=self.member_in_segment, confirmed_on=None)
        mail_category = self._create_category(mode=MailCategoryMode.ALWAYS_ON)

        result = MemberExtraRecipientProvider.get_category_recipients(
            mail_category=mail_category, cache={}
        )

        management_link = result[0].token_overrides[
            SubscriptionManagementLinkProvider.TOKEN_NAME
        ]
        self.assertEqual(
            [
                AddressedRecipient(
                    recipient=self.member_in_segment,
                    email=extra_email.email,
                    token_overrides={
                        "first_name": extra_email.first_name,
                        "last_name": extra_email.last_name,
                        SubscriptionManagementLinkProvider.TOKEN_NAME: management_link,
                    },
                )
            ],
            result,
        )
        link_prefix = "https://tapir.example/core/subscription_management/"
        self.assertTrue(management_link.startswith(link_prefix))
        self.assertEqual(
            extra_email.email,
            SubscriptionManagementTokenSigner.get_address(
                token=management_link.removeprefix(link_prefix)
            ),
        )

    def test_getCategoryRecipients_extraDoesNotReceiveDirectMails_extraIsIncluded(
        self,
    ):
        extra_email = self._create_confirmed_extra(
            member=self.member_in_segment, receives_direct_mails=False
        )
        mail_category = self._create_category(mode=MailCategoryMode.ALWAYS_ON)

        result = MemberExtraRecipientProvider.get_category_recipients(
            mail_category=mail_category, cache={}
        )

        self.assertEqual([extra_email.email], [r.email for r in result])

    def test_getCategoryRecipients_noRegistration_followsExtraDefaults(self):
        self._create_confirmed_extra(member=self.member_in_segment)
        expected_inclusion_by_mode = {
            MailCategoryMode.ALWAYS_ON: True,
            MailCategoryMode.OPTIONAL_DEFAULT_ON: True,
            MailCategoryMode.OPTIONAL_DEFAULT_OFF: False,
        }

        for mode, is_included in expected_inclusion_by_mode.items():
            with self.subTest(mode=mode):
                mail_category = self._create_category(mode=mode)

                result = MemberExtraRecipientProvider.get_category_recipients(
                    mail_category=mail_category, cache={}
                )

                self.assertEqual(is_included, len(result) == 1)

    def test_getCategoryRecipients_extraHasRegistration_followsRegistration(self):
        extra_email = self._create_confirmed_extra(member=self.member_in_segment)

        for mode in MailCategoryMode:
            for is_registered in [True, False]:
                with self.subTest(mode=mode, is_registered=is_registered):
                    mail_category = self._create_category(mode=mode)
                    InternalRecipientCategoryRegistration.objects.create(
                        member_extra_email=extra_email,
                        mail_category=mail_category,
                        is_registered=is_registered,
                    )

                    result = MemberExtraRecipientProvider.get_category_recipients(
                        mail_category=mail_category, cache={}
                    )

                    self.assertEqual(is_registered, len(result) == 1)

    def test_getCategoryRecipients_memberIsUnregistered_extraIsStillIncluded(self):
        self._create_confirmed_extra(member=self.member_in_segment)
        mail_category = self._create_category(mode=MailCategoryMode.OPTIONAL_DEFAULT_ON)
        InternalRecipientCategoryRegistration.objects.create(
            member=self.member_in_segment,
            mail_category=mail_category,
            is_registered=False,
        )

        result = MemberExtraRecipientProvider.get_category_recipients(
            mail_category=mail_category, cache={}
        )

        self.assertEqual(1, len(result))

    def _create_category(self, mode: MailCategoryMode) -> MailCategory:
        return MailCategoryFactory.create(
            mode=mode, dynamic_segment_name=self.SEGMENT_NAME
        )

    @staticmethod
    def _create_confirmed_extra(
        member: Member, receives_direct_mails: bool = True
    ) -> MemberExtraEmail:
        return MemberExtraEmailFactory.create(
            member=member,
            confirmed_on=timezone.now(),
            receives_direct_mails=receives_direct_mails,
        )
