"""
Tests for BreadDeliveryService.ensure_bread_deliveries_for_member

These tests verify that BreadDelivery records are correctly synchronized when:
1. A Subscription is created or updated
2. A MemberPickupLocation is changed
3. A Joker is added or removed
"""

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
    """Base test class with common setup for breaddelivery sync tests."""

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        # Create a weekly product type for bread subscriptions
        enable_bakery()
        self.product_type = ProductTypeFactory.create(
            name="Brot", delivery_cycle="weekly", is_bread=True
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
        """Helper to create a member with a pickup location."""
        member = MemberFactory.create()
        if pickup_location is None:
            pickup_location = PickupLocationFactory.create()
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=pickup_location,
            # Fixed, not relative to the real today: these tests freeze the
            # clock in 2026 and the station is now resolved per delivery week.
            valid_from=date(2025, 1, 1),
        )
        return member, pickup_location


class TestSubscriptionSync(TestEnsureBreadDeliveriesForMember):
    """Tests for BreadDelivery sync when subscriptions change."""

    @patch("tapir.bakery.services.breaddelivery_service.datetime")
    def test_subscription_created_creates_bread_deliveries(self, mock_datetime):
        """When a weekly subscription is created, BreadDeliveries should be created."""
        mock_datetime.now.return_value.date.return_value = date(2026, 3, 1)

        member, pickup_location = self._create_member_with_pickup_location()

        # Create subscription for 4 weeks with quantity 2
        subscription = SubscriptionFactory.create(
            member=member,
            product=self.product,
            quantity=2,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 28),
        )

        # Trigger sync (normally called by signal)
        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        # 2026-03-01 is a Sunday, so the period overlaps ISO weeks 9-13 - but
        # week 9 is delivered on Wednesday 2026-02-25, before the contract
        # starts, so only weeks 10-13 count: 4 weeks × 2 quantity.
        deliveries = BreadDelivery.objects.filter(subscription=subscription)
        self.assertEqual(deliveries.count(), 8)

        # All deliveries resolve to the member's pickup location
        cache = {}
        for delivery in deliveries.select_related("subscription"):
            self.assertEqual(
                self._derived_pickup_location_id(delivery, cache), pickup_location.id
            )

    @patch("tapir.bakery.services.breaddelivery_service.datetime")
    def test_subscription_quantity_increased_creates_more_deliveries(
        self, mock_datetime
    ):
        """When subscription quantity increases, more BreadDeliveries should be created."""
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

        # Increase quantity
        subscription.quantity = 3
        subscription.save()

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        # Should now have 3 weeks × 3 quantity = 9 deliveries
        deliveries = BreadDelivery.objects.filter(subscription=subscription)
        self.assertEqual(deliveries.count(), 6)

    @patch("tapir.bakery.services.breaddelivery_service.datetime")
    def test_subscription_quantity_decreased_removes_deliveries(self, mock_datetime):
        """When subscription quantity decreases, excess BreadDeliveries should be removed."""
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

        # Decrease quantity
        subscription.quantity = 1
        subscription.save()

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        # Should now have 3 weeks × 1 quantity = 3 deliveries
        deliveries = BreadDelivery.objects.filter(subscription=subscription)
        self.assertEqual(deliveries.count(), 2)

    @patch("tapir.bakery.services.breaddelivery_service.datetime")
    def test_non_weekly_subscription_ignored(self, mock_datetime):
        """Subscriptions with non-weekly delivery cycle should not create BreadDeliveries."""
        mock_datetime.now.return_value.date.return_value = date(2026, 3, 1)

        member, pickup_location = self._create_member_with_pickup_location()

        # Create a non-weekly product type
        monthly_type = ProductTypeFactory.create(
            name="Gemüse", delivery_cycle="monthly"
        )
        monthly_product = ProductFactory.create(type=monthly_type, name="Gemüse Abo")

        subscription = SubscriptionFactory.create(
            member=member,
            product=monthly_product,
            quantity=2,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 28),
        )

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        # Should have no bread deliveries
        deliveries = BreadDelivery.objects.filter(subscription=subscription)
        self.assertEqual(deliveries.count(), 0)


