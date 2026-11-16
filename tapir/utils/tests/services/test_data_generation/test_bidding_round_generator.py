from unittest.mock import patch

from tapir.bidding_round.config import BIDDING_ROUND_STATUS_ACTIVE
from tapir.bidding_round.models import Bid, BiddingRound, BiddingRoundProductPrice
from tapir.utils.config import Organization
from tapir.utils.services.test_data_generation.data_generator import DataGenerator
from tapir.utils.services.test_data_generation.user_generator import UserGenerator
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@patch.object(UserGenerator, "get_user_count", return_value=25, autospec=True)
class TestBiddingRoundGenerator(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_generateAll_createsActiveRoundWithBids(self, _count):
        DataGenerator.generate_all(Organization.BIOTOP)

        rounds = BiddingRound.objects.filter(status=BIDDING_ROUND_STATUS_ACTIVE)
        self.assertEqual(1, rounds.count())
        self.assertTrue(BiddingRoundProductPrice.objects.exists())
        self.assertTrue(Bid.objects.exists())
