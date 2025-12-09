import datetime

from django.urls import reverse

from tapir.configuration.models import TapirParameter
from tapir.waiting_list.tests.factories import WaitingListEntryFactory
from tapir.wirgarten.constants import WEEKLY, EVEN_WEEKS
from tapir.wirgarten.models import PickupLocationOpeningTime
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    ProductFactory,
    GrowingPeriodFactory,
    PickupLocationFactory,
    MemberFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestBestellWizardDeliveryDatesForOrderApiView(TapirIntegrationTest):
    maxDiff = 2000

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_BUFFER_TIME_BEFORE_START
        ).update(value=20)
        TapirParameter.objects.filter(
            key=ParameterKeys.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL
        ).update(
            value=6
        )  # pickup location changes until sunday

        cls.product_weekly = ProductFactory.create(type__delivery_cycle=WEEKLY[0])
        cls.product_even_weeks = ProductFactory.create(
            type__delivery_cycle=EVEN_WEEKS[0]
        )

        cls.current_growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2024, month=1, day=1)
        )
        cls.next_growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2025, month=1, day=1)
        )

        cls.pickup_location_1 = PickupLocationFactory.create()
        PickupLocationOpeningTime.objects.create(
            pickup_location=cls.pickup_location_1,
            day_of_week=3,
            open_time=datetime.time(8, 0),
            close_time=datetime.time(9, 0),
        )  # delivery on Thursday

        cls.pickup_location_2 = PickupLocationFactory.create()
        PickupLocationOpeningTime.objects.create(
            pickup_location=cls.pickup_location_2,
            day_of_week=4,
            open_time=datetime.time(8, 0),
            close_time=datetime.time(9, 0),
        )  # delivery on Friday

    def setUp(self) -> None:
        mock_timezone(self, now=datetime.datetime(year=2024, month=6, day=8))

    def test_post_noWaitingListAndNoGrowingPeriodSpecified_returnsDatesRelativeToTheStandardContractStart(
        self,
    ):
        url = reverse("bestell_wizard:bestell_wizard_delivery_dates")

        response = self.client.post(
            url,
            data={
                "shopping_cart": {
                    self.product_weekly.id: 1,
                    self.product_even_weeks.id: 2,
                },
            },
            content_type="application/json",
        )

        # The first monday after the 20 days buffer period is the 2024-07-01, the first delivery is on the following wednesday
        self.assertEqual(
            {
                self.pickup_location_1.id: {
                    self.product_weekly.type.id: "2024-07-04",
                    self.product_even_weeks.type.id: "2024-07-11",
                },
                self.pickup_location_2.id: {
                    self.product_weekly.type.id: "2024-07-05",
                    self.product_even_weeks.type.id: "2024-07-12",
                },
            },
            response.json()["delivery_date_by_pickup_location_id_and_product_type_id"],
        )

    def test_post_noWaitingListButGrowingPeriodSpecified_returnsDatesRelativeToTheGrowingPeriod(
        self,
    ):
        url = reverse("bestell_wizard:bestell_wizard_delivery_dates")

        response = self.client.post(
            url,
            data={
                "shopping_cart": {
                    self.product_weekly.id: 1,
                    self.product_even_weeks.id: 2,
                },
                "growing_period_id": self.next_growing_period.id,
            },
            content_type="application/json",
        )

        # The first delivery day of the given growing period is the first thursday, 2025-01-02
        # However, the contract must start on a monday and within the given period.
        # The contract will therefore start on the 06.01., the first delivery will be right after that.
        self.assertEqual(
            {
                self.pickup_location_1.id: {
                    self.product_weekly.type.id: "2025-01-09",
                    self.product_even_weeks.type.id: "2025-01-09",
                },
                self.pickup_location_2.id: {
                    self.product_weekly.type.id: "2025-01-10",
                    self.product_even_weeks.type.id: "2025-01-10",
                },
            },
            response.json()["delivery_date_by_pickup_location_id_and_product_type_id"],
        )

    def test_post_waitingListEntryWithOnlyPickupLocationWish_returnsDatesRelativeToThePickupLocationChange(
        self,
    ):
        url = reverse("bestell_wizard:bestell_wizard_delivery_dates")
        member = MemberFactory.create()
        waiting_list_entry = WaitingListEntryFactory.create(member=member)
        SubscriptionFactory.create(
            product=self.product_weekly,
            period=self.current_growing_period,
            member=member,
        )
        SubscriptionFactory.create(
            product=self.product_even_weeks,
            period=self.current_growing_period,
            member=member,
        )

        response = self.client.post(
            url,
            data={
                "shopping_cart": {},
                "waiting_list_entry_id": waiting_list_entry.id,
            },
            content_type="application/json",
        )

        # Today is Saturday, changes are allowed until Sunday, so the first delivery is on the following week
        self.assertEqual(
            {
                self.pickup_location_1.id: {
                    self.product_weekly.type.id: "2024-06-13",
                    self.product_even_weeks.type.id: "2024-06-13",
                },
                self.pickup_location_2.id: {
                    self.product_weekly.type.id: "2024-06-14",
                    self.product_even_weeks.type.id: "2024-06-14",
                },
            },
            response.json()["delivery_date_by_pickup_location_id_and_product_type_id"],
        )

    def test_post_waitingListEntryWithDesiredDate_returnsFirstDeliveryAfterDesiredDate(
        self,
    ):
        url = reverse("bestell_wizard:bestell_wizard_delivery_dates")
        member = MemberFactory.create()
        waiting_list_entry = WaitingListEntryFactory.create(
            member=member, desired_start_date=datetime.date(year=2024, month=8, day=13)
        )

        response = self.client.post(
            url,
            data={
                "shopping_cart": {
                    self.product_weekly.id: 1,
                    self.product_even_weeks.id: 2,
                },
                "waiting_list_entry_id": waiting_list_entry.id,
            },
            content_type="application/json",
        )

        self.assertEqual(
            {
                self.pickup_location_1.id: {
                    self.product_weekly.type.id: "2024-08-15",
                    self.product_even_weeks.type.id: "2024-08-22",
                },
                self.pickup_location_2.id: {
                    self.product_weekly.type.id: "2024-08-16",
                    self.product_even_weeks.type.id: "2024-08-23",
                },
            },
            response.json()["delivery_date_by_pickup_location_id_and_product_type_id"],
        )

    def test_post_waitingListEntryWithProductWishes_returnsDatesRelativeToContractStartDateWithoutBuffer(
        self,
    ):
        url = reverse("bestell_wizard:bestell_wizard_delivery_dates")
        waiting_list_entry = WaitingListEntryFactory.create()

        response = self.client.post(
            url,
            data={
                "shopping_cart": {
                    self.product_weekly.id: 1,  # The wishes are sent as shopping cart by the bestell wizard
                    self.product_even_weeks.id: 2,
                },
                "waiting_list_entry_id": waiting_list_entry.id,
            },
            content_type="application/json",
        )

        self.assertEqual(
            {
                self.pickup_location_1.id: {
                    self.product_weekly.type.id: "2024-06-13",
                    self.product_even_weeks.type.id: "2024-06-13",
                },
                self.pickup_location_2.id: {
                    self.product_weekly.type.id: "2024-06-14",
                    self.product_even_weeks.type.id: "2024-06-14",
                },
            },
            response.json()["delivery_date_by_pickup_location_id_and_product_type_id"],
        )
