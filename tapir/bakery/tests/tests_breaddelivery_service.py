from datetime import date
from unittest.mock import patch

from django.test import TestCase

from tapir.bakery.models import BreadDelivery
from tapir.bakery.services.bread_delivery_context_service import (
    BreadDeliveryContextService,
)
from tapir.bakery.services.breaddelivery_service import BreadDeliveryService
from tapir.bakery.tests.factories import enable_bakery
from tapir.deliveries.models import Joker
from tapir.wirgarten.constants import NO_DELIVERY
from tapir.wirgarten.models import MemberPickupLocation
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    MemberPickupLocationFactory,
    PickupLocationFactory,
    ProductFactory,
    ProductTypeFactory,
    SubscriptionFactory,
)


class TestEnsureBreadDeliveriesForMember(TestCase):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        enable_bakery()
        self.product_type = ProductTypeFactory.create(
            name="Brot", delivery_cycle="weekly"
        )
        self.product = ProductFactory.create(type=self.product_type, name="Brot Abo")

    @staticmethod
    def _derived_pickup_location_id(delivery, cache=None):
        return BreadDeliveryContextService.get_pickup_location_id(
            delivery, cache={} if cache is None else cache
        )

    @staticmethod
    def _derived_joker_taken(delivery, cache=None):
        return BreadDeliveryContextService.is_joker_taken(
            delivery, cache={} if cache is None else cache
        )

    def _create_member_with_pickup_location(self, pickup_location=None):
        member = MemberFactory.create()
        if pickup_location is None:
            pickup_location = PickupLocationFactory.create()
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=pickup_location,
            # Fixed rather than relative: these tests freeze the clock in 2026.
            valid_from=date(2025, 1, 1),
        )
        return member, pickup_location


class TestSubscriptionSync(TestEnsureBreadDeliveriesForMember):
    @patch("tapir.bakery.services.breaddelivery_service.datetime")
    def test_subscription_created_creates_bread_deliveries(self, mock_datetime):
        mock_datetime.now.return_value.date.return_value = date(2026, 3, 1)

        member, pickup_location = self._create_member_with_pickup_location()

        subscription = SubscriptionFactory.create(
            member=member,
            product=self.product,
            quantity=2,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 28),
        )

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        # 2026-03-01 is a Sunday, so the period overlaps ISO weeks 9-13 - but
        # week 9 is delivered on Wednesday 2026-02-25, before the contract
        # starts, so only weeks 10-13 count: 4 weeks × 2 quantity.
        deliveries = BreadDelivery.objects.filter(subscription=subscription)
        self.assertEqual(deliveries.count(), 8)

        cache = {}
        for delivery in deliveries.select_related("subscription"):
            self.assertEqual(
                self._derived_pickup_location_id(delivery, cache), pickup_location.id
            )

    @patch("tapir.bakery.services.breaddelivery_service.datetime")
    def test_subscription_quantity_increased_creates_more_deliveries(
        self, mock_datetime
    ):
        mock_datetime.now.return_value.date.return_value = date(2026, 3, 1)

        member, pickup_location = self._create_member_with_pickup_location()

        subscription = SubscriptionFactory.create(
            member=member,
            product=self.product,
            quantity=1,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 14),  # overlaps weeks 9-11, delivered in 10-11
        )

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)
        self.assertEqual(
            BreadDelivery.objects.filter(subscription=subscription).count(), 2
        )

        subscription.quantity = 3
        subscription.save()

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        deliveries = BreadDelivery.objects.filter(subscription=subscription)
        self.assertEqual(deliveries.count(), 6)

    @patch("tapir.bakery.services.breaddelivery_service.datetime")
    def test_subscription_quantity_decreased_removes_deliveries(self, mock_datetime):
        mock_datetime.now.return_value.date.return_value = date(2026, 3, 1)

        member, pickup_location = self._create_member_with_pickup_location()

        subscription = SubscriptionFactory.create(
            member=member,
            product=self.product,
            quantity=3,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 14),  # overlaps weeks 9-11, delivered in 10-11
        )

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)
        self.assertEqual(
            BreadDelivery.objects.filter(subscription=subscription).count(), 6
        )

        subscription.quantity = 1
        subscription.save()

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        deliveries = BreadDelivery.objects.filter(subscription=subscription)
        self.assertEqual(deliveries.count(), 2)

    @patch("tapir.bakery.services.breaddelivery_service.datetime")
    def test_subscription_without_deliveries_ignored(self, mock_datetime):
        mock_datetime.now.return_value.date.return_value = date(2026, 3, 1)

        member, pickup_location = self._create_member_with_pickup_location()

        undelivered_type = ProductTypeFactory.create(
            name="Gemüse", delivery_cycle=NO_DELIVERY[0]
        )
        monthly_product = ProductFactory.create(
            type=undelivered_type, name="Gemüse Abo"
        )

        subscription = SubscriptionFactory.create(
            member=member,
            product=monthly_product,
            quantity=2,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 28),
        )

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        deliveries = BreadDelivery.objects.filter(subscription=subscription)
        self.assertEqual(deliveries.count(), 0)


