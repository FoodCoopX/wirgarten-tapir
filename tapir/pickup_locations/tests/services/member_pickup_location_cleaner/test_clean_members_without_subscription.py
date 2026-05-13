import datetime

from tapir.pickup_locations.services.member_pickup_location_cleaner import (
    MemberPickupLocationCleaner,
)
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.wirgarten.constants import WEEKLY, NO_DELIVERY
from tapir.wirgarten.models import MemberPickupLocation
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PickupLocationFactory,
    MemberPickupLocationFactory,
    GrowingPeriodFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestCleanMembersWithoutSubscription(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls.member = MemberFactory.create()
        cls.pickup_location = PickupLocationFactory.create()

    def setUp(self) -> None:
        self.now = mock_timezone(
            test=self, now=datetime.datetime(year=2029, month=6, day=29)
        )
        self.today = self.now.date()
        self.growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2029, month=1, day=1)
        )

    def test_cleanMembersWithoutSubscription_memberHasNoSubscription_cleans(self):
        MemberPickupLocationFactory.create(
            member=self.member,
            pickup_location=self.pickup_location,
            valid_from=self.growing_period.start_date,
        )

        MemberPickupLocationCleaner.clean_members_without_subscription(
            reference_date=self.today, dry_run=False
        )

        self.assert_pickup_location_cleaned()

    def test_cleanMembersWithoutSubscription_memberHasOneCurrentDeliveredSubscription_doesntClean(
        self,
    ):
        MemberPickupLocationFactory.create(
            member=self.member,
            pickup_location=self.pickup_location,
            valid_from=self.growing_period.start_date,
        )
        SubscriptionFactory.create(
            member=self.member,
            period=self.growing_period,
            product__type__delivery_cycle=WEEKLY[0],
        )

        MemberPickupLocationCleaner.clean_members_without_subscription(
            reference_date=self.today, dry_run=False
        )

        self.assert_pickup_location_not_cleaned()

    def test_cleanMembersWithoutSubscription_memberHasOneFutureDeliveredSubscription_doesntClean(
        self,
    ):
        MemberPickupLocationFactory.create(
            member=self.member,
            pickup_location=self.pickup_location,
            valid_from=self.growing_period.start_date,
        )
        SubscriptionFactory.create(
            member=self.member,
            period=GrowingPeriodFactory.create(
                start_date=self.growing_period.end_date + datetime.timedelta(days=1)
            ),
            product__type__delivery_cycle=WEEKLY[0],
        )

        MemberPickupLocationCleaner.clean_members_without_subscription(
            reference_date=self.today, dry_run=False
        )

        self.assert_pickup_location_not_cleaned()

    def test_cleanMembersWithoutSubscription_memberHasOneCurrentSubscriptionWithoutDelivery_cleans(
        self,
    ):
        MemberPickupLocationFactory.create(
            member=self.member,
            pickup_location=self.pickup_location,
            valid_from=self.growing_period.start_date,
        )
        SubscriptionFactory.create(
            member=self.member,
            period=self.growing_period,
            product__type__delivery_cycle=NO_DELIVERY[0],
        )

        MemberPickupLocationCleaner.clean_members_without_subscription(
            reference_date=self.today, dry_run=False
        )

        self.assert_pickup_location_cleaned()

    def test_cleanMembersWithoutSubscription_memberHasOnePastDeliveredSubscription_cleans(
        self,
    ):
        MemberPickupLocationFactory.create(
            member=self.member,
            pickup_location=self.pickup_location,
            valid_from=self.growing_period.start_date,
        )
        SubscriptionFactory.create(
            member=self.member,
            period=GrowingPeriodFactory.create(
                start_date=self.growing_period.start_date.replace(
                    year=self.growing_period.start_date.year - 1
                )
            ),
            product__type__delivery_cycle=WEEKLY[0],
        )

        MemberPickupLocationCleaner.clean_members_without_subscription(
            reference_date=self.today, dry_run=False
        )

        self.assert_pickup_location_cleaned()

    def test_cleanMembersWithoutSubscription_memberHasAFuturePickupLocationValueNone_cleans(
        self,
    ):
        MemberPickupLocationFactory.create(
            member=self.member,
            pickup_location=self.pickup_location,
            valid_from=self.growing_period.start_date,
        )

        MemberPickupLocationFactory.create(
            member=self.member,
            pickup_location=None,
            valid_from=self.today + datetime.timedelta(days=10),
        )

        MemberPickupLocationCleaner.clean_members_without_subscription(
            reference_date=self.today, dry_run=False
        )

        self.assert_pickup_location_cleaned()

    def test_cleanMembersWithoutSubscription_memberHasAFuturePickupLocationValueNotNone_cleans(
        self,
    ):
        MemberPickupLocationFactory.create(
            member=self.member,
            pickup_location=self.pickup_location,
            valid_from=self.today + datetime.timedelta(days=10),
        )

        MemberPickupLocationCleaner.clean_members_without_subscription(
            reference_date=self.today, dry_run=False
        )

        self.assert_pickup_location_cleaned()

    def test_cleanMembersWithoutSubscription_memberHasNeverHadAPickupLocation_doesntClean(
        self,
    ):
        MemberPickupLocationCleaner.clean_members_without_subscription(
            reference_date=self.today, dry_run=False
        )

        self.assertFalse(MemberPickupLocation.objects.exists())

    def test_cleanMembersWithoutSubscription_memberLocationIsAlreadyNone_doesntClean(
        self,
    ):
        old_location_object = MemberPickupLocationFactory.create(
            member=self.member,
            pickup_location=None,
            valid_from=self.growing_period.start_date,
        )

        MemberPickupLocationCleaner.clean_members_without_subscription(
            reference_date=self.today, dry_run=False
        )

        self.assertEqual(1, MemberPickupLocation.objects.count())
        new_location_object = MemberPickupLocation.objects.get()
        self.assertEqual(old_location_object, new_location_object)

    def test_cleanMembersWithoutSubscription_dryRun_doesntClean(
        self,
    ):
        MemberPickupLocationFactory.create(
            member=self.member,
            pickup_location=self.pickup_location,
            valid_from=self.growing_period.start_date,
        )

        MemberPickupLocationCleaner.clean_members_without_subscription(
            reference_date=self.today, dry_run=True
        )

        self.assert_pickup_location_not_cleaned()

    def assert_pickup_location_cleaned(self):
        last_member_location_object = MemberPickupLocation.objects.order_by(
            "valid_from"
        ).last()
        self.assertEqual(self.today, last_member_location_object.valid_from)
        self.assertIsNone(last_member_location_object.pickup_location)

        result = MemberPickupLocationGetter.get_member_pickup_location(
            member=self.member, reference_date=self.today, cache={}
        )
        self.assertIsNone(result)

    def assert_pickup_location_not_cleaned(self):
        last_member_location_object = MemberPickupLocation.objects.order_by(
            "valid_from"
        ).last()
        self.assertEqual(
            self.growing_period.start_date, last_member_location_object.valid_from
        )

        result = MemberPickupLocationGetter.get_member_pickup_location(
            member=self.member, reference_date=self.today, cache={}
        )
        self.assertEqual(self.pickup_location, result)
