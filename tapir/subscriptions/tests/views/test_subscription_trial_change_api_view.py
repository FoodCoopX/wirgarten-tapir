import datetime

from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestSubscriptionTrialChangeApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self) -> None:
        super().setUp()
        self._set_parameter(ParameterKeys.TRIAL_PERIOD_ENABLED, True)
        self._set_parameter(ParameterKeys.TRIAL_PERIOD_DURATION, 4)
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
            trial_disabled=False,
            trial_end_date_override=datetime.date(2026, 3, 22),
        )
        self.client.force_login(admin)

        response = self.client.post(
            reverse("subscriptions:subscription_trial_change"),
            data={"subscription_id": subscription.id, "trial_disabled": True},
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_order_confirmed(response.json())
        subscription.refresh_from_db()
        self.assertTrue(subscription.trial_disabled)
        self.assertIsNone(subscription.trial_end_date_override)

    def test_post_enableTrial_keepsOverrideEmpty(self):
        admin = MemberFactory.create(is_superuser=True)
        subscription = SubscriptionFactory.create(
            trial_disabled=True,
            period__start_date=datetime.date(2026, 1, 1),
        )
        self.client.force_login(admin)

        response = self.client.post(
            reverse("subscriptions:subscription_trial_change"),
            data={"subscription_id": subscription.id, "trial_disabled": False},
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_order_confirmed(response.json())
        subscription.refresh_from_db()
        self.assertFalse(subscription.trial_disabled)
        self.assertIsNone(subscription.trial_end_date_override)

    def test_post_disableTrial_whenNotInTrial_stillDisables(self):
        admin = MemberFactory.create(is_superuser=True)
        mock_timezone(self, datetime.datetime(2026, 7, 3, 12, 0, 0))
        subscription = SubscriptionFactory.create(
            trial_disabled=False,
            period__start_date=datetime.date(2026, 1, 1),
        )
        self.client.force_login(admin)

        response = self.client.post(
            reverse("subscriptions:subscription_trial_change"),
            data={"subscription_id": subscription.id, "trial_disabled": True},
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_order_confirmed(response.json())
        subscription.refresh_from_db()
        self.assertTrue(subscription.trial_disabled)

    def test_post_invalidWeekdayOverride_returnsError(self):
        admin = MemberFactory.create(is_superuser=True)
        subscription = SubscriptionFactory.create(trial_disabled=False)
        self.client.force_login(admin)

        response = self.client.post(
            reverse("subscriptions:subscription_trial_change"),
            data={
                "subscription_id": subscription.id,
                "trial_disabled": False,
                "trial_end_date_override": datetime.date(
                    year=2026, month=4, day=6
                ).isoformat(),
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
        subscription = SubscriptionFactory.create(trial_disabled=True)
        self._set_parameter(ParameterKeys.TRIAL_PERIOD_ENABLED, False)
        self.client.force_login(admin)

        response = self.client.post(
            reverse("subscriptions:subscription_trial_change"),
            data={"subscription_id": subscription.id, "trial_disabled": False},
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertFalse(response_content["order_confirmed"])
        self.assertEqual("Probezeit ist global deaktiviert", response_content["error"])
