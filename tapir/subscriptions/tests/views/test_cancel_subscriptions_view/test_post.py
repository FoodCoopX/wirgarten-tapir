import datetime
from decimal import Decimal
from unittest.mock import patch, Mock, ANY

from django.urls import reverse
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.configuration.models import TapirParameter
from tapir.coop.services.membership_cancellation_manager import (
    MembershipCancellationManager,
)
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.solidarity_contribution.tests.factories import SolidarityContributionFactory
from tapir.subscriptions.services.subscription_cancellation_manager import (
    SubscriptionCancellationManager,
)
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import (
    SubscriptionChangeLogEntry,
    QuestionaireCancellationReasonResponse,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    SubscriptionFactory,
    NOW,
    GrowingPeriodFactory,
    TODAY,
    ProductTypeFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone
from tapir.wirgarten.utils import format_date, format_subscription_list_html


class TestCancelSubscriptionsPostView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        mock_timezone(self, NOW)

    @patch.object(MembershipCancellationManager, "cancel_coop_membership")
    @patch.object(SubscriptionCancellationManager, "cancel_subscriptions")
    def test_post_memberCancelsSubscriptionsOfOtherMember_returns403(
        self,
        mock_cancel_subscriptions: Mock,
        mock_cancel_coop_membership: Mock,
    ):
        actor = MemberFactory.create()
        target = MemberFactory.create()
        self.client.force_login(actor)

        subscriptions = SubscriptionFactory.create_batch(size=3, member=target)
        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=subscriptions[0].product.type_id
        )

        post_data = {
            "member_id": target.id,
            "product_ids": [subscription.product_id for subscription in subscriptions],
            "cancel_coop_membership": False,
            "cancellation_reasons": [],
            "custom_cancellation_reason": "Test reason",
        }

        url = reverse("subscriptions:cancel_subscriptions")
        response = self.client.post(url, data=post_data)

        self.assertStatusCode(response, 403)
        mock_cancel_subscriptions.assert_not_called()
        mock_cancel_coop_membership.assert_not_called()

    @patch.object(SubscriptionCancellationManager, "cancel_subscriptions")
    def test_post_memberCancelsOwnSubscriptions_returns200(
        self, mock_cancel_subscriptions: Mock
    ):
        member = MemberFactory.create()
        self.client.force_login(member)
        mock_cancel_subscriptions.return_value = [], []

        subscriptions = SubscriptionFactory.create_batch(size=3, member=member)
        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=subscriptions[0].product.type_id
        )

        post_data = {
            "member_id": member.id,
            "product_ids": [subscription.product_id for subscription in subscriptions],
            "cancel_coop_membership": False,
            "cancellation_reasons": [],
            "custom_cancellation_reason": "Test reason",
        }

        url = reverse("subscriptions:cancel_subscriptions")
        response = self.client.post(url, data=post_data)

        self.assertStatusCode(response, 200)
        self.assertEqual(3, mock_cancel_subscriptions.call_count)

    @patch.object(SubscriptionCancellationManager, "cancel_subscriptions")
    def test_post_adminCancelsSubscriptionOfOtherMember_returns200(
        self, mock_cancel_subscriptions: Mock
    ):
        actor = MemberFactory.create(is_superuser=True)
        target = MemberFactory.create()
        self.client.force_login(actor)
        mock_cancel_subscriptions.return_value = [], []

        subscriptions = SubscriptionFactory.create_batch(size=3, member=target)
        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=subscriptions[0].product.type_id
        )

        post_data = {
            "member_id": target.id,
            "product_ids": [subscription.product_id for subscription in subscriptions],
            "cancel_coop_membership": False,
            "cancellation_reasons": [],
            "custom_cancellation_reason": "Test reason",
        }

        url = reverse("subscriptions:cancel_subscriptions")
        response = self.client.post(url, data=post_data)

        self.assertStatusCode(response, 200)
        self.assertEqual(3, mock_cancel_subscriptions.call_count)

    @patch.object(MembershipCancellationManager, "cancel_coop_membership")
    @patch.object(SubscriptionCancellationManager, "cancel_subscriptions")
    @patch.object(MembershipCancellationManager, "can_member_cancel_coop_membership")
    def test_post_memberTriesToCancelCoopMembershipButCannot_returnsError(
        self,
        mock_can_member_cancel_coop_membership: Mock,
        mock_cancel_subscriptions: Mock,
        mock_cancel_coop_membership: Mock,
    ):
        mock_can_member_cancel_coop_membership.return_value = False
        member = MemberFactory.create()
        self.client.force_login(member)

        subscriptions = SubscriptionFactory.create_batch(size=3, member=member)

        post_data = {
            "member_id": member.id,
            "product_ids": [subscription.product_id for subscription in subscriptions],
            "cancel_coop_membership": True,
            "cancellation_reasons": [],
            "custom_cancellation_reason": "Test reason",
        }

        url = reverse("subscriptions:cancel_subscriptions")
        response = self.client.post(url, data=post_data)

        self.assertStatusCode(response, 200)
        self.assertEqual(1, len(response.json()["errors"]))
        mock_cancel_subscriptions.assert_not_called()
        mock_cancel_coop_membership.assert_not_called()

    @patch.object(MembershipCancellationManager, "cancel_coop_membership")
    @patch.object(SubscriptionCancellationManager, "cancel_subscriptions")
    @patch.object(MembershipCancellationManager, "can_member_cancel_coop_membership")
    def test_post_memberTriesToCancelCoopMembershipAndIsAllowed_cancelsCoopMembership(
        self,
        mock_can_member_cancel_coop_membership: Mock,
        mock_cancel_subscriptions: Mock,
        mock_cancel_coop_membership: Mock,
    ):
        mock_can_member_cancel_coop_membership.return_value = True
        member = MemberFactory.create()
        self.client.force_login(member)
        mock_cancel_subscriptions.return_value = [], []

        subscriptions = SubscriptionFactory.create_batch(size=3, member=member)
        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=subscriptions[0].product.type_id
        )

        post_data = {
            "member_id": member.id,
            "product_ids": [subscription.product_id for subscription in subscriptions],
            "cancel_coop_membership": True,
            "cancellation_reasons": [],
            "custom_cancellation_reason": "Test reason",
        }

        url = reverse("subscriptions:cancel_subscriptions")
        response = self.client.post(url, data=post_data)

        self.assertStatusCode(response, 200)
        self.assertEqual(0, len(response.json()["errors"]))
        self.assertEqual(3, mock_cancel_subscriptions.call_count)
        mock_cancel_coop_membership.assert_called_once_with(
            member, cache=ANY, actor=ANY
        )
        self.assertEqual(
            member.email, mock_cancel_coop_membership.call_args.kwargs["actor"].email
        )

    @patch.object(MembershipCancellationManager, "cancel_coop_membership")
    @patch.object(SubscriptionCancellationManager, "cancel_subscriptions")
    @patch.object(MembershipCancellationManager, "can_member_cancel_coop_membership")
    def test_post_memberDoesntCancelCoopMembership_coopMembershipNotCancelled(
        self,
        mock_can_member_cancel_coop_membership: Mock,
        mock_cancel_subscriptions: Mock,
        mock_cancel_coop_membership: Mock,
    ):
        mock_can_member_cancel_coop_membership.return_value = False
        member = MemberFactory.create()
        self.client.force_login(member)
        mock_cancel_subscriptions.return_value = [], []

        subscriptions = SubscriptionFactory.create_batch(size=3, member=member)
        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=subscriptions[0].product.type_id
        )

        post_data = {
            "member_id": member.id,
            "product_ids": [subscription.product_id for subscription in subscriptions],
            "cancel_coop_membership": False,
            "cancellation_reasons": [],
            "custom_cancellation_reason": "Test reason",
        }

        url = reverse("subscriptions:cancel_subscriptions")
        response = self.client.post(url, data=post_data)

        self.assertStatusCode(response, 200)
        self.assertEqual(0, len(response.json()["errors"]))
        self.assertEqual(3, mock_cancel_subscriptions.call_count)
        mock_cancel_coop_membership.assert_not_called()

    @patch.object(SubscriptionCancellationManager, "cancel_subscriptions")
    def test_post_cantHaveAdditionalProductsWithoutBaseProduct_returnsError(
        self,
        mock_cancel_subscriptions: Mock,
    ):
        member = MemberFactory.create()
        self.client.force_login(member)
        mock_cancel_subscriptions.return_value = [], []

        subscriptions = SubscriptionFactory.create_batch(size=3, member=member)
        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=subscriptions[0].product.type_id
        )
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_ADDITIONAL_PRODUCT_ALLOWED_WITHOUT_BASE_PRODUCT
        ).update(value=False)

        post_data = {
            "member_id": member.id,
            "product_ids": [subscriptions[0].product_id],
            "cancel_coop_membership": False,
            "cancellation_reasons": [],
            "custom_cancellation_reason": "Test reason",
        }

        url = reverse("subscriptions:cancel_subscriptions")
        response = self.client.post(url, data=post_data)

        self.assertStatusCode(response, 200)
        self.assertEqual(1, len(response.json()["errors"]))
        mock_cancel_subscriptions.assert_not_called()

    @patch.object(SubscriptionCancellationManager, "cancel_subscriptions")
    def test_post_additionalProductsWithoutBaseProductAllowed_cancelsBaseProduct(
        self,
        mock_cancel_subscriptions: Mock,
    ):
        member = MemberFactory.create()
        self.client.force_login(member)
        mock_cancel_subscriptions.return_value = [], []

        subscriptions = SubscriptionFactory.create_batch(size=3, member=member)
        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=subscriptions[0].product.type_id
        )
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_ADDITIONAL_PRODUCT_ALLOWED_WITHOUT_BASE_PRODUCT
        ).update(value=True)

        post_data = {
            "member_id": member.id,
            "product_ids": [subscriptions[0].product_id],
            "cancel_coop_membership": False,
            "cancellation_reasons": [],
            "custom_cancellation_reason": "Test reason",
        }

        url = reverse("subscriptions:cancel_subscriptions")
        response = self.client.post(url, data=post_data)

        self.assertStatusCode(response, 200)
        self.assertEqual(0, len(response.json()["errors"]))
        mock_cancel_subscriptions.assert_called_once_with(
            subscriptions[0].product, member, cache=ANY
        )

    @patch.object(TransactionalTrigger, "fire_action")
    def test_post_default_sendsMailTriggerAndCreatesLogEntryAndSavesCancellationReasons(
        self,
        mock_fire_action: Mock,
    ):
        member = MemberFactory.create()
        self.client.force_login(member)

        growing_period = GrowingPeriodFactory.create(
            start_date=TODAY.replace(month=1, day=1),
            end_date=TODAY.replace(month=12, day=31),
        )
        subscriptions = SubscriptionFactory.create_batch(
            size=3,
            member=member,
            period=growing_period,
        )
        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=subscriptions[0].product.type_id
        )
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_ADDITIONAL_PRODUCT_ALLOWED_WITHOUT_BASE_PRODUCT
        ).update(value=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        ).update(value=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.MEMBER_CANCELLATION_REASON_CHOICES
        ).update(value="reason1 ;   reason2  ")

        post_data = {
            "member_id": member.id,
            "product_ids": [
                subscription.product_id for subscription in subscriptions[:2]
            ],
            "cancel_coop_membership": False,
            "cancellation_reasons": ["reason1", "reason2"],
            "custom_cancellation_reason": "reason3",
        }

        url = reverse("subscriptions:cancel_subscriptions")
        response = self.client.post(url, data=post_data)

        self.assertStatusCode(response, 200)
        self.assertEqual(0, len(response.json()["errors"]))
        mock_fire_action.assert_called_once_with(
            TransactionalTriggerData(
                key=Events.CONTRACT_CANCELLED,
                recipient_id_in_base_queryset=member.id,
                token_data={
                    "contract_list": format_subscription_list_html(subscriptions[:2]),
                    "contract_end_date": format_date(growing_period.end_date),
                },
            )
        )

        self.assertEqual(1, SubscriptionChangeLogEntry.objects.count())
        log_entry = SubscriptionChangeLogEntry.objects.get()
        self.assertEqual(
            SubscriptionChangeLogEntry.SubscriptionChangeLogEntryType.CANCELLED,
            log_entry.change_type,
        )
        self.assertEqual(
            SubscriptionChangeLogEntry.build_subscription_list_as_string(
                subscriptions[:2]
            ),
            log_entry.subscriptions,
        )
        self.assertEqual(3, QuestionaireCancellationReasonResponse.objects.count())
        self.assertTrue(
            QuestionaireCancellationReasonResponse.objects.filter(
                member=member, reason="reason1", custom=False, timestamp=NOW
            ).exists()
        )
        self.assertTrue(
            QuestionaireCancellationReasonResponse.objects.filter(
                member=member, reason="reason2", custom=False, timestamp=NOW
            ).exists()
        )
        self.assertTrue(
            QuestionaireCancellationReasonResponse.objects.filter(
                member=member, reason="reason3", custom=True, timestamp=NOW
            ).exists()
        )

    @patch.object(TransactionalTrigger, "fire_action")
    def test_post_aSubscriptionStartsInTheFuture_subscriptionIsIncludedInMailTriggerAndHasOwnLogEntry(
        self,
        mock_fire_action: Mock,
    ):
        member = MemberFactory.create()
        self.client.force_login(member)

        growing_period = GrowingPeriodFactory.create(
            start_date=TODAY.replace(month=1, day=1)
        )
        subscriptions = SubscriptionFactory.create_batch(
            size=3,
            member=member,
            period=growing_period,
        )
        subscriptions[1].start_date = TODAY + datetime.timedelta(days=5)
        subscriptions[1].save()

        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=subscriptions[0].product.type_id
        )
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_ADDITIONAL_PRODUCT_ALLOWED_WITHOUT_BASE_PRODUCT
        ).update(value=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        ).update(value=True)

        post_data = {
            "member_id": member.id,
            "product_ids": [
                subscription.product_id for subscription in subscriptions[:2]
            ],
            "cancel_coop_membership": False,
            "cancellation_reasons": [],
            "custom_cancellation_reason": "Test reason",
        }

        url = reverse("subscriptions:cancel_subscriptions")
        response = self.client.post(url, data=post_data)

        self.assertStatusCode(response, 200)
        self.assertEqual(0, len(response.json()["errors"]))

        mock_fire_action.assert_called_once_with(
            TransactionalTriggerData(
                key=Events.CONTRACT_CANCELLED,
                recipient_id_in_base_queryset=member.id,
                token_data={
                    "contract_list": format_subscription_list_html(subscriptions[:2]),
                    "contract_end_date": format_date(growing_period.end_date),
                },
            )
        )

        self.assertEqual(2, SubscriptionChangeLogEntry.objects.count())
        log_entry = SubscriptionChangeLogEntry.objects.filter(
            admin_confirmed=NOW
        ).first()
        self.assertIsNotNone(log_entry)
        self.assertEqual(
            SubscriptionChangeLogEntry.SubscriptionChangeLogEntryType.CANCELLED,
            log_entry.change_type,
        )
        self.assertEqual(
            SubscriptionChangeLogEntry.build_subscription_list_as_string(
                [subscriptions[0]]
            ),
            log_entry.subscriptions,
        )

        log_entry = SubscriptionChangeLogEntry.objects.filter(
            admin_confirmed=None
        ).first()
        self.assertIsNotNone(log_entry)
        self.assertEqual(
            SubscriptionChangeLogEntry.SubscriptionChangeLogEntryType.CANCELLED,
            log_entry.change_type,
        )
        self.assertEqual(
            SubscriptionChangeLogEntry.build_subscription_list_as_string(
                [subscriptions[1]]
            ),
            log_entry.subscriptions,
        )

    @patch.object(SubscriptionCancellationManager, "cancel_subscriptions")
    @patch.object(TransactionalTrigger, "fire_action")
    def test_post_cancellationReasonIsInvalid_returnsError(
        self, mock_fire_action: Mock, mock_cancel_subscriptions: Mock
    ):
        member = MemberFactory.create()
        self.client.force_login(member)

        growing_period = GrowingPeriodFactory.create(
            start_date=TODAY.replace(month=1, day=1),
            end_date=TODAY.replace(month=12, day=31),
        )
        subscriptions = SubscriptionFactory.create_batch(
            size=3,
            member=member,
            period=growing_period,
        )
        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=subscriptions[0].product.type_id
        )
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_ADDITIONAL_PRODUCT_ALLOWED_WITHOUT_BASE_PRODUCT
        ).update(value=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        ).update(value=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.MEMBER_CANCELLATION_REASON_CHOICES
        ).update(value="reason1 ;   reason2  ")

        post_data = {
            "member_id": member.id,
            "product_ids": [
                subscription.product_id for subscription in subscriptions[:2]
            ],
            "cancel_coop_membership": False,
            "cancellation_reasons": ["reason1", "reason4"],
            "custom_cancellation_reason": "reason3",
        }

        url = reverse("subscriptions:cancel_subscriptions")
        response = self.client.post(url, data=post_data)

        response_content = response.json()
        self.assertStatusCode(response, 200)
        self.assertEqual(1, len(response_content["errors"]))
        self.assertEqual(
            "Folgende Kündigungsgrund ist nicht gültig: reason4, gültige Gründe sind: ['reason1', 'reason2']",
            response_content["errors"][0],
        )
        mock_fire_action.assert_not_called()
        mock_cancel_subscriptions.assert_not_called()

    @patch.object(SubscriptionCancellationManager, "cancel_subscriptions")
    @patch.object(TransactionalTrigger, "fire_action")
    def test_post_noCancellationReasonSent_returnsError(
        self, mock_fire_action: Mock, mock_cancel_subscriptions: Mock
    ):
        member = MemberFactory.create()
        self.client.force_login(member)

        growing_period = GrowingPeriodFactory.create(
            start_date=TODAY.replace(month=1, day=1),
            end_date=TODAY.replace(month=12, day=31),
        )
        subscriptions = SubscriptionFactory.create_batch(
            size=3,
            member=member,
            period=growing_period,
        )
        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=subscriptions[0].product.type_id
        )
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_ADDITIONAL_PRODUCT_ALLOWED_WITHOUT_BASE_PRODUCT
        ).update(value=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        ).update(value=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.MEMBER_CANCELLATION_REASON_CHOICES
        ).update(value="reason1 ;   reason2  ")

        post_data = {
            "member_id": member.id,
            "product_ids": [subscription.product_id for subscription in subscriptions],
            "cancel_coop_membership": False,
            "cancellation_reasons": [],
            "custom_cancellation_reason": "",
        }

        url = reverse("subscriptions:cancel_subscriptions")
        response = self.client.post(url, data=post_data)

        response_content = response.json()
        self.assertStatusCode(response, 200)
        self.assertEqual(1, len(response_content["errors"]))
        self.assertEqual(
            "Es muss mindestens 1 Kündigungsgrund angegeben werden.",
            response_content["errors"][0],
        )
        mock_fire_action.assert_not_called()
        mock_cancel_subscriptions.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action")
    def test_post_noCustomReasonSent_doesntCreateACustomObject(
        self, mock_fire_action: Mock
    ):
        member = MemberFactory.create()
        self.client.force_login(member)

        growing_period = GrowingPeriodFactory.create(
            start_date=TODAY.replace(month=1, day=1),
            end_date=TODAY.replace(month=12, day=31),
        )
        subscriptions = SubscriptionFactory.create_batch(
            size=3,
            member=member,
            period=growing_period,
        )
        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=subscriptions[0].product.type_id
        )
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_ADDITIONAL_PRODUCT_ALLOWED_WITHOUT_BASE_PRODUCT
        ).update(value=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        ).update(value=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.MEMBER_CANCELLATION_REASON_CHOICES
        ).update(value="reason1 ;   reason2  ")

        post_data = {
            "member_id": member.id,
            "product_ids": [subscription.product_id for subscription in subscriptions],
            "cancel_coop_membership": False,
            "cancellation_reasons": ["reason1"],
            "custom_cancellation_reason": "",
        }

        url = reverse("subscriptions:cancel_subscriptions")
        response = self.client.post(url, data=post_data)

        response_content = response.json()
        self.assertStatusCode(response, 200)
        self.assertEqual(0, len(response_content["errors"]))

        mock_fire_action.assert_called_once_with(
            TransactionalTriggerData(
                key=Events.CONTRACT_CANCELLED,
                recipient_id_in_base_queryset=member.id,
                token_data={
                    "contract_list": format_subscription_list_html(subscriptions),
                    "contract_end_date": format_date(growing_period.end_date),
                },
            )
        )
        self.assertEqual(1, QuestionaireCancellationReasonResponse.objects.count())
        self.assertTrue(
            QuestionaireCancellationReasonResponse.objects.filter(
                member=member, reason="reason1", custom=False, timestamp=NOW
            ).exists()
        )

    def test_post_memberCancelsSolidarityButItCannotBeCancelled_returnsError(self):
        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=ProductTypeFactory.create().id
        )
        member = MemberFactory.create()
        self.client.force_login(member)

        post_data = {
            "member_id": member.id,
            "product_ids": [],
            "cancel_coop_membership": False,
            "cancellation_reasons": [],
            "custom_cancellation_reason": "Test reason",
            "cancel_solidarity_contribution": True,
        }

        url = reverse("subscriptions:cancel_subscriptions")
        response = self.client.post(url, data=post_data)

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertEqual(1, len(response_content["errors"]))
        self.assertEqual(
            "Es kann kein Solidarbeitrag gekündigt werden.",
            response_content["errors"][0],
        )

    def test_post_memberCancelsSolidarity_correctlyUpdatesContribution(self):
        mock_timezone(
            test=self, now=datetime.datetime(year=2013, month=1, day=20, hour=10)
        )
        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=ProductTypeFactory.create().id
        )
        TapirParameter.objects.filter(key=ParameterKeys.TRIAL_PERIOD_ENABLED).update(
            value=True
        )
        TapirParameter.objects.filter(key=ParameterKeys.TRIAL_PERIOD_DURATION).update(
            value=8
        )
        TapirParameter.objects.filter(
            key=ParameterKeys.TRIAL_PERIOD_CAN_BE_CANCELLED_BEFORE_END
        ).update(value=True)

        member = MemberFactory.create()
        self.client.force_login(member)

        SolidarityContributionFactory.create(
            member=member,
            start_date=datetime.date(year=2013, month=1, day=1),
            amount=12,
        )
        SolidarityContributionFactory.create(
            member=member,
            start_date=datetime.date(year=2014, month=1, day=1),
            amount=13.5,
        )

        post_data = {
            "member_id": member.id,
            "product_ids": [],
            "cancel_coop_membership": False,
            "cancellation_reasons": [],
            "custom_cancellation_reason": "Test reason",
            "cancel_solidarity_contribution": True,
        }

        url = reverse("subscriptions:cancel_subscriptions")
        response = self.client.post(url, data=post_data)

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertEqual(0, len(response_content["errors"]))

        self.assertEqual(1, SolidarityContribution.objects.count())
        contribution = SolidarityContribution.objects.get()
        self.assertEqual(Decimal(12), contribution.amount)

        # since we are still in trial the mocked today is before the weekday change limit, the change happens today.
        # With the changes happening today, the new contribution value (0) is valid from today. So the previous contribution must end yesterday
        self.assertEqual(
            datetime.date(year=2013, month=1, day=19), contribution.end_date
        )