class TestPickupLocationSync(TestEnsureBreadDeliveriesForMember):
    @patch("tapir.bakery.services.breaddelivery_service.datetime")
    def test_pickup_location_change_updates_future_deliveries(self, mock_datetime):
        mock_datetime.now.return_value.date.return_value = date(2026, 3, 10)

        old_pl = PickupLocationFactory.create(name="Old Location")
        new_pl = PickupLocationFactory.create(name="New Location")

        member, _ = self._create_member_with_pickup_location(old_pl)

        subscription = SubscriptionFactory.create(
            member=member,
            product=self.product,
            quantity=1,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 28),
        )

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        deliveries = BreadDelivery.objects.filter(
            subscription=subscription
        ).select_related("subscription")
        for delivery in deliveries:
            self.assertEqual(self._derived_pickup_location_id(delivery), old_pl.id)

        member_pl = MemberPickupLocation.objects.get(member=member)
        member_pl.pickup_location = new_pl
        member_pl.save()

        cache = {}
        for delivery in deliveries:
            self.assertEqual(
                self._derived_pickup_location_id(delivery, cache),
                new_pl.id,
                f"Week {delivery.delivery_week} should resolve to the new location",
            )

    @patch("tapir.bakery.services.breaddelivery_service.datetime")
    def test_new_pickup_location_added_updates_deliveries(self, mock_datetime):
        mock_datetime.now.return_value.date.return_value = date(2026, 3, 1)

        old_pl = PickupLocationFactory.create(name="Old Location")
        new_pl = PickupLocationFactory.create(name="New Location")

        member, _ = self._create_member_with_pickup_location(old_pl)

        subscription = SubscriptionFactory.create(
            member=member,
            product=self.product,
            quantity=1,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 14),
        )

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        # 2026-03-09 is the Monday of week 11: week 10 is delivered on Wed
        # 2026-03-04, week 11 on Wed 2026-03-11.
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=new_pl,
            valid_from=date(2026, 3, 9),
        )

        deliveries = (
            BreadDelivery.objects.filter(subscription=subscription)
            .select_related("subscription")
            .order_by("year", "delivery_week")
        )
        self.assertEqual(deliveries.count(), 2)

        cache = {}
        week_10_delivery = deliveries.filter(delivery_week=10).first()
        self.assertEqual(
            self._derived_pickup_location_id(week_10_delivery, cache), old_pl.id
        )

        week_11_delivery = deliveries.filter(delivery_week=11).first()
        self.assertEqual(
            self._derived_pickup_location_id(week_11_delivery, cache), new_pl.id
        )


