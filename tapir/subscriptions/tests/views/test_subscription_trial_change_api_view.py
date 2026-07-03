import datetime

from django.urls import reverse
from rest_framework import status

from tapir.configuration.models import TapirParameter
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestSubscriptionTrialChangeApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(key=ParameterKeys.TRIAL_PERIOD_ENABLED).update(
            value=True
        )
        TapirParameter.objects.filter(key=ParameterKeys.TRIAL_PERIOD_DURATION).update(
            value=4
        )

    def setUp(self) -> None:
        super().setUp()
        mock_timezone(self, datetime.datetime(2026, 3, 15, 12, 0, 0))

    def test_post_normalMember_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        subscription = SubscriptionFactory.create(member=member, trial_disabled=False)
        self.client.force_login(member)

        response = self.client.post(
            reverse("subscriptions:subscription_trial_change"),
            data={"subscription_id": subscription.id, "trial_disabled": True},
        )

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        subscription.refresh_from_db()
        self.assertFalse(subscription.trial_disabled)

    def test_post_disableTrial_setsTrialDisabledAndClearsOverride(self):
        admin = MemberFactory.create(is_superuser=True)
        subscription = SubscriptionFactory.create(
            member=MemberFactory.create(),
            trial_disabled=False,
            trial_end_date_override=datetime.date(2026, 3, 22),
        )
        self.client.force_login(admin)

        response = self.client.post(
            reverse("subscriptions:subscription_trial_change"),
            data={"subscription_id": subscription.id, "trial_disabled": True},
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertTrue(response.json()["order_confirmed"])
        subscription.refresh_from_db()
        self.assertTrue(subscription.trial_disabled)
        self.assertIsNone(subscription.trial_end_date_override)

    def test_post_enableExpiredTrial_setsTrialEndDateOverride(self):
        admin = MemberFactory.create(is_superuser=True)
        period = GrowingPeriodFactory.create(
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 12, 31),
        )
        subscription = SubscriptionFactory.create(
            member=MemberFactory.create(),
            trial_disabled=True,
            period=period,
            start_date=period.start_date,
            end_date=period.end_date,
        )
        cache = {}
        expected_override = (
            TrialPeriodManager.get_default_trial_end_date_for_admin_enable(
                subscription, cache=cache
            )
        )
        self.client.force_login(admin)

        response = self.client.post(
            reverse("subscriptions:subscription_trial_change"),
            data={"subscription_id": subscription.id, "trial_disabled": False},
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertTrue(response.json()["order_confirmed"])
        subscription.refresh_from_db()
        self.assertFalse(subscription.trial_disabled)
        self.assertEqual(expected_override, subscription.trial_end_date_override)

    def test_post_invalidWeekdayOverride_returnsError(self):
        admin = MemberFactory.create(is_superuser=True)
        subscription = SubscriptionFactory.create(
            member=MemberFactory.create(),
            trial_disabled=False,
        )
        self.client.force_login(admin)

        response = self.client.post(
            reverse("subscriptions:subscription_trial_change"),
            data={
                "subscription_id": subscription.id,
                "trial_disabled": False,
                "trial_end_date_override": datetime.date(2026, 4, 6).isoformat(),
            },
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertFalse(response_content["order_confirmed"])
        self.assertEqual(
            "Das Probezeit-Enddatum muss ein Sonntag sein",
            response_content["error"],
        )

    def test_post_enableTrialWhenGloballyDisabled_returnsError(self):
        admin = MemberFactory.create(is_superuser=True)
        subscription = SubscriptionFactory.create(
            member=MemberFactory.create(),
            trial_disabled=True,
        )
        TapirParameter.objects.filter(key=ParameterKeys.TRIAL_PERIOD_ENABLED).update(
            value=False
        )
        self.client.force_login(admin)

        response = self.client.post(
            reverse("subscriptions:subscription_trial_change"),
            data={"subscription_id": subscription.id, "trial_disabled": False},
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertFalse(response_content["order_confirmed"])
        self.assertEqual("Probezeit ist global deaktiviert", response_content["error"])

        TapirParameter.objects.filter(key=ParameterKeys.TRIAL_PERIOD_ENABLED).update(
            value=True
        )

    def test_retrieve_includesTrialFields(self):
        admin = MemberFactory.create(is_superuser=True)
        subscription = SubscriptionFactory.create(
            member=MemberFactory.create(),
            trial_disabled=False,
        )
        self.client.force_login(admin)

        response = self.client.get(
            reverse("subscriptions:subscriptions-detail", args=[subscription.id]),
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertIn("is_in_trial", response_content)
        self.assertIn("default_trial_end_date", response_content)
        self.assertIn("effective_trial_end_date", response_content)
