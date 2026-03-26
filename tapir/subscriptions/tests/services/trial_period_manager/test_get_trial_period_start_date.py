import datetime
from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.deliveries.services.delivery_date_calculator import DeliveryDateCalculator
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.solidarity_contribution.tests.factories import SolidarityContributionFactory
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.wirgarten.tests.factories import SubscriptionFactory, ProductTypeFactory


class TestGetTrialPeriodStartDate(SimpleTestCase):
    @patch.object(
        MemberPickupLocationGetter,
        "get_member_pickup_location_id_from_cache",
        autospec=True,
    )
    @patch.object(
        DeliveryDateCalculator, "get_next_delivery_date_for_product_type", autospec=True
    )
    def test_getTrialPeriodStartDate_givenContractHasNoProduct_returnsContractStartDate(
        self,
        mock_get_next_delivery_date_for_product_type: Mock,
        mock_get_member_pickup_location_id_from_cache: Mock,
    ):
        contract_start_date = datetime.date(year=2022, month=12, day=16)
        contract = SolidarityContributionFactory.build(start_date=contract_start_date)

        trial_period_start_date = TrialPeriodManager.get_trial_period_start_date(
            contract=contract, cache=Mock()
        )

        self.assertEqual(contract_start_date, trial_period_start_date)

        mock_get_member_pickup_location_id_from_cache.assert_not_called()
        mock_get_next_delivery_date_for_product_type.assert_not_called()

    @patch.object(
        MemberPickupLocationGetter,
        "get_member_pickup_location_id_from_cache",
        autospec=True,
    )
    @patch.object(
        DeliveryDateCalculator, "get_next_delivery_date_for_product_type", autospec=True
    )
    def test_getTrialPeriodStartDate_givenContractHasAProduct_returnMondayOfFirstDeliveryWeek(
        self,
        mock_get_next_delivery_date_for_product_type: Mock,
        mock_get_member_pickup_location_id_from_cache: Mock,
    ):
        contract_start_date = datetime.date(year=2022, month=12, day=16)
        product_type = ProductTypeFactory.build()
        contract = SubscriptionFactory.build(
            mandate_ref__ref="test_ref",
            start_date=contract_start_date,
            member_id="test_member_id",
            product__type=product_type,
        )
        cache = Mock()

        mock_get_member_pickup_location_id_from_cache.return_value = (
            "test_pickup_location_id"
        )
        mock_get_next_delivery_date_for_product_type.return_value = datetime.date(
            year=2022, month=12, day=29
        )  # This is a Thursday

        trial_period_start_date = TrialPeriodManager.get_trial_period_start_date(
            contract=contract, cache=cache
        )

        self.assertEqual(
            datetime.date(year=2022, month=12, day=26), trial_period_start_date
        )

        mock_get_member_pickup_location_id_from_cache.assert_called_once_with(
            member_id="test_member_id", reference_date=contract_start_date, cache=cache
        )
        mock_get_next_delivery_date_for_product_type.assert_called_once_with(
            reference_date=contract_start_date,
            product_type=product_type,
            check_for_weeks_without_delivery=False,
            pickup_location_id="test_pickup_location_id",
            cache=cache,
        )