class TestJokerSync(TestEnsureBreadDeliveriesForMember):
    @patch("tapir.bakery.services.breaddelivery_service.datetime")
    def test_joker_added_sets_joker_taken_true(self, mock_datetime):
        mock_datetime.now.return_value.date.return_value = date(2026, 3, 1)

        member, pickup_location = self._create_member_with_pickup_location()

        subscription = SubscriptionFactory.create(
            member=member,
            product=self.product,
            quantity=1,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 14),
        )

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        deliveries = BreadDelivery.objects.filter(
            subscription=subscription
        ).select_related("subscription__member")
        for delivery in deliveries:
            self.assertFalse(self._derived_joker_taken(delivery))

        # 2026-03-04 is in week 10.
        Joker.objects.create(member=member, date=date(2026, 3, 4))

        cache = {}
        for delivery in deliveries:
            self.assertEqual(
                self._derived_joker_taken(delivery, cache),
                delivery.year == 2026 and delivery.delivery_week == 10,
                f"Week {delivery.delivery_week} joker status",
            )

    @patch("tapir.bakery.services.breaddelivery_service.datetime")
    def test_joker_removed_sets_joker_taken_false(self, mock_datetime):
        mock_datetime.now.return_value.date.return_value = date(2026, 3, 1)

        member, pickup_location = self._create_member_with_pickup_location()

        subscription = SubscriptionFactory.create(
            member=member,
            product=self.product,
            quantity=1,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 14),
        )

        joker = Joker.objects.create(member=member, date=date(2026, 3, 4))

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        delivery_week_10 = BreadDelivery.objects.select_related(
            "subscription__member"
        ).get(subscription=subscription, year=2026, delivery_week=10)
        self.assertTrue(self._derived_joker_taken(delivery_week_10))

        joker.delete()

        cache = {}
        deliveries = BreadDelivery.objects.filter(
            subscription=subscription
        ).select_related("subscription__member")
        for delivery in deliveries:
            self.assertFalse(
                self._derived_joker_taken(delivery, cache),
                f"Week {delivery.delivery_week} should not read as jokered any more",
            )

    @patch("tapir.bakery.services.breaddelivery_service.datetime")
    def test_multiple_jokers_sets_correct_weeks(self, mock_datetime):
        mock_datetime.now.return_value.date.return_value = date(2026, 3, 1)

        member, pickup_location = self._create_member_with_pickup_location()

        subscription = SubscriptionFactory.create(
            member=member,
            product=self.product,
            quantity=1,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 28),
        )

        Joker.objects.create(member=member, date=date(2026, 3, 4))  # Week 10
        Joker.objects.create(member=member, date=date(2026, 3, 18))  # Week 12

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        deliveries = BreadDelivery.objects.filter(
            subscription=subscription
        ).select_related("subscription__member")
        joker_weeks = {10, 12}

        cache = {}
        for delivery in deliveries:
            self.assertEqual(
                self._derived_joker_taken(delivery, cache),
                delivery.delivery_week in joker_weeks,
                f"Week {delivery.delivery_week} joker status",
            )


class TestSignalIntegration(TestEnsureBreadDeliveriesForMember):
    @patch("tapir.bakery.services.breaddelivery_service.datetime")
    def test_subscription_save_signal_triggers_sync(self, mock_datetime):
        mock_datetime.now.return_value.date.return_value = date(2026, 3, 1)

        member, pickup_location = self._create_member_with_pickup_location()

        subscription = SubscriptionFactory.create(
            member=member,
            product=self.product,
            quantity=1,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 14),
        )

        deliveries = BreadDelivery.objects.filter(subscription=subscription)
        self.assertEqual(deliveries.count(), 2)

    @patch("tapir.bakery.services.breaddelivery_service.datetime")
    def test_pickupLocationAndJokerSaves_doNotTouchBreadDeliveries(self, mock_datetime):
        mock_datetime.now.return_value.date.return_value = date(2026, 3, 1)

        member, _ = self._create_member_with_pickup_location()
        subscription = SubscriptionFactory.create(
            member=member,
            product=self.product,
            quantity=1,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 14),
        )
        before = list(
            BreadDelivery.objects.filter(subscription=subscription)
            .order_by("year", "delivery_week", "slot_number")
            .values_list("id", "year", "delivery_week", "slot_number", "bread_id")
        )
        self.assertEqual(len(before), 2)

        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=PickupLocationFactory.create(),
            valid_from=date(2026, 3, 2),
        )
        Joker.objects.create(member=member, date=date(2026, 3, 4))

        after = list(
            BreadDelivery.objects.filter(subscription=subscription)
            .order_by("year", "delivery_week", "slot_number")
            .values_list("id", "year", "delivery_week", "slot_number", "bread_id")
        )
        self.assertEqual(before, after)


