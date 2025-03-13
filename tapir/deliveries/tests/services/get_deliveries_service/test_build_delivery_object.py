import datetime
from unittest.mock import patch, Mock

from tapir.deliveries.services.get_deliveries_service import GetDeliveriesService
from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.models import ProductType, Member, PickupLocationOpeningTime
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests import factories
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    MemberWithSubscriptionFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestGetDeliveriesServiceBuildDeliveryObject(TapirIntegrationTest):
    def setUp(self):
        ParameterDefinitions().import_definitions()
        mock_timezone(self, factories.NOW)

    def test_buildDeliveryObject_noSubscriptionWithDeliveryOnGivenWeek_returnsNone(
        self,
    ):
        member = MemberFactory.create()
        SubscriptionFactory.create(  # ends before the given date
            member=member, end_date=datetime.date(year=2023, month=6, day=1)
        )

        MemberWithSubscriptionFactory.create()  # another member with a subscription that should not influence our result
        ProductType.objects.update(delivery_cycle=WEEKLY[0])

        self.assertIsNone(
            GetDeliveriesService.build_delivery_object(
                member, datetime.date(year=2023, month=6, day=5)
            )
        )

    @patch.object(GetDeliveriesService, "update_delivery_date_to_opening_times")
    def test_buildDeliveryObject_default_returnsCorrectDeliveryDate(
        self,
        mock_update_delivery_date_to_opening_times: Mock,
    ):
        member = MemberFactory.create()
        SubscriptionFactory.create(member=member)
        ProductType.objects.update(delivery_cycle=WEEKLY[0])

        updated_delivery_date = datetime.date(year=2023, month=6, day=8)
        mock_update_delivery_date_to_opening_times.return_value = updated_delivery_date

        given_delivery_date = datetime.date(year=2023, month=6, day=5)
        delivery_object = GetDeliveriesService.build_delivery_object(
            member, given_delivery_date
        )

        self.assertIsNotNone(delivery_object)
        self.assertEqual(updated_delivery_date, delivery_object["delivery_date"])
        mock_update_delivery_date_to_opening_times.assert_called_once()

    @patch.object(JokerManagementService, "can_joker_be_used")
    @patch.object(GetDeliveriesService, "is_joker_used_in_week")
    @patch.object(GetDeliveriesService, "update_delivery_date_to_opening_times")
    @patch.object(PickupLocationOpeningTime, "objects")
    @patch.object(Member, "get_pickup_location")
    def test_buildDeliveryObject_default_returnsCorrectPickupLocationData(
        self,
        mock_get_pickup_location: Mock,
        mock_pickup_location_opening_times_objects: Mock,
        *_,
    ):
        member = MemberFactory.create()
        SubscriptionFactory.create(member=member)
        ProductType.objects.update(delivery_cycle=WEEKLY[0])

        mock_pickup_location = Mock()
        mock_get_pickup_location.return_value = mock_pickup_location
        mock_opening_times = Mock()
        mock_pickup_location_opening_times_objects.filter.return_value = (
            mock_opening_times
        )

        given_delivery_date = datetime.date(year=2023, month=6, day=5)
        delivery_object = GetDeliveriesService.build_delivery_object(
            member, given_delivery_date
        )

        self.assertIsNotNone(delivery_object)
        self.assertEqual(mock_pickup_location, delivery_object["pickup_location"])
        self.assertEqual(
            mock_opening_times, delivery_object["pickup_location_opening_times"]
        )

    def test_buildDeliveryObject_default_returnsCorrectSubscriptions(
        self,
    ):
        member = MemberFactory.create()
        active_subscription_1 = SubscriptionFactory.create(member=member)
        active_subscription_2 = SubscriptionFactory.create(member=member)
        SubscriptionFactory.create(  # ends before the given date
            member=member, end_date=datetime.date(year=2023, month=6, day=1)
        )
        ProductType.objects.update(delivery_cycle=WEEKLY[0])

        given_delivery_date = datetime.date(year=2023, month=6, day=5)
        delivery_object = GetDeliveriesService.build_delivery_object(
            member, given_delivery_date
        )

        self.assertIsNotNone(delivery_object)
        self.assertEqual(2, len(delivery_object["subscriptions"]))
        self.assertIn(active_subscription_1, delivery_object["subscriptions"])
        self.assertIn(active_subscription_2, delivery_object["subscriptions"])

    @patch.object(JokerManagementService, "can_joker_be_used")
    @patch.object(GetDeliveriesService, "is_joker_used_in_week")
    def test_buildDeliveryObject_default_returnsCorrectJokerData(
        self,
        mock_is_joker_used_in_week: Mock,
        mock_can_joker_be_used: Mock,
    ):
        member = MemberFactory.create()
        SubscriptionFactory.create(member=member)
        ProductType.objects.update(delivery_cycle=WEEKLY[0])
        mock_is_joker_used_in_week_value = Mock()
        mock_is_joker_used_in_week.return_value = mock_is_joker_used_in_week_value
        mock_can_joker_be_used_value = Mock()
        mock_can_joker_be_used.return_value = mock_can_joker_be_used_value

        given_delivery_date = datetime.date(year=2023, month=6, day=5)
        delivery_object = GetDeliveriesService.build_delivery_object(
            member, given_delivery_date
        )

        self.assertEqual(
            mock_is_joker_used_in_week_value, delivery_object["joker_used"]
        )
        self.assertEqual(
            mock_can_joker_be_used_value, delivery_object["can_joker_be_used"]
        )