class TestPickupLocationSync(TestEnsureBreadDeliveriesForMember):
    """Tests for BreadDelivery sync when pickup location changes."""

    @patch("tapir.bakery.services.breaddelivery_service.datetime")
    def test_pickup_location_change_updates_future_deliveries(self, mock_datetime):
        """When pickup location changes, future BreadDeliveries should be updated."""
        mock_datetime.now.return_value.date.return_value = date(2026, 3, 10)

        old_pl = PickupLocationFactory.create(name="Old Location")
        new_pl = PickupLocationFactory.create(name="New Location")

        member, _ = self._create_member_with_pickup_location(old_pl)

        subscription = SubscriptionFactory.create(
            member=member,
            product=self.product,
            quantity=1,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 28),  # 4 weeks
        )

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        deliveries = BreadDelivery.objects.filter(
            subscription=subscription
        ).select_related("subscription")
        for delivery in deliveries:
            self.assertEqual(self._derived_pickup_location_id(delivery), old_pl.id)

        # Change pickup location. No re-sync: the station is derived, so every
        # week resolves to the new one straight away.
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
        """When a new MemberPickupLocation is added, deliveries should be updated based on valid_from."""
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

        # valid_from is the Monday of week 11, so it lands between the two
        # weeks the subscription is delivered in: week 10 (Wed 2026-03-04)
        # resolves to the previous station, week 11 (Wed 2026-03-11) to the new
        # one.
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=new_pl,
            valid_from=date(2026, 3, 9),
        )

        # Each week resolves against valid_from on its own delivery date.
        deliveries = (
            BreadDelivery.objects.filter(subscription=subscription)
            .select_related("subscription")
            .order_by("year", "delivery_week")
        )
        self.assertEqual(deliveries.count(), 2)

        cache = {}
        week_10_delivery = deliveries.filter(delivery_week=10).first()
        self.assertEqual(
            self._derived_pickup_location_id(week_10_delivery, cache),
            old_pl.id,
            "Week 10 should use old location (valid_from not yet reached)",
        )

        week_11_delivery = deliveries.filter(delivery_week=11).first()
        self.assertEqual(
            self._derived_pickup_location_id(week_11_delivery, cache),
            new_pl.id,
            "Week 11 should use new location (valid_from reached)",
        )


