from django.urls import reverse
from rest_framework import status

from tapir.configuration.models import TapirParameter
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


def _set_flag(key, value):
    TapirParameter.objects.filter(key=key).update(value=str(value).lower())


class BiddingRoundPageViewTestBase(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)


class TestBiddingRoundView(BiddingRoundPageViewTestBase):
    def test_pageDisabled_returns404(self):
        _set_flag(ParameterKeys.BIDDING_ROUND_ENABLED, False)
        response = self.client.get(reverse("bidding_rounds:bidding_rounds"))
        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)

    def test_page_urlFlagOff_returns404(self):
        _set_flag(ParameterKeys.BIDDING_ROUND_ENABLED, True)
        _set_flag(ParameterKeys.BIDDING_ROUND_URL_ENABLED, False)
        response = self.client.get(reverse("bidding_rounds:bidding_rounds"))
        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)

    def test_pageEnabled_returns200(self):
        _set_flag(ParameterKeys.BIDDING_ROUND_ENABLED, True)
        _set_flag(ParameterKeys.BIDDING_ROUND_URL_ENABLED, True)
        response = self.client.get(reverse("bidding_rounds:bidding_rounds"))
        self.assertStatusCode(response, status.HTTP_200_OK)


class TestBiddingRoundConfigView(BiddingRoundPageViewTestBase):
    def test_adminPageDisabled_returns404(self):
        _set_flag(ParameterKeys.BIDDING_ROUND_ENABLED, False)
        response = self.client.get(reverse("bidding_rounds:bidding_rounds_config"))
        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)

    def test_adminPageEnabled_anonymous_redirectsToLogin(self):
        _set_flag(ParameterKeys.BIDDING_ROUND_ENABLED, True)
        response = self.client.get(reverse("bidding_rounds:bidding_rounds_config"))
        self.assertStatusCode(response, status.HTTP_302_FOUND)

    def test_adminPageEnabled_nonAdmin_returns403(self):
        _set_flag(ParameterKeys.BIDDING_ROUND_ENABLED, True)
        self.client.force_login(MemberFactory.create())
        response = self.client.get(reverse("bidding_rounds:bidding_rounds_config"))
        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_adminPageEnabled_admin_returns200(self):
        _set_flag(ParameterKeys.BIDDING_ROUND_ENABLED, True)
        self.client.force_login(MemberFactory.create(is_superuser=True))
        response = self.client.get(reverse("bidding_rounds:bidding_rounds_config"))
        self.assertStatusCode(response, status.HTTP_200_OK)
