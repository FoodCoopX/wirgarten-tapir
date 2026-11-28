from unittest.mock import MagicMock, patch

from django.test import override_settings
from django.utils import timezone

from tapir.core.services.active_member_provider import ActiveMemberProvider
from tapir.core.services.member_extra_email_registration_snapshotter import (
    MemberExtraEmailRegistrationSnapshotter,
)
from tapir.core.tests.mailman_test_helper import MailmanTestHelper, MockMailingListData
from tapir.mail.models import (
    InternalRecipientCategoryRegistration,
    MailCategory,
    MailCategoryMode,
)
from tapir.mail.tests.factories import MailCategoryFactory, MailSegmentFactory
from tapir.mail.tests.test_utils import add_mail_segment_provider
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberExtraEmailFactory, MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@patch.object(
    ActiveMemberProvider,
    "get_active_members",
    autospec=True,
    side_effect=lambda reference_datetime, cache: Member.objects.all(),
)
@override_settings(MAILING_LISTS_ENABLED=True, MAILING_LIST_DOMAIN="example.com")
class TestSnapshot(TapirIntegrationTest):
    SEGMENT_WITH_MEMBER = "segment_with_member"
    SEGMENT_WITHOUT_MEMBER = "segment_without_member"

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        self.member = MemberFactory.create(email="member@example.com")
        self.extra_email = MemberExtraEmailFactory.create(
            member=self.member,
            email="extra@example.com",
            confirmed_on=timezone.now(),
        )
        add_mail_segment_provider(
            self,
            lambda: {
                self.SEGMENT_WITH_MEMBER: MailSegmentFactory.build(
                    get_queryset=Member.objects.all
                ),
                self.SEGMENT_WITHOUT_MEMBER: MailSegmentFactory.build(
                    get_queryset=Member.objects.none
                ),
            },
        )

    def test_snapshot_default_createsOneRegistrationPerCategoryContainingTheMemberWithTheMemberState(
        self, _: MagicMock
    ):
        MailmanTestHelper.mock_domain(test=self, mailing_list_datas=[])
        always_on = self._create_category(mode=MailCategoryMode.ALWAYS_ON)
        default_on = self._create_category(mode=MailCategoryMode.OPTIONAL_DEFAULT_ON)
        default_off = self._create_category(mode=MailCategoryMode.OPTIONAL_DEFAULT_OFF)
        member_unregistered = self._create_category(
            mode=MailCategoryMode.OPTIONAL_DEFAULT_ON
        )
        member_registered = self._create_category(
            mode=MailCategoryMode.OPTIONAL_DEFAULT_OFF
        )
        self._create_category(
            mode=MailCategoryMode.ALWAYS_ON,
            dynamic_segment_name=self.SEGMENT_WITHOUT_MEMBER,
        )
        self._create_category(mode=MailCategoryMode.ALWAYS_ON, dynamic_segment_name="")
        for mail_category, is_registered in [
            (member_unregistered, False),
            (member_registered, True),
        ]:
            InternalRecipientCategoryRegistration.objects.create(
                member=self.member,
                mail_category=mail_category,
                is_registered=is_registered,
            )

        self._snapshot()

        self.assertEqual(
            {
                (always_on.id, True),
                (default_on.id, True),
                (default_off.id, False),
                (member_unregistered.id, False),
                (member_registered.id, True),
            },
            set(
                InternalRecipientCategoryRegistration.objects.filter(
                    member_extra_email=self.extra_email
                ).values_list("mail_category_id", "is_registered")
            ),
        )

    def test_snapshot_default_subscribesExtraToTheListsOfTheMainAddress(
        self, _: MagicMock
    ):
        domain = MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(
                    name="member_subscribed", confirmed_recipients=[self.member.email]
                ),
                MockMailingListData(
                    name="member_invited", unconfirmed_recipients=[self.member.email]
                ),
                MockMailingListData(name="member_not_subscribed"),
                MockMailingListData(
                    name="extra_already_subscribed",
                    confirmed_recipients=[self.member.email, self.extra_email.email],
                ),
                MockMailingListData(
                    name="extra_already_invited",
                    confirmed_recipients=[self.member.email],
                    unconfirmed_recipients=[self.extra_email.email],
                ),
            ],
        )

        self._snapshot()

        domain.lists[0].subscribe.assert_called_once_with(
            address=self.extra_email.email,
            pre_verified=True,
            pre_confirmed=True,
            pre_approved=True,
            send_welcome_message=False,
        )
        for mailing_list in domain.lists[1:]:
            mailing_list.subscribe.assert_not_called()

    def test_snapshot_memberHasLeft_doesNotSubscribeButStillSnapshotsTheCategories(
        self, mock_get_active_members: MagicMock
    ):
        mock_get_active_members.side_effect = (
            lambda reference_datetime, cache: Member.objects.none()
        )
        mail_category = MailCategoryFactory.create(
            dynamic_segment_name=self.SEGMENT_WITH_MEMBER
        )
        domain = MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(
                    name="member_subscribed", confirmed_recipients=[self.member.email]
                )
            ],
        )

        self._snapshot()

        domain.lists[0].subscribe.assert_not_called()
        self.assertTrue(
            InternalRecipientCategoryRegistration.objects.filter(
                member_extra_email=self.extra_email, mail_category=mail_category
            ).exists()
        )

    @override_settings(MAILING_LISTS_ENABLED=False)
    def test_snapshot_mailingListsDisabled_doesNotSubscribe(self, _: MagicMock):
        domain = MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(
                    name="member_subscribed", confirmed_recipients=[self.member.email]
                ),
            ],
        )

        self._snapshot()

        domain.lists[0].subscribe.assert_not_called()

    def test_snapshot_default_subscribesOnlyAfterCommit(self, _: MagicMock):
        domain = MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(
                    name="member_subscribed", confirmed_recipients=[self.member.email]
                ),
            ],
        )

        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            MemberExtraEmailRegistrationSnapshotter.snapshot(
                extra_email=self.extra_email, cache={}
            )

        domain.lists[0].subscribe.assert_not_called()
        self.assertEqual(1, len(callbacks))

    def _snapshot(self):
        with self.captureOnCommitCallbacks(execute=True):
            MemberExtraEmailRegistrationSnapshotter.snapshot(
                extra_email=self.extra_email, cache={}
            )

    def _create_category(
        self, mode: MailCategoryMode, dynamic_segment_name: str | None = None
    ) -> MailCategory:
        return MailCategoryFactory.create(
            mode=mode,
            dynamic_segment_name=(
                self.SEGMENT_WITH_MEMBER
                if dynamic_segment_name is None
                else dynamic_segment_name
            ),
        )
