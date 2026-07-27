from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestSubscriptionsRetrieveTrialFields(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_retrieve_includesTrialFields(self):
        admin = MemberFactory.create(is_superuser=True)
        subscription = SubscriptionFactory.create(trial_disabled=False)
        self.client.force_login(admin)

        response = self.client.get(
            reverse("subscriptions:subscriptions-detail", args=[subscription.id]),
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertIn("is_in_trial", response_content)
        self.assertIn("default_trial_end_date", response_content)
        self.assertIn("effective_trial_end_date", response_content)
