import datetime
from unittest.mock import Mock

from tapir.pickup_locations.services.pickup_location_capacity_mode_share_checker import (
    PickupLocationCapacityModeShareChecker,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests import factories
from tapir.wirgarten.tests.factories import (
    ProductFactory,
    MemberFactory,
    SubscriptionFactory,
    ProductTypeFactory,
    ProductPriceFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestGetCapacityUsedByMemberBeforeChanges(TapirIntegrationTest):
    def test_getCapacityUsedByMemberBeforeChanges_memberIsNone_returnsZero(self):
        # If the member doesn't exist yet, or if it is registered at another pickup location at the given date,
        # then it is not currently occupying any space at the given pickup location
        self.assertEqual(
            0,
            PickupLocationCapacityModeShareChecker.get_capacity_used_by_member_before_changes(
                None, Mock(), Mock(), {}
            ),
        )

    def test_getCapacityUsedByMemberBeforeChanges_default_otherMemberNotCounted(self):
        ParameterDefinitions().import_definitions()
        product_type = ProductTypeFactory.create()
        product_s = ProductFactory(name="S", type=product_type)
        product_m = ProductFactory(name="M", type=product_type)
        product_l = ProductFactory(name="L", type=product_type)
        ProductPriceFactory.create(
            product=product_s,
            size=2,
            valid_from=factories.NOW - datetime.timedelta(days=1),
        )
        ProductPriceFactory.create(
            product=product_m,
            size=3,
            valid_from=factories.NOW - datetime.timedelta(days=1),
        )
        ProductPriceFactory.create(
            product=product_l,
            size=5,
            valid_from=factories.NOW - datetime.timedelta(days=1),
        )

        member_1 = MemberFactory.create()
        SubscriptionFactory.create(
            member=member_1,
            product=product_s,
            quantity=3,
            start_date=factories.NOW - datetime.timedelta(days=1),
        )
        member_2 = MemberFactory.create()
        SubscriptionFactory.create(
            member=member_2,
            product=product_m,
            quantity=2,
            start_date=factories.NOW - datetime.timedelta(days=1),
        )

        mock_timezone(self, factories.NOW)

        self.assertEqual(
            6,
            PickupLocationCapacityModeShareChecker.get_capacity_used_by_member_before_changes(
                member_1, factories.NOW, product_type, {}
            ),
        )

    def test_getCapacityUsedByMemberBeforeChanges_default_inactiveSubscriptionNotCounted(
        self,
    ):
        ParameterDefinitions().import_definitions()
        product_type = ProductTypeFactory.create()
        product_s = ProductFactory(name="S", type=product_type)
        product_m = ProductFactory(name="M", type=product_type)
        product_l = ProductFactory(name="L", type=product_type)
        ProductPriceFactory.create(
            product=product_s,
            size=2,
            valid_from=factories.NOW - datetime.timedelta(days=1),
        )
        ProductPriceFactory.create(
            product=product_m,
            size=3,
            valid_from=factories.NOW - datetime.timedelta(days=1),
        )
        ProductPriceFactory.create(
            product=product_l,
            size=5,
            valid_from=factories.NOW - datetime.timedelta(days=1),
        )

        member_1 = MemberFactory.create()
        SubscriptionFactory.create(
            member=member_1,
            product=product_s,
            quantity=3,
            start_date=factories.NOW + datetime.timedelta(days=1),
        )
        SubscriptionFactory.create(
            member=member_1,
            product=product_l,
            quantity=2,
            start_date=factories.NOW - datetime.timedelta(days=1),
        )

        mock_timezone(self, factories.NOW)

        self.assertEqual(
            10,
            PickupLocationCapacityModeShareChecker.get_capacity_used_by_member_before_changes(
                member_1, factories.NOW, product_type, {}
            ),
        )