class TestJokerSync(TestEnsureBreadDeliveriesForMember):
    """The joker status of a slot is derived from the member's jokers."""

    @patch("tapir.bakery.services.breaddelivery_service.datetime")
    def test_joker_added_sets_joker_taken_true(self, mock_datetime):
        """A joker in a week makes that week's slots read as jokered."""
        mock_datetime.now.return_value.date.return_value = date(2026, 3, 1)

        member, pickup_location = self._create_member_with_pickup_location()

        subscription = SubscriptionFactory.create(
            member=member,
            product=self.product,
            quantity=1,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 14),  # 2 weeks
        )

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        deliveries = BreadDelivery.objects.filter(
            subscription=subscription
        ).select_related("subscription__member")
        for delivery in deliveries:
            self.assertFalse(self._derived_joker_taken(delivery))

        # Add joker for week 10 (March 2-8, 2026). No re-sync needed.
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
        """Removing the joker makes the week read as delivered again."""
        mock_datetime.now.return_value.date.return_value = date(2026, 3, 1)

        member, pickup_location = self._create_member_with_pickup_location()

        subscription = SubscriptionFactory.create(
            member=member,
            product=self.product,
            quantity=1,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 14),
        )

        # Add joker first
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
        """Multiple jokers should correctly mark multiple weeks."""
        mock_datetime.now.return_value.date.return_value = date(2026, 3, 1)

        member, pickup_location = self._create_member_with_pickup_location()

        subscription = SubscriptionFactory.create(
            member=member,
            product=self.product,
            quantity=1,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 28),  # 4 weeks
        )

        # Add jokers for weeks 10 and 12
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
    """Integration tests verifying signals trigger the sync correctly."""

    @patch("tapir.bakery.services.breaddelivery_service.datetime")
    def test_subscription_save_signal_triggers_sync(self, mock_datetime):
        """Saving a subscription should trigger ensure_bread_deliveries_for_member via signal."""
        mock_datetime.now.return_value.date.return_value = date(2026, 3, 1)

        member, pickup_location = self._create_member_with_pickup_location()

        # Creating subscription triggers post_save signal
        subscription = SubscriptionFactory.create(
            member=member,
            product=self.product,
            quantity=1,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 14),
        )

        # Signal should have created deliveries
        deliveries = BreadDelivery.objects.filter(subscription=subscription)
        self.assertEqual(deliveries.count(), 2)

    @patch("tapir.bakery.services.breaddelivery_service.datetime")
    def test_pickupLocationAndJokerSaves_doNotTouchBreadDeliveries(self, mock_datetime):
        """
        The MemberPickupLocation and Joker receivers are gone: both facts are
        derived at read time, so neither event has any rows to write. This is
        what took a few hundred queries out of every location change.
        """
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
    """Tests for edge cases and error handling."""

    @patch("tapir.bakery.services.breaddelivery_service.datetime")
    def test_member_without_pickup_location_no_error(self, mock_datetime):
        """Member without pickup location should not cause errors."""
        mock_datetime.now.return_value.date.return_value = date(2026, 3, 1)

        member = MemberFactory.create()
        # No MemberPickupLocation created

        subscription = SubscriptionFactory.create(
            member=member,
            product=self.product,
            quantity=1,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 14),
        )

        # Should not raise an error
        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        # Rows are still created; they just resolve to no station.
        deliveries = BreadDelivery.objects.filter(
            subscription=subscription
        ).select_related("subscription")
        self.assertEqual(deliveries.count(), 2)
        cache = {}
        for delivery in deliveries:
            self.assertIsNone(self._derived_pickup_location_id(delivery, cache))

    @patch("tapir.bakery.services.breaddelivery_service.datetime")
    def test_expired_subscription_cleaned_up(self, mock_datetime):
        """Expired subscriptions should have future deliveries cleaned up."""
        mock_datetime.now.return_value.date.return_value = date(2026, 3, 15)

        member, pickup_location = self._create_member_with_pickup_location()

        # Subscription that ended
        subscription = SubscriptionFactory.create(
            member=member,
            product=self.product,
            quantity=1,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 3, 1),  # Ended March 1
        )

        # Manually create a "future" delivery that shouldn't exist
        BreadDelivery.objects.create(
            subscription=subscription,
            year=2026,
            delivery_week=15,  # April - should be deleted
            slot_number=1,
        )

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        # Future delivery should be cleaned up
        future_delivery = BreadDelivery.objects.filter(
            subscription=subscription, year=2026, delivery_week=15
        )
        self.assertEqual(future_delivery.count(), 0)

    @patch("tapir.bakery.services.breaddelivery_service.datetime")
    def test_concurrent_sync_prevented(self, mock_datetime):
        """Concurrent syncs for the same member should be prevented."""
        mock_datetime.now.return_value.date.return_value = date(2026, 3, 1)

        member, pickup_location = self._create_member_with_pickup_location()

        subscription = SubscriptionFactory.create(
            member=member,
            product=self.product,
            quantity=1,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 7),
        )

        # First sync
        BreadDeliveryService.ensure_bread_deliveries_for_member(member)
        count_after_first = BreadDelivery.objects.filter(
            subscription=subscription
        ).count()

        # Second sync (should not duplicate)
        BreadDeliveryService.ensure_bread_deliveries_for_member(member)
        count_after_second = BreadDelivery.objects.filter(
            subscription=subscription
        ).count()

        self.assertEqual(count_after_first, count_after_second)


class TestWeeksWithoutDelivery(TestEnsureBreadDeliveriesForMember):
    """Weeks the growing period marks as undelivered must not get bread slots."""

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
            BreadDelivery.objects.filter(year=2026, delivery_week=30).count(),
            0,
            "week 30 is marked as a week without delivery",
        )
        self.assertEqual(
            BreadDelivery.objects.filter(year=2026, delivery_week=29).count(),
            2,
            "neighbouring weeks are unaffected",
        )
