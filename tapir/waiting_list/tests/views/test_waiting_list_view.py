from django.urls import reverse

from tapir.configuration.models import TapirParameter
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, ProductFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestWaitingListView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        product = ProductFactory.create()
        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=product.type_id
        )

    def test_waitingListView_loggedInAsNormalUser_redirectsToUserProfile(self):
        member = MemberFactory.create()
        self.client.force_login(member)

        response = self.client.get(reverse("waiting_list:list"))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response=response,
            expected_url=reverse("wirgarten:member_detail", args=[member.id]),
        )

    def test_waitingListView_loggedInAsAdmin_returns200(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        response = self.client.get(reverse("waiting_list:list"))

        self.assertEqual(response.status_code, 200)
