from django.urls import reverse

from tapir.configuration.models import TapirParameter
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestWaitingListCategoriesView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_WAITING_LIST_CATEGORIES
        ).update(value="cat1,cat2")

    def test_waitingListView_loggedInAsNormalUser_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        response = self.client.get(reverse("waiting_list:categories"))

        self.assertEqual(response.status_code, 403)

    def test_waitingListView_loggedInAsAdmin_returnsCategories(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        response = self.client.get(reverse("waiting_list:categories"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(["cat1", "cat2"], response.json())
