from unittest.mock import patch, Mock, ANY, call

from django.urls import reverse
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.configuration.models import TapirParameter
from tapir.coop.services.membership_cancellation_manager import (
    MembershipCancellationManager,
)
from tapir.subscriptions.services.subscription_cancellation_manager import (
    SubscriptionCancellationManager,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tapirmail import Events
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    SubscriptionFactory,
    NOW,
    GrowingPeriodFactory,
    TODAY,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone
from tapir.wirgarten.utils import format_date, format_subscription_list_html


class TestCancelSubscriptionsPostView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()

    def setUp(self):
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

        url = reverse("subscriptions:cancel_subscriptions")
        product_ids_as_parameters = "&".join(
            [f"product_ids={subscription.product_id}" for subscription in subscriptions]
        )
        url = f"{url}?member_id={target.id}&{product_ids_as_parameters}&cancel_coop_membership=false"
        response = self.client.post(url)

        self.assertStatusCode(response, 403)
        mock_cancel_subscriptions.assert_not_called()
        mock_cancel_coop_membership.assert_not_called()

    @patch.object(SubscriptionCancellationManager, "cancel_subscriptions")
    def test_post_memberCancelsOwnSubscriptions_returns200(
        self, mock_cancel_subscriptions: Mock
    ):
        member = MemberFactory.create()
        self.client.force_login(member)

        subscriptions = SubscriptionFactory.create_batch(size=3, member=member)
        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=subscriptions[0].product.type_id
        )

        url = reverse("subscriptions:cancel_subscriptions")
        product_ids_as_parameters = "&".join(
            [f"product_ids={subscription.product_id}" for subscription in subscriptions]
        )
        url = f"{url}?member_id={member.id}&{product_ids_as_parameters}&cancel_coop_membership=false"
        response = self.client.post(url)

        self.assertStatusCode(response, 200)
        self.assertEqual(3, mock_cancel_subscriptions.call_count)

    @patch.object(SubscriptionCancellationManager, "cancel_subscriptions")
    def test_post_adminCancelsSubscriptionOfOtherMember_returns200(
        self, mock_cancel_subscriptions: Mock
    ):
        actor = MemberFactory.create(is_superuser=True)
        target = MemberFactory.create()
        self.client.force_login(actor)

        subscriptions = SubscriptionFactory.create_batch(size=3, member=target)
        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=subscriptions[0].product.type_id
        )

        url = reverse("subscriptions:cancel_subscriptions")
        product_ids_as_parameters = "&".join(
            [f"product_ids={subscription.product_id}" for subscription in subscriptions]
        )
        url = f"{url}?member_id={target.id}&{product_ids_as_parameters}&cancel_coop_membership=false"
        response = self.client.post(url)

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

        url = reverse("subscriptions:cancel_subscriptions")
        product_ids_as_parameters = "&".join(
            [f"product_ids={subscription.product_id}" for subscription in subscriptions]
        )
        url = f"{url}?member_id={member.id}&{product_ids_as_parameters}&cancel_coop_membership=true"
        response = self.client.post(url)

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

        subscriptions = SubscriptionFactory.create_batch(size=3, member=member)
        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=subscriptions[0].product.type_id
        )

        url = reverse("subscriptions:cancel_subscriptions")
        product_ids_as_parameters = "&".join(
            [f"product_ids={subscription.product_id}" for subscription in subscriptions]
        )
        url = f"{url}?member_id={member.id}&{product_ids_as_parameters}&cancel_coop_membership=true"
        response = self.client.post(url)

        self.assertStatusCode(response, 200)
        self.assertEqual(0, len(response.json()["errors"]))
        self.assertEqual(3, mock_cancel_subscriptions.call_count)
        mock_cancel_coop_membership.assert_called_once_with(member, cache=ANY)

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

        subscriptions = SubscriptionFactory.create_batch(size=3, member=member)
        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=subscriptions[0].product.type_id
        )

        url = reverse("subscriptions:cancel_subscriptions")
        product_ids_as_parameters = "&".join(
            [f"product_ids={subscription.product_id}" for subscription in subscriptions]
        )
        url = f"{url}?member_id={member.id}&{product_ids_as_parameters}&cancel_coop_membership=false"
        response = self.client.post(url)

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

        subscriptions = SubscriptionFactory.create_batch(size=3, member=member)
        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=subscriptions[0].product.type_id
        )
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_ADDITIONAL_PRODUCT_ALLOWED_WITHOUT_BASE_PRODUCT
        ).update(value=False)

        url = reverse("subscriptions:cancel_subscriptions")
        url = f"{url}?member_id={member.id}&product_ids={subscriptions[0].product_id}&cancel_coop_membership=false"
        response = self.client.post(url)

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

        subscriptions = SubscriptionFactory.create_batch(size=3, member=member)
        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=subscriptions[0].product.type_id
        )
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_ADDITIONAL_PRODUCT_ALLOWED_WITHOUT_BASE_PRODUCT
        ).update(value=True)

        url = reverse("subscriptions:cancel_subscriptions")
        url = f"{url}?member_id={member.id}&product_ids={subscriptions[0].product_id}&cancel_coop_membership=false"
        response = self.client.post(url)

        self.assertStatusCode(response, 200)
        self.assertEqual(0, len(response.json()["errors"]))
        mock_cancel_subscriptions.assert_called_once_with(
            subscriptions[0].product, member, cache=ANY
        )

    @patch.object(TransactionalTrigger, "fire_action")
    def test_post_default_sendsMailTrigger(
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

        url = reverse("subscriptions:cancel_subscriptions")
        product_ids_as_parameters = "&".join(
            [
                f"product_ids={subscription.product_id}"
                for subscription in subscriptions[:2]
            ]
        )
        url = f"{url}?member_id={member.id}&{product_ids_as_parameters}&cancel_coop_membership=false"
        response = self.client.post(url)

        self.assertStatusCode(response, 200)
        self.assertEqual(0, len(response.json()["errors"]))
        self.assertEqual(2, mock_fire_action.call_count)
        mock_fire_action.assert_has_calls(
            [
                call(
                    TransactionalTriggerData(
                        key=Events.CONTRACT_CANCELLED,
                        recipient_id_in_base_queryset=member.id,
                        token_data={
                            "contract_list": format_subscription_list_html(
                                [subscription]
                            ),
                            "contract_end_date": format_date(growing_period.end_date),
                        },
                    )
                )
                for subscription in subscriptions[:2]
            ],
            any_order=True,
        )
