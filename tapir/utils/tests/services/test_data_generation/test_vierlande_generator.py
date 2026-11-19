from collections import Counter
from decimal import Decimal
from unittest.mock import patch

import pytest

from tapir.associations.models import AssociationMembershipType
from tapir.configuration.parameter import get_parameter_value
from tapir.core.config import THEME_VIERLANDE
from tapir.pickup_locations.models import PickupLocationDeliveryCharge
from tapir.utils.config import Organization
from tapir.utils.services.test_data_generation.data_generator import DataGenerator
from tapir.utils.services.test_data_generation.vierlande_generator import (
    VierlandeGenerator,
)
from tapir.wirgarten.models import (
    Member,
    MemberPickupLocation,
    PickupLocation,
    Product,
    ProductCapacity,
    Subscription,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    PickupLocationCapabilityFactory,
    PickupLocationFactory,
    ProductTypeFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest

SMALL_VARIANTS = [
    {
        "name": "einfach",
        "base_price": 70,
        "size": 1.0,
        "count": 30,
        "base": True,
        "description": "Der einfache Ernteanteil.",
    },
    {
        "name": "groß",
        "base_price": 140,
        "size": 2.0,
        "count": 2,
        "base": False,
        "description": "Der große Ernteanteil.",
    },
]
SMALL_TOTAL_MEMBER_COUNT = 40
SMALL_SHARE_MEMBER_COUNT = sum(variant["count"] for variant in SMALL_VARIANTS)


class TestVierlandeGenerator(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    @pytest.mark.slow
    def test_generateAll_createsVierlandeProfile(self):
        with (
            patch.object(VierlandeGenerator, "HARVEST_SHARE_VARIANTS", SMALL_VARIANTS),
            patch.object(
                VierlandeGenerator, "TOTAL_MEMBER_COUNT", SMALL_TOTAL_MEMBER_COUNT
            ),
        ):
            DataGenerator.generate_all(Organization.VIERLANDE)

        self.assertGreaterEqual(Member.objects.count(), SMALL_TOTAL_MEMBER_COUNT)

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
            Product.objects.filter(
                name__in=[variant["name"] for variant in SMALL_VARIANTS]
            ).exists()
        )
        self.assertEqual(
            [230],
            list(
                ProductCapacity.objects.filter(product_type__name="Ernteanteile")
                .values_list("capacity", flat=True)
                .distinct()
            ),
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
        self.assertEqual(
            len(VierlandeGenerator.CITY_PICKUP_LOCATION_NAMES),
            PickupLocationDeliveryCharge.objects.filter(
                pickup_location__name__in=VierlandeGenerator.CITY_PICKUP_LOCATION_NAMES
            ).count(),
        )
        self.assertFalse(
            PickupLocationDeliveryCharge.objects.filter(
                pickup_location__name__in=VierlandeGenerator.LAND_PICKUP_LOCATION_NAMES
            ).exists()
        )

        self.assertEqual(SMALL_SHARE_MEMBER_COUNT, Subscription.objects.count())
        self.assertEqual(SMALL_SHARE_MEMBER_COUNT, MemberPickupLocation.objects.count())

    def test_distributeEntriesByCityLand_givenEqualCapacities_splitsByCityShare(
        self,
    ):
        product_type = ProductTypeFactory.create()
        city_locations = [
            PickupLocationFactory.create(name="Stadt A"),
            PickupLocationFactory.create(name="Stadt B"),
        ]
        land_locations = [
            PickupLocationFactory.create(name="Land A"),
            PickupLocationFactory.create(name="Land B"),
        ]
        for location in city_locations + land_locations:
            PickupLocationCapabilityFactory.create(
                pickup_location=location,
                max_capacity=20,
                product_type=product_type,
            )

        assignment = VierlandeGenerator.distribute_entries_by_city_land(
            weighted_entries=[(index, Decimal("1")) for index in range(100)],
            city_locations=city_locations,
            land_locations=land_locations,
        )

        self.assertEqual(100, len(assignment))
        city_assignments = Counter(
            location for location in assignment.values() if location in city_locations
        )
        land_assignments = Counter(
            location for location in assignment.values() if location in land_locations
        )
        self.assertEqual(62, sum(city_assignments.values()))
        self.assertEqual(38, sum(land_assignments.values()))
        self.assertEqual(31, city_assignments[city_locations[0]])
        self.assertEqual(31, city_assignments[city_locations[1]])
        self.assertEqual(19, land_assignments[land_locations[0]])
        self.assertEqual(19, land_assignments[land_locations[1]])

    def test_distributeEntriesByCityLand_withoutLocations_returnsEmptyMapping(self):
        self.assertEqual(
            {},
            VierlandeGenerator.distribute_entries_by_city_land(
                weighted_entries=[(0, Decimal("1"))],
                city_locations=[],
                land_locations=[],
            ),
        )

    def test_distributeEntriesByCityLand_withoutCapacities_assignsAllEntries(self):
        city_locations = [PickupLocationFactory.create(name="Stadt")]
        land_locations = [PickupLocationFactory.create(name="Land")]

        assignment = VierlandeGenerator.distribute_entries_by_city_land(
            weighted_entries=[(index, Decimal("1")) for index in range(10)],
            city_locations=city_locations,
            land_locations=land_locations,
        )

        self.assertEqual(10, len(assignment))
        self.assertEqual(
            {city_locations[0], land_locations[0]}, set(assignment.values())
        )
