"""
Tests for breaddelivery_service.py - ensure_bread_deliveries_for_member

These tests verify that BreadDelivery records are correctly synchronized when:
1. A Subscription is created or updated
2. A MemberPickupLocation is changed
3. A Joker is added or removed
"""

from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase

from tapir.bakery.models import BreadDelivery
from tapir.bakery.services.breaddelivery_service import (
    ensure_bread_deliveries_for_member,
)
from tapir.deliveries.models import Joker
from tapir.wirgarten.models import MemberPickupLocation
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
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
        self.product_type = ProductTypeFactory.create(
            name="Brot", delivery_cycle="weekly"
        )
        self.product = ProductFactory.create(type=self.product_type, name="Brot Abo")

    def _create_member_with_pickup_location(self, pickup_location=None):
        """Helper to create a member with a pickup location."""
        member = MemberFactory.create()
        if pickup_location is None:
            pickup_location = PickupLocationFactory.create()
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=pickup_location,
            valid_from=date.today() - timedelta(days=30),
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
        ensure_bread_deliveries_for_member(member)

        # Should have 4 weeks × 2 quantity = 8 deliveries
        deliveries = BreadDelivery.objects.filter(subscription=subscription)
        self.assertEqual(deliveries.count(), 8)

        # All deliveries should have the correct pickup location
        for delivery in deliveries:
            self.assertEqual(delivery.pickup_location, pickup_location)

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
            end_date=date(2026, 3, 14),  # 2 weeks
        )

        ensure_bread_deliveries_for_member(member)
        self.assertEqual(
            BreadDelivery.objects.filter(subscription=subscription).count(), 2
        )

        # Increase quantity
        subscription.quantity = 3
        subscription.save()

        ensure_bread_deliveries_for_member(member)

        # Should now have 2 weeks × 3 quantity = 6 deliveries
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
            end_date=date(2026, 3, 14),  # 2 weeks
        )

        ensure_bread_deliveries_for_member(member)
        self.assertEqual(
            BreadDelivery.objects.filter(subscription=subscription).count(), 6
        )

        # Decrease quantity
        subscription.quantity = 1
        subscription.save()

        ensure_bread_deliveries_for_member(member)

        # Should now have 2 weeks × 1 quantity = 2 deliveries
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

        ensure_bread_deliveries_for_member(member)

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

        ensure_bread_deliveries_for_member(member)

        # All deliveries should have old pickup location
        deliveries = BreadDelivery.objects.filter(subscription=subscription)
        for delivery in deliveries:
            self.assertEqual(delivery.pickup_location, old_pl)

        # Change pickup location
        member_pl = MemberPickupLocation.objects.get(member=member)
        member_pl.pickup_location = new_pl
        member_pl.save()

        # This would normally trigger signal, but we call manually
        ensure_bread_deliveries_for_member(member)

        # Future deliveries (from current week onward) should have new pickup location
        # Week 11 (March 9-15) is current, so weeks 11, 12, 13 should be updated
        deliveries = BreadDelivery.objects.filter(subscription=subscription)
        for delivery in deliveries:
            # Year 2026, week 10 (March 2-8) is in the past
            if delivery.year == 2026 and delivery.delivery_week >= 11:
                self.assertEqual(
                    delivery.pickup_location,
                    new_pl,
                    f"Week {delivery.delivery_week} should have new pickup location",
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

        ensure_bread_deliveries_for_member(member)

        # Add new pickup location with valid_from = Monday of week 10 (March 2)
        # Week 9 Monday is Feb 23, Week 10 Monday is March 2
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=new_pl,
            valid_from=date(2026, 3, 2),  # Valid from week 10 (Monday of week 10)
        )

        ensure_bread_deliveries_for_member(member)

        # Check that deliveries use the correct pickup location based on valid_from
        deliveries = BreadDelivery.objects.filter(subscription=subscription).order_by(
            "year", "delivery_week"
        )
        self.assertEqual(deliveries.count(), 2)

        # Week 9 (Monday = Feb 23) should still use old location (Feb 23 < March 2)
        week_9_delivery = deliveries.filter(delivery_week=9).first()
        self.assertEqual(
            week_9_delivery.pickup_location,
            old_pl,
            "Week 9 should use old location (valid_from not yet reached)",
        )

        # Week 10 (Monday = March 2) should use new location (March 2 >= March 2)
        week_10_delivery = deliveries.filter(delivery_week=10).first()
        self.assertEqual(
            week_10_delivery.pickup_location,
            new_pl,
            "Week 10 should use new location (valid_from reached)",
        )


