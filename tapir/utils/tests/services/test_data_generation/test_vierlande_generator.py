from unittest.mock import patch

from tapir.associations.models import AssociationMembershipType
from tapir.bidding_round.config import ACTIVE
from tapir.bidding_round.models import Bid, BiddingRound, BiddingRoundProductPrice
from tapir.configuration.parameter import get_parameter_value
from tapir.core.config import THEME_VIERLANDE
from tapir.utils.config import Organization
from tapir.utils.services.test_data_generation.data_generator import DataGenerator
from tapir.utils.services.test_data_generation.product_generator import ProductGenerator
from tapir.utils.services.test_data_generation.vierlande_generator import (
    VierlandeGenerator,
)
from tapir.wirgarten.models import Member, PickupLocation
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest

SMALL_VARIANTS = [
    {
        "name": "einfach",
        "base_price": 70,
        "size": 1.0,
        "count": 30,
        "base": True,
        "description": "Der einfache Ernteanteil.",
        "image_file": "harvest_share_small.png",
    },
    {
        "name": "groß",
        "base_price": 140,
        "size": 2.0,
        "count": 2,
        "base": False,
        "description": "Der große Ernteanteil.",
        "image_file": "harvest_share_medium.png",
    },
]
SMALL_CAPACITIES = {
    "Ernteanteile": 40,
    "Hühneranteile": 40,
    "Hofpunkt": 40,
}


class TestVierlandeGenerator(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_generateAll_createsVierlandeProfile(self):
        with (
            patch.object(VierlandeGenerator, "HARVEST_SHARE_VARIANTS", SMALL_VARIANTS),
            patch.object(VierlandeGenerator, "NUMBER_OF_SHARE_MEMBERS", 32),
            patch.object(VierlandeGenerator, "TOTAL_MEMBER_COUNT", 40),
            patch.object(
                ProductGenerator,
                "REALISTIC_CAPACITIES_BY_PRODUCT_TYPE_NAME",
                SMALL_CAPACITIES,
            ),
        ):
            DataGenerator.generate_all(Organization.VIERLANDE)

        self.assertGreaterEqual(Member.objects.count(), 40)
        self.assertFalse(Member.objects.exclude(preferred_language="de").exists())

        self.assertEqual(
            THEME_VIERLANDE,
            get_parameter_value(ParameterKeys.ORGANISATION_THEME, cache={}),
        )
        self.assertTrue(
            AssociationMembershipType.objects.filter(
                name=VierlandeGenerator.MEMBERSHIP_TYPE_ORDENTLICH
            ).exists()
        )
        self.assertTrue(
            AssociationMembershipType.objects.filter(
                name=VierlandeGenerator.MEMBERSHIP_TYPE_FOERDER
            ).exists()
        )

        self.assertTrue(
            PickupLocation.objects.filter(
                name__in=VierlandeGenerator.CITY_PICKUP_LOCATION_NAMES
            ).exists()
        )
        self.assertTrue(
            PickupLocation.objects.filter(
                name__in=VierlandeGenerator.LAND_PICKUP_LOCATION_NAMES
            ).exists()
        )

        rounds = BiddingRound.objects.all()
        self.assertEqual(4, rounds.count())
        self.assertEqual(1, rounds.filter(status=ACTIVE).count())
        self.assertTrue(BiddingRoundProductPrice.objects.exists())
        self.assertTrue(Bid.objects.exists())
