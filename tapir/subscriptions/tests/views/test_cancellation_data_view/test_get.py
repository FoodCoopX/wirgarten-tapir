import datetime
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status

from tapir.configuration.models import TapirParameter
from tapir.coop.services.membership_cancellation_manager import (
    MembershipCancellationManager,
)
from tapir.subscriptions.services.product_cancellation_data_builder import (
    ProductCancellationDataBuilder,
)
from tapir.wirgarten.constants import ODD_WEEKS
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestGet(TapirIntegrationTest):
    maxDiff = 2000

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self) -> None:
        super().setUp()
        self.now = mock_timezone(self, datetime.datetime(year=2023, month=2, day=15))

    def test_get_normalMemberAsksForOwnData_returnsCorrectData(
        self,
    ):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)
        subscriptions = SubscriptionFactory.create_batch(size=3, member=member)

        url = reverse("subscriptions:cancellation_data")
        response = self.client.get(f"{url}?member_id={member.id}")

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        returned_product_ids = [
            subscribed_product["product"]["id"]
            for subscribed_product in response_content["subscribed_products"]
        ]
        expected_product_ids = [
            subscription.product.id for subscription in subscriptions
        ]
        self.assertCountEqual(expected_product_ids, returned_product_ids)
        self.assertFalse(response_content["show_trial_period_help_text"])

    def test_get_memberHasSubscriptionWithBiweeklyDeliveryCycle_showTrialPeriodHelpTextIsTrue(
        self,
    ):
        TapirParameter.objects.filter(key=ParameterKeys.TRIAL_PERIOD_DURATION).update(
            value=7
        )
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)
        SubscriptionFactory.create(
            member=member,
            product__type__delivery_cycle=ODD_WEEKS[0],
            start_date=self.now.date().replace(month=1, day=1),
        )

        url = reverse("subscriptions:cancellation_data")
        response = self.client.get(f"{url}?member_id={member.id}")

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertTrue(response_content["show_trial_period_help_text"])
        self.assertEqual(7, response_content["trial_period_duration"])
        self.assertTrue(response_content["trial_period_is_flexible"])

    def test_get_trialPeriodDisabled_showTrialPeriodHelpTextIsFalse(
        self,
    ):
        TapirParameter.objects.filter(key=ParameterKeys.TRIAL_PERIOD_ENABLED).update(
            value=False
        )
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)
        SubscriptionFactory.create(
            member=member, product__type__delivery_cycle=ODD_WEEKS[0]
        )

        url = reverse("subscriptions:cancellation_data")
        response = self.client.get(f"{url}?member_id={member.id}")

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertFalse(response_content["show_trial_period_help_text"])

    def test_get_trialPeriodIsNotFlexible_returnsCorrectData(
        self,
    ):
        TapirParameter.objects.filter(
            key=ParameterKeys.TRIAL_PERIOD_CAN_BE_CANCELLED_BEFORE_END
        ).update(value=False)
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)
        SubscriptionFactory.create(
            member=member, product__type__delivery_cycle=ODD_WEEKS[0]
        )

        url = reverse("subscriptions:cancellation_data")
        response = self.client.get(f"{url}?member_id={member.id}")

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertFalse(response_content["trial_period_is_flexible"])

    def test_get_normalMemberAsksForDataOfOtherMember_returnsStatus403(
        self,
    ):
        user = MemberFactory.create(is_superuser=False)
        other_member = MemberFactory.create()
        self.client.force_login(user)

        url = reverse("subscriptions:cancellation_data")
        response = self.client.get(f"{url}?member_id={other_member.id}")

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    @patch.object(ProductCancellationDataBuilder, "build_data_for_all_products")
    @patch.object(MembershipCancellationManager, "can_member_cancel_coop_membership")
    def test_get_adminAsksForDataOfOtherMember_returnsStatus200(self, *_):
        user = MemberFactory.create(is_superuser=True)
        other_member = MemberFactory.create()
        self.client.force_login(user)

        url = reverse("subscriptions:cancellation_data")
        response = self.client.get(f"{url}?member_id={other_member.id}")

        self.assertStatusCode(response, status.HTTP_200_OK)
