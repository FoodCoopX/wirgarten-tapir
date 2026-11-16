from django.urls import reverse
from rest_framework import status

from tapir.bidding_round.tests.helpers import create_open_round
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestBiddingRoundFeatureFlagGating(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.client.force_login(MemberFactory.create(is_superuser=True))

    def test_masterFlagOff_adminEndpoint_returns404(self):
        self._set_parameter(ParameterKeys.BIDDING_ROUND_ENABLED, False)

        response = self.client.get(reverse("bidding_rounds:round_list_create"))

        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)

    def test_masterFlagOn_adminEndpoint_reachable(self):
        self._set_parameter(ParameterKeys.BIDDING_ROUND_ENABLED, True)

        response = self.client.get(reverse("bidding_rounds:round_list_create"))

        self.assertStatusCode(response, status.HTTP_200_OK)

    def test_masterFlagOff_publicData_returns404(self):
        self._set_parameter(ParameterKeys.BIDDING_ROUND_ENABLED, False)

        response = self.client.get(reverse("bidding_rounds:public_data"))

        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)

    def test_urlFlagOff_publicData_returns404(self):
        self._set_parameter(ParameterKeys.BIDDING_ROUND_ENABLED, True)
        self._set_parameter(ParameterKeys.BIDDING_ROUND_URL_ENABLED, False)

        response = self.client.get(reverse("bidding_rounds:public_data"))

        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)

    def test_urlFlagOff_adminEndpoint_staysReachable(self):
        self._set_parameter(ParameterKeys.BIDDING_ROUND_ENABLED, True)
        self._set_parameter(ParameterKeys.BIDDING_ROUND_URL_ENABLED, False)

        response = self.client.get(reverse("bidding_rounds:round_list_create"))

        self.assertStatusCode(response, status.HTTP_200_OK)

    def test_urlFlagOff_publicResults_returns404(self):
        self._set_parameter(ParameterKeys.BIDDING_ROUND_ENABLED, True)
        self._set_parameter(ParameterKeys.BIDDING_ROUND_URL_ENABLED, False)
        bidding_round = create_open_round()

        response = self.client.get(
            reverse("bidding_rounds:public_results", args=[bidding_round.id])
        )

        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)

    def test_urlFlagOff_memberBid_returns404(self):
        self._set_parameter(ParameterKeys.BIDDING_ROUND_ENABLED, True)
        self._set_parameter(ParameterKeys.BIDDING_ROUND_URL_ENABLED, False)
        bidding_round = create_open_round()

        response = self.client.get(
            reverse("bidding_rounds:member_bid", args=[bidding_round.id])
        )

        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)
