import datetime
from unittest.mock import patch, Mock, call

from django.test import SimpleTestCase

from tapir.deliveries.services.delivery_date_calculator import DeliveryDateCalculator
from tapir.payments.services.month_payment_builder import MonthPaymentBuilder
from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.wirgarten.tests.factories import SubscriptionFactory


class TestGetNumberOfDeliveriesInMonth(SimpleTestCase):
    @patch.object(
        MemberPickupLocationService, "get_member_pickup_location_id_from_cache"
    )
    @patch.object(
        DeliveryDateCalculator,
        "get_next_delivery_date_for_delivery_cycle",
    )
    def test_getNumberOfDeliveriesInMonth_subscriptionFullyIncludesGivenMonth_returnsAllDeliveries(
        self,
        mock_get_next_delivery_date_for_delivery_cycle: Mock,
        mock_get_member_pickup_location_id_from_cache: Mock,
    ):
        delivery_cycle = Mock()
        subscription = SubscriptionFactory.build(
            mandate_ref__ref="test_ref",
            start_date=datetime.date(year=2025, month=1, day=1),
            end_date=datetime.date(year=2025, month=12, day=31),
            product__type__delivery_cycle=delivery_cycle,
            member_id="test_member_id",
        )
        first_of_month = datetime.date(year=2025, month=8, day=1)
        cache = Mock()

        mock_get_member_pickup_location_id_from_cache.side_effect = (
            lambda member_id, reference_date, cache: (
                "pl_id_1"
                if reference_date < datetime.date(year=2025, month=8, day=16)
                else "pl_id_2"
            )
        )

        def mock_get_next_delivery_date(
            reference_date, pickup_location_id, delivery_cycle, cache
        ):
            if reference_date < first_of_month:
                return first_of_month
            return reference_date + datetime.timedelta(days=7)

        mock_get_next_delivery_date_for_delivery_cycle.side_effect = (
            mock_get_next_delivery_date
        )

        result = MonthPaymentBuilder.get_number_of_deliveries_in_month(
            subscription=subscription, first_of_month=first_of_month, cache=cache
        )

        self.assertEqual(
            5,
            result,
            "There should be a delivery on each Friday of the month (1, 8, 15, 22, 29)",
        )

        self.assertEqual(6, mock_get_member_pickup_location_id_from_cache.call_count)
        mock_get_member_pickup_location_id_from_cache.assert_has_calls(
            [
                call(
                    member_id="test_member_id",
                    reference_date=reference_date,
                    cache=cache,
                )
                for reference_date in [
                    datetime.date(year=2025, month=7, day=31),
                    datetime.date(year=2025, month=8, day=1),
                    datetime.date(year=2025, month=8, day=8),
                    datetime.date(year=2025, month=8, day=15),
                    datetime.date(year=2025, month=8, day=22),
                    datetime.date(year=2025, month=8, day=29),
                ]
            ]
        )
        self.assertEqual(6, mock_get_next_delivery_date_for_delivery_cycle.call_count)
        mock_get_next_delivery_date_for_delivery_cycle.assert_has_calls(
            [
                call(
                    reference_date=reference_date,
                    pickup_location_id="pl_id_1",
                    delivery_cycle=delivery_cycle,
                    cache=cache,
                )
                for reference_date in [
                    datetime.date(year=2025, month=7, day=31),
                    datetime.date(year=2025, month=8, day=1),
                    datetime.date(year=2025, month=8, day=8),
                    datetime.date(year=2025, month=8, day=15),
                ]
            ]
        )
        mock_get_next_delivery_date_for_delivery_cycle.assert_has_calls(
            [
                call(
                    reference_date=reference_date,
                    pickup_location_id="pl_id_2",
                    delivery_cycle=delivery_cycle,
                    cache=cache,
                )
                for reference_date in [
                    datetime.date(year=2025, month=8, day=22),
                    datetime.date(year=2025, month=8, day=29),
                ]
            ]
        )

    @patch.object(
        MemberPickupLocationService, "get_member_pickup_location_id_from_cache"
    )
    @patch.object(
        DeliveryDateCalculator,
        "get_next_delivery_date_for_delivery_cycle",
    )
    def test_getNumberOfDeliveriesInMonth_subscriptionStartsInGivenMonth_returnsDeliveriesAfterStartOnly(
        self,
        mock_get_next_delivery_date_for_delivery_cycle: Mock,
        mock_get_member_pickup_location_id_from_cache: Mock,
    ):
        delivery_cycle = Mock()
        subscription = SubscriptionFactory.build(
            mandate_ref__ref="test_ref",
            start_date=datetime.date(year=2025, month=8, day=10),
            end_date=datetime.date(year=2025, month=12, day=31),
            product__type__delivery_cycle=delivery_cycle,
            member_id="test_member_id",
        )
        first_of_month = datetime.date(year=2025, month=8, day=1)
        cache = Mock()

        mock_get_member_pickup_location_id_from_cache.return_value = "pl_id"

        def mock_get_next_delivery_date(
            reference_date, pickup_location_id, delivery_cycle, cache
        ):
            if reference_date < first_of_month:
                return first_of_month
            return reference_date + datetime.timedelta(days=7)

        mock_get_next_delivery_date_for_delivery_cycle.side_effect = (
            mock_get_next_delivery_date
        )

        result = MonthPaymentBuilder.get_number_of_deliveries_in_month(
            subscription=subscription, first_of_month=first_of_month, cache=cache
        )

        self.assertEqual(
            3, result, "There should be a delivery on the 15th, 22nd, 29th"
        )

    @patch.object(
        MemberPickupLocationService, "get_member_pickup_location_id_from_cache"
    )
    @patch.object(
        DeliveryDateCalculator,
        "get_next_delivery_date_for_delivery_cycle",
    )
    def test_getNumberOfDeliveriesInMonth_subscriptionEndsInGivenMonth_returnsDeliveriesBeforeEndOnly(
        self,
        mock_get_next_delivery_date_for_delivery_cycle: Mock,
        mock_get_member_pickup_location_id_from_cache: Mock,
    ):
        delivery_cycle = Mock()
        subscription = SubscriptionFactory.build(
            mandate_ref__ref="test_ref",
            start_date=datetime.date(year=2025, month=1, day=1),
            end_date=datetime.date(year=2025, month=8, day=23),
            product__type__delivery_cycle=delivery_cycle,
            member_id="test_member_id",
        )
        first_of_month = datetime.date(year=2025, month=8, day=1)
        cache = Mock()

        mock_get_member_pickup_location_id_from_cache.return_value = "pl_id"

        def mock_get_next_delivery_date(
            reference_date, pickup_location_id, delivery_cycle, cache
        ):
            if reference_date < first_of_month:
                return first_of_month
            return reference_date + datetime.timedelta(days=7)

        mock_get_next_delivery_date_for_delivery_cycle.side_effect = (
            mock_get_next_delivery_date
        )

        result = MonthPaymentBuilder.get_number_of_deliveries_in_month(
            subscription=subscription, first_of_month=first_of_month, cache=cache
        )

        self.assertEqual(
            4, result, "There should be a delivery on the 1st, 8th, 15th, 22nd"
        )

    @patch.object(
        MemberPickupLocationService, "get_member_pickup_location_id_from_cache"
    )
    @patch.object(
        DeliveryDateCalculator,
        "get_next_delivery_date_for_delivery_cycle",
    )
    def test_getNumberOfDeliveriesInMonth_subscriptionStartsAndEndsInGivenMonth_returnsDeliveriesInsideSubscriptionOnly(
        self,
        mock_get_next_delivery_date_for_delivery_cycle: Mock,
        mock_get_member_pickup_location_id_from_cache: Mock,
    ):
        delivery_cycle = Mock()
        subscription = SubscriptionFactory.build(
            mandate_ref__ref="test_ref",
            start_date=datetime.date(year=2025, month=8, day=4),
            end_date=datetime.date(year=2025, month=8, day=24),
            product__type__delivery_cycle=delivery_cycle,
            member_id="test_member_id",
        )
        first_of_month = datetime.date(year=2025, month=8, day=1)
        cache = Mock()

        mock_get_member_pickup_location_id_from_cache.return_value = "pl_id"

        def mock_get_next_delivery_date(
            reference_date, pickup_location_id, delivery_cycle, cache
        ):
            if reference_date < first_of_month:
                return first_of_month
            return reference_date + datetime.timedelta(days=7)

        mock_get_next_delivery_date_for_delivery_cycle.side_effect = (
            mock_get_next_delivery_date
        )

        result = MonthPaymentBuilder.get_number_of_deliveries_in_month(
            subscription=subscription, first_of_month=first_of_month, cache=cache
        )

        self.assertEqual(3, result, "There should be a delivery on the 8th, 15th, 22nd")