class TestEdgeCases(TestEnsureBreadDeliveriesForMember):
    @patch("tapir.bakery.services.breaddelivery_service.datetime")
    def test_member_without_pickup_location_no_error(self, mock_datetime):
        mock_datetime.now.return_value.date.return_value = date(2026, 3, 1)

        member = MemberFactory.create()

        subscription = SubscriptionFactory.create(
            member=member,
            product=self.product,
            quantity=1,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 14),
        )

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        deliveries = BreadDelivery.objects.filter(
            subscription=subscription
        ).select_related("subscription")
        self.assertEqual(deliveries.count(), 2)
        cache = {}
        for delivery in deliveries:
            self.assertIsNone(self._derived_pickup_location_id(delivery, cache))

    @patch("tapir.bakery.services.breaddelivery_service.datetime")
    def test_expired_subscription_cleaned_up(self, mock_datetime):
        mock_datetime.now.return_value.date.return_value = date(2026, 3, 15)

        member, pickup_location = self._create_member_with_pickup_location()

        subscription = SubscriptionFactory.create(
            member=member,
            product=self.product,
            quantity=1,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 3, 1),
        )

        BreadDelivery.objects.create(
            subscription=subscription,
            year=2026,
            delivery_week=15,
            slot_number=1,
        )

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        future_delivery = BreadDelivery.objects.filter(
            subscription=subscription, year=2026, delivery_week=15
        )
        self.assertEqual(future_delivery.count(), 0)

    @patch("tapir.bakery.services.breaddelivery_service.datetime")
    def test_concurrent_sync_prevented(self, mock_datetime):
        mock_datetime.now.return_value.date.return_value = date(2026, 3, 1)

        member, pickup_location = self._create_member_with_pickup_location()

        subscription = SubscriptionFactory.create(
            member=member,
            product=self.product,
            quantity=1,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 7),
        )

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)
        count_after_first = BreadDelivery.objects.filter(
            subscription=subscription
        ).count()

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)
        count_after_second = BreadDelivery.objects.filter(
            subscription=subscription
        ).count()

        self.assertEqual(count_after_first, count_after_second)


class TestWeeksWithoutDelivery(TestEnsureBreadDeliveriesForMember):
    @patch("tapir.bakery.services.breaddelivery_service.datetime")
    def test_weeksWithoutDelivery_areSkipped(self, mock_datetime):
        mock_datetime.now.return_value.date.return_value = date(2026, 3, 2)

        growing_period = GrowingPeriodFactory.create(
            start_date=date(2026, 3, 1),
            end_date=date(2027, 2, 28),
            weeks_without_delivery=[30],
        )
        member, _ = self._create_member_with_pickup_location()
        SubscriptionFactory.create(
            member=member,
            product=self.product,
            period=growing_period,
            quantity=2,
            start_date=date(2026, 3, 2),
            end_date=date(2026, 12, 27),
        )

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        self.assertEqual(
            BreadDelivery.objects.filter(year=2026, delivery_week=30).count(), 0
        )
        self.assertEqual(
            BreadDelivery.objects.filter(year=2026, delivery_week=29).count(), 2
        )
