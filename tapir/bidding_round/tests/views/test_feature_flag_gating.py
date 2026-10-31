from django.urls import reverse
from rest_framework import status

from tapir.bidding_round.tests.helpers import create_open_round
from tapir.configuration.models import TapirParameter
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

    @classmethod
    def _set_flag(cls, key, value):
        TapirParameter.objects.filter(key=key).update(
            value="true" if value else "false"
        )

    def test_masterFlagOff_adminEndpoint_returns404(self):
        self._set_flag(ParameterKeys.BIDDING_ROUND_ENABLED, False)

        response = self.client.get(reverse("bidding_rounds:round_list_create"))

        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)

    def test_masterFlagOn_adminEndpoint_reachable(self):
        self._set_flag(ParameterKeys.BIDDING_ROUND_ENABLED, True)

        response = self.client.get(reverse("bidding_rounds:round_list_create"))

        self.assertStatusCode(response, status.HTTP_200_OK)

    def test_masterFlagOff_publicData_returns404(self):
        self._set_flag(ParameterKeys.BIDDING_ROUND_ENABLED, False)

        response = self.client.get(reverse("bidding_rounds:public_data"))

        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)

    def test_urlFlagOff_publicData_returns404(self):
        self._set_flag(ParameterKeys.BIDDING_ROUND_ENABLED, True)
        self._set_flag(ParameterKeys.BIDDING_ROUND_URL_ENABLED, False)

        response = self.client.get(reverse("bidding_rounds:public_data"))

        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)

    def test_urlFlagOff_adminEndpoint_staysReachable(self):
        self._set_flag(ParameterKeys.BIDDING_ROUND_ENABLED, True)
        self._set_flag(ParameterKeys.BIDDING_ROUND_URL_ENABLED, False)

        response = self.client.get(reverse("bidding_rounds:round_list_create"))

        self.assertStatusCode(response, status.HTTP_200_OK)

    def test_urlFlagOff_memberBid_returns404(self):
        self._set_flag(ParameterKeys.BIDDING_ROUND_ENABLED, True)
        self._set_flag(ParameterKeys.BIDDING_ROUND_URL_ENABLED, False)
        round_ = create_open_round()

        response = self.client.get(
            reverse("bidding_rounds:member_bid", args=[round_.id])
        )

        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)

    def test_masterFlagOff_capacityCheck_returns404(self):
        self._set_flag(ParameterKeys.BIDDING_ROUND_ENABLED, False)
        round_ = create_open_round()

        response = self.client.post(
            reverse("bidding_rounds:capacity_check", args=[round_.id]),
            data={"items": []},
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)

    def test_capacityCheck_notAuthenticated_returns403(self):
        self._set_flag(ParameterKeys.BIDDING_ROUND_ENABLED, True)
        round_ = create_open_round()
        self.client.logout()

        response = self.client.post(
            reverse("bidding_rounds:capacity_check", args=[round_.id]),
            data={"items": []},
            content_type="application/json",
        )

        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )
