from django.urls import reverse

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGrowingPeriodViewSet(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_growingPeriodViewSet_loggedInAsNormalUser_returns403(self):
        member = MemberFactory()
        self.client.force_login(member)

        response = self.client.get(reverse("Deliveries:growing_periods-list"))
        self.assertStatusCode(response, 403)

    def test_growingPeriodViewSet_loggedInAsAdmin_returns200(self):
        member = MemberFactory(is_superuser=True)
        self.client.force_login(member)

        response = self.client.get(reverse("Deliveries:growing_periods-list"))
        self.assertStatusCode(response, 200)
