import datetime
from unittest.mock import patch, Mock

from tapir_mail.service.shortcuts import make_timezone_aware

from tapir.configuration.models import TapirParameter
from tapir.deliveries.services.delivery_donation_manager import DeliveryDonationManager
from tapir.deliveries.services.get_deliveries_service import GetDeliveriesService
from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.deliveries.services.weeks_without_delivery_service import (
    WeeksWithoutDeliveryService,
)
from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.pickup_locations.services.pickup_location_opening_times_manager import (
    PickupLocationOpeningTimesManager,
)
from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.models import ProductType, PickupLocationOpeningTime
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests import factories
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    MemberWithSubscriptionFactory,
    SubscriptionFactory,
    ProductTypeFactory,
    GrowingPeriodFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestGetDeliveriesServiceBuildDeliveryObject(TapirIntegrationTest):
    def setUp(self):
        mock_timezone(self, factories.NOW)

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

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
                member=member,
                delivery_date=datetime.date(year=2023, month=6, day=5),
                cache={},
            )
        )

    @patch.object(
        PickupLocationOpeningTimesManager, "update_delivery_date_to_opening_times"
    )
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
            member=member,
            delivery_date=given_delivery_date,
            cache={},
        )

        self.assertIsNotNone(delivery_object)
        self.assertEqual(updated_delivery_date, delivery_object["delivery_date"])
        mock_update_delivery_date_to_opening_times.assert_called_once()

    @patch.object(JokerManagementService, "can_joker_be_used_in_week")
    @patch.object(JokerManagementService, "does_member_have_a_joker_in_week")
    @patch.object(
        PickupLocationOpeningTimesManager, "update_delivery_date_to_opening_times"
    )
    @patch.object(PickupLocationOpeningTime, "objects")
    @patch.object(
        MemberPickupLocationService, "get_member_pickup_location_id_from_cache"
    )
    def test_buildDeliveryObject_default_returnsCorrectPickupLocationData(
        self,
        mock_get_member_pickup_location_id_from_cache: Mock,
        mock_pickup_location_opening_times_objects: Mock,
        mock_update_delivery_date_to_opening_times: Mock,
        *_,
    ):
        member = MemberFactory.create()
        SubscriptionFactory.create(member=member)
        ProductType.objects.update(delivery_cycle=WEEKLY[0])

        mock_pickup_location = Mock()
        mock_get_member_pickup_location_id_from_cache.return_value = "test_pl_id"
        cache = {"pickup_location_by_id": {"test_pl_id": mock_pickup_location}}
        mock_opening_time = Mock()
        mock_pickup_location_opening_times_objects.filter.return_value = [
            mock_opening_time
        ]
        mock_update_delivery_date_to_opening_times.return_value = datetime.date(
            year=2023, month=6, day=7
        )

        given_delivery_date = datetime.date(year=2023, month=6, day=5)
        delivery_object = GetDeliveriesService.build_delivery_object(
            member=member,
            delivery_date=given_delivery_date,
            cache=cache,
        )

        self.assertIsNotNone(delivery_object)
        self.assertEqual(mock_pickup_location, delivery_object["pickup_location"])
        self.assertEqual(
            [mock_opening_time], delivery_object["pickup_location_opening_times"]
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
            member=member,
            delivery_date=given_delivery_date,
            cache={},
        )

        self.assertIsNotNone(delivery_object)
        self.assertEqual(2, len(delivery_object["subscriptions"]))
        self.assertIn(active_subscription_1, delivery_object["subscriptions"])
        self.assertIn(active_subscription_2, delivery_object["subscriptions"])

    @patch.object(JokerManagementService, "can_joker_be_used_in_week")
    @patch.object(JokerManagementService, "does_member_have_a_joker_in_week")
    def test_buildDeliveryObject_default_returnsCorrectJokerData(
        self,
        mock_does_member_have_a_joker_in_week: Mock,
        mock_can_joker_be_used_in_week: Mock,
    ):
        member = MemberFactory.create()
        SubscriptionFactory.create(member=member)
        ProductType.objects.update(delivery_cycle=WEEKLY[0])
        mock_is_joker_used_in_week_value = Mock()
        mock_does_member_have_a_joker_in_week.return_value = (
            mock_is_joker_used_in_week_value
        )
        mock_can_joker_be_used_value = Mock()
        mock_can_joker_be_used_in_week.return_value = mock_can_joker_be_used_value

        given_delivery_date = datetime.date(year=2023, month=6, day=5)
        delivery_object = GetDeliveriesService.build_delivery_object(
            member=member,
            delivery_date=given_delivery_date,
            cache={},
        )

        self.assertEqual(
            mock_is_joker_used_in_week_value, delivery_object["joker_used"]
        )
        self.assertEqual(
            mock_can_joker_be_used_value, delivery_object["can_joker_be_used"]
        )

    @patch.object(JokerManagementService, "can_joker_be_used_in_week")
    @patch.object(JokerManagementService, "does_member_have_a_joker_in_week")
    def test_buildDeliveryObject_jokerUsed_returnsOnlySubscriptionsFromProductTypesNotAffectedByJokers(
        self,
        mock_does_member_have_a_joker_in_week: Mock,
        mock_can_joker_be_used_in_week: Mock,
    ):
        member = MemberFactory.create()
        type_1 = ProductTypeFactory.create(is_affected_by_jokers=True)
        type_2 = ProductTypeFactory.create(is_affected_by_jokers=False)
        SubscriptionFactory.create(member=member, product__type=type_1)
        subscription_2 = SubscriptionFactory.create(member=member, product__type=type_2)
        ProductType.objects.update(delivery_cycle=WEEKLY[0])
        mock_does_member_have_a_joker_in_week_value = Mock()
        mock_does_member_have_a_joker_in_week.return_value = (
            mock_does_member_have_a_joker_in_week_value
        )
        mock_can_joker_be_used_value = Mock()
        mock_can_joker_be_used_in_week.return_value = mock_can_joker_be_used_value

        given_delivery_date = datetime.date(year=2023, month=6, day=5)
        delivery_object = GetDeliveriesService.build_delivery_object(
            member=member,
            delivery_date=given_delivery_date,
            cache={},
        )
        self.assertEqual([subscription_2], list(delivery_object["subscriptions"]))

    @patch.object(WeeksWithoutDeliveryService, "is_delivery_cancelled_this_week")
    def test_buildDeliveryObject_default_returnsCorrectCancelData(
        self, mock_is_delivery_cancelled_this_week: Mock
    ):
        member = MemberFactory.create()
        SubscriptionFactory.create(member=member)
        ProductType.objects.update(delivery_cycle=WEEKLY[0])
        mock_is_delivery_cancelled_this_week_value = Mock()
        mock_is_delivery_cancelled_this_week.return_value = (
            mock_is_delivery_cancelled_this_week_value
        )

        given_delivery_date = datetime.date(year=2023, month=6, day=5)
        delivery_object = GetDeliveriesService.build_delivery_object(
            member=member,
            delivery_date=given_delivery_date,
            cache={},
        )

        self.assertEqual(
            mock_is_delivery_cancelled_this_week_value,
            delivery_object["is_delivery_cancelled_this_week"],
        )

    @patch.object(
        DeliveryDonationManager, "does_member_have_a_donation_in_week", autospec=True
    )
    @patch.object(DeliveryDonationManager, "can_delivery_be_donated", autospec=True)
    def test_buildDeliveryObject_default_returnsCorrectDonationData(
        self,
        mock_can_delivery_be_donated: Mock,
        mock_does_member_have_a_donation_in_week: Mock,
    ):
        member = MemberFactory.create()
        SubscriptionFactory.create(member=member)
        ProductType.objects.update(delivery_cycle=WEEKLY[0])
        mock_can_delivery_be_donated_value = Mock()
        mock_can_delivery_be_donated.return_value = mock_can_delivery_be_donated_value
        mock_does_member_have_a_donation_in_week_value = Mock()
        mock_does_member_have_a_donation_in_week.return_value = (
            mock_does_member_have_a_donation_in_week_value
        )

        given_delivery_date = datetime.date(year=2023, month=6, day=5)
        delivery_object = GetDeliveriesService.build_delivery_object(
            member=member,
            delivery_date=given_delivery_date,
            cache={},
        )

        self.assertEqual(
            mock_can_delivery_be_donated_value,
            delivery_object["can_delivery_be_donated"],
        )
        self.assertEqual(
            mock_does_member_have_a_donation_in_week_value,
            delivery_object["donation_used"],
        )

    def test_buildDeliveryObject_givenDateIsAfterSubscriptionEndButSubscriptionNotCancelled_returnsPreviousSubscriptions(
        self,
    ):
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        ).update(value=True)
        member = MemberFactory.create()
        past_growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2022, month=1, day=1),
            end_date=datetime.date(year=2022, month=12, day=31),
        )
        GrowingPeriodFactory.create(
            start_date=datetime.date(year=2023, month=1, day=1),
            end_date=datetime.date(year=2023, month=12, day=31),
        )
        past_subscription = SubscriptionFactory.create(
            member=member, period=past_growing_period
        )

        ProductType.objects.update(delivery_cycle=WEEKLY[0])

        given_delivery_date = datetime.date(year=2023, month=6, day=5)
        delivery_object = GetDeliveriesService.build_delivery_object(
            member=member,
            delivery_date=given_delivery_date,
            cache={},
        )

        self.assertIsNotNone(delivery_object)
        self.assertEqual(1, len(delivery_object["subscriptions"]))
        self.assertIn(past_subscription, delivery_object["subscriptions"])

    def test_buildDeliveryObject_givenDateIsAfterSubscriptionEndAndSubscriptionCancelled_returnsNone(
        self,
    ):
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        ).update(value=True)
        member = MemberFactory.create()
        past_growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2022, month=1, day=1),
            end_date=datetime.date(year=2022, month=12, day=31),
        )
        GrowingPeriodFactory.create(
            start_date=datetime.date(year=2023, month=1, day=1),
            end_date=datetime.date(year=2023, month=12, day=31),
        )
        SubscriptionFactory.create(
            member=member,
            period=past_growing_period,
            cancellation_ts=make_timezone_aware(
                datetime.datetime(year=2022, month=11, day=15)
            ),
        )

        ProductType.objects.update(delivery_cycle=WEEKLY[0])

        given_delivery_date = datetime.date(year=2023, month=6, day=5)
        delivery_object = GetDeliveriesService.build_delivery_object(
            member=member,
            delivery_date=given_delivery_date,
            cache={},
        )

        self.assertIsNone(delivery_object)

    def test_buildDeliveryObject_givenDateIsAfterSubscriptionEndButAutoRenewIsOff_returnsNone(
        self,
    ):
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        ).update(value=False)
        member = MemberFactory.create()
        past_growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2022, month=1, day=1),
            end_date=datetime.date(year=2022, month=12, day=31),
        )
        GrowingPeriodFactory.create(
            start_date=datetime.date(year=2023, month=1, day=1),
            end_date=datetime.date(year=2023, month=12, day=31),
        )
        SubscriptionFactory.create(member=member, period=past_growing_period)

        ProductType.objects.update(delivery_cycle=WEEKLY[0])

        given_delivery_date = datetime.date(year=2023, month=6, day=5)
        delivery_object = GetDeliveriesService.build_delivery_object(
            member=member,
            delivery_date=given_delivery_date,
            cache={},
        )

        self.assertIsNone(delivery_object)