class TestJokerSync(TestEnsureBreadDeliveriesForMember):
    """Tests for BreadDelivery sync when jokers change."""

    @patch("tapir.bakery.services.breaddelivery_service.datetime")
    def test_joker_added_sets_joker_taken_true(self, mock_datetime):
        """When a joker is added, corresponding BreadDeliveries should have joker_taken=True."""
        mock_datetime.now.return_value.date.return_value = date(2026, 3, 1)

        member, pickup_location = self._create_member_with_pickup_location()

        subscription = SubscriptionFactory.create(
            member=member,
            product=self.product,
            quantity=1,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 14),  # 2 weeks
        )

        ensure_bread_deliveries_for_member(member)

        # All deliveries should have joker_taken=False
        deliveries = BreadDelivery.objects.filter(subscription=subscription)
        for delivery in deliveries:
            self.assertFalse(delivery.joker_taken)

        # Add joker for week 10 (March 2-8, 2026)
        joker = Joker.objects.create(member=member, date=date(2026, 3, 4))

        # Signal would trigger this, but we call manually
        ensure_bread_deliveries_for_member(member)

        # Delivery in week 10 should have joker_taken=True
        deliveries = BreadDelivery.objects.filter(subscription=subscription)
        for delivery in deliveries:
            if delivery.year == 2026 and delivery.delivery_week == 10:
                self.assertTrue(
                    delivery.joker_taken,
                    f"Week {delivery.delivery_week} should have joker_taken=True",
                )
            else:
                self.assertFalse(
                    delivery.joker_taken,
                    f"Week {delivery.delivery_week} should have joker_taken=False",
                )

    @patch("tapir.bakery.services.breaddelivery_service.datetime")
    def test_joker_removed_sets_joker_taken_false(self, mock_datetime):
        """When a joker is removed, corresponding BreadDeliveries should have joker_taken=False."""
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

        ensure_bread_deliveries_for_member(member)

        # Verify joker_taken is True
        delivery_week_10 = BreadDelivery.objects.get(
            subscription=subscription, year=2026, delivery_week=10
        )
        self.assertTrue(delivery_week_10.joker_taken)

        # Remove joker
        joker.delete()

        # Signal would trigger this, but we call manually
        ensure_bread_deliveries_for_member(member)

        # All deliveries should have joker_taken=False
        deliveries = BreadDelivery.objects.filter(subscription=subscription)
        for delivery in deliveries:
            self.assertFalse(
                delivery.joker_taken,
                f"Week {delivery.delivery_week} should have joker_taken=False after joker deletion",
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

        ensure_bread_deliveries_for_member(member)

        deliveries = BreadDelivery.objects.filter(subscription=subscription)
        joker_weeks = {10, 12}

        for delivery in deliveries:
            if delivery.delivery_week in joker_weeks:
                self.assertTrue(
                    delivery.joker_taken,
                    f"Week {delivery.delivery_week} should have joker_taken=True",
                )
            else:
                self.assertFalse(
                    delivery.joker_taken,
                    f"Week {delivery.delivery_week} should have joker_taken=False",
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
    def test_member_pickup_location_save_signal_triggers_sync(self, mock_datetime):
        """Saving a MemberPickupLocation should trigger sync via signal."""
        mock_datetime.now.return_value.date.return_value = date(2026, 3, 1)

        old_pl = PickupLocationFactory.create(name="Old")
        new_pl = PickupLocationFactory.create(name="New")

        member, _ = self._create_member_with_pickup_location(old_pl)

        subscription = SubscriptionFactory.create(
            member=member,
            product=self.product,
            quantity=1,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 14),
        )

        # Update pickup location - this triggers signal
        member_pl = MemberPickupLocation.objects.get(member=member)
        member_pl.pickup_location = new_pl
        member_pl.save()

        # Signal should have updated deliveries
        deliveries = BreadDelivery.objects.filter(subscription=subscription)
        for delivery in deliveries:
            self.assertEqual(delivery.pickup_location, new_pl)

    @patch("tapir.bakery.services.breaddelivery_service.datetime")
    def test_joker_save_signal_triggers_sync(self, mock_datetime):
        """Creating a Joker should trigger sync via signal."""
        mock_datetime.now.return_value.date.return_value = date(2026, 3, 1)

        member, pickup_location = self._create_member_with_pickup_location()

        subscription = SubscriptionFactory.create(
            member=member,
            product=self.product,
            quantity=1,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 14),
        )

        # Creating joker triggers post_save signal
        Joker.objects.create(member=member, date=date(2026, 3, 4))

        # Signal should have set joker_taken
        delivery = BreadDelivery.objects.get(
            subscription=subscription, year=2026, delivery_week=10
        )
        self.assertTrue(delivery.joker_taken)

    @patch("tapir.bakery.services.breaddelivery_service.datetime")
    def test_joker_delete_signal_triggers_sync(self, mock_datetime):
        """Deleting a Joker should trigger sync via signal."""
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

        # Verify joker_taken is True
        delivery = BreadDelivery.objects.get(
            subscription=subscription, year=2026, delivery_week=10
        )
        self.assertTrue(delivery.joker_taken)

        # Delete joker - triggers post_delete signal
        joker.delete()

        # Signal should have cleared joker_taken
        delivery.refresh_from_db()
        self.assertFalse(delivery.joker_taken)


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
        ensure_bread_deliveries_for_member(member)

        # Deliveries created with pickup_location=None
        deliveries = BreadDelivery.objects.filter(subscription=subscription)
        self.assertEqual(deliveries.count(), 2)
        for delivery in deliveries:
            self.assertIsNone(delivery.pickup_location)

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
            pickup_location=pickup_location,
        )

        ensure_bread_deliveries_for_member(member)

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
        ensure_bread_deliveries_for_member(member)
        count_after_first = BreadDelivery.objects.filter(
            subscription=subscription
        ).count()

        # Second sync (should not duplicate)
        ensure_bread_deliveries_for_member(member)
        count_after_second = BreadDelivery.objects.filter(
            subscription=subscription
        ).count()

        self.assertEqual(count_after_first, count_after_second)
