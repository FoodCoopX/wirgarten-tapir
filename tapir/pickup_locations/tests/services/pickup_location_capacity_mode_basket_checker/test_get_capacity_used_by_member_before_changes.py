import datetime
from unittest.mock import Mock

from tapir.configuration.models import TapirParameter
from tapir.pickup_locations.models import ProductBasketSizeEquivalence
from tapir.pickup_locations.services.pickup_location_capacity_mode_basket_checker import (
    PickupLocationCapacityModeBasketChecker,
)
from tapir.wirgarten.parameters import ParameterDefinitions, Parameter
from tapir.wirgarten.tests import factories
from tapir.wirgarten.tests.factories import (
    ProductFactory,
    MemberFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestGetCapacityUsedByMemberBeforeChanges(TapirIntegrationTest):
    def test_getCapacityUsedByMemberBeforeChanges_memberIsNone_returnsZero(self):
        # If the member doesn't exist yet, or if it is registered at another pickup location at the given date,
        # then it is not currently occupying any space at the given pickup location
        self.assertEqual(
            0,
            PickupLocationCapacityModeBasketChecker.get_capacity_used_by_member_before_changes(
                None, Mock(), Mock()
            ),
        )

    def test_getCapacityUsedByMemberBeforeChanges_default_otherMemberNotCounted(self):
        ParameterDefinitions().import_definitions()
        TapirParameter.objects.filter(key=Parameter.PICKING_BASKET_SIZES).update(
            value="small;medium"
        )
        product_s = ProductFactory(name="S")
        product_m = ProductFactory(name="M")
        product_l = ProductFactory(name="L")
        ProductBasketSizeEquivalence.objects.bulk_create(
            [
                ProductBasketSizeEquivalence(
                    basket_size_name="small", product=product_s, quantity=1
                ),
                ProductBasketSizeEquivalence(
                    basket_size_name="medium", product=product_s, quantity=0
                ),
                ProductBasketSizeEquivalence(
                    basket_size_name="medium", product=product_m, quantity=1
                ),
                ProductBasketSizeEquivalence(
                    basket_size_name="small", product=product_l, quantity=1
                ),
                ProductBasketSizeEquivalence(
                    basket_size_name="medium", product=product_l, quantity=1
                ),
            ]
        )

        member_1 = MemberFactory.create()
        SubscriptionFactory.create(member=member_1, product=product_s, quantity=3)
        member_2 = MemberFactory.create()
        SubscriptionFactory.create(member=member_2, product=product_m, quantity=2)

        mock_timezone(self, factories.NOW)

        self.assertEqual(
            3,
            PickupLocationCapacityModeBasketChecker.get_capacity_used_by_member_before_changes(
                member_1, factories.NOW, "small"
            ),
        )
        self.assertEqual(
            0,
            PickupLocationCapacityModeBasketChecker.get_capacity_used_by_member_before_changes(
                member_1, factories.NOW, "medium"
            ),
        )

    def test_getCapacityUsedByMemberBeforeChanges_default_inactiveSubscriptioNotCount(
        self,
    ):
        ParameterDefinitions().import_definitions()
        TapirParameter.objects.filter(key=Parameter.PICKING_BASKET_SIZES).update(
            value="small;medium"
        )
        product_s = ProductFactory(name="S")
        product_m = ProductFactory(name="M")
        product_l = ProductFactory(name="L")
        ProductBasketSizeEquivalence.objects.bulk_create(
            [
                ProductBasketSizeEquivalence(
                    basket_size_name="small", product=product_s, quantity=1
                ),
                ProductBasketSizeEquivalence(
                    basket_size_name="medium", product=product_s, quantity=0
                ),
                ProductBasketSizeEquivalence(
                    basket_size_name="medium", product=product_m, quantity=1
                ),
                ProductBasketSizeEquivalence(
                    basket_size_name="small", product=product_l, quantity=1
                ),
                ProductBasketSizeEquivalence(
                    basket_size_name="medium", product=product_l, quantity=1
                ),
            ]
        )

        member_1 = MemberFactory.create()
        SubscriptionFactory.create(member=member_1, product=product_s, quantity=3)
        SubscriptionFactory.create(
            member=member_1,
            product=product_m,
            quantity=2,
            start_date=factories.NOW + datetime.timedelta(days=1),
        )

        mock_timezone(self, factories.NOW)

        self.assertEqual(
            3,
            PickupLocationCapacityModeBasketChecker.get_capacity_used_by_member_before_changes(
                member_1, factories.NOW, "small"
            ),
        )
        self.assertEqual(
            0,
            PickupLocationCapacityModeBasketChecker.get_capacity_used_by_member_before_changes(
                member_1, factories.NOW, "medium"
            ),
        )
