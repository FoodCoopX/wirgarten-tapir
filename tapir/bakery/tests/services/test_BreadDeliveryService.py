import datetime
from unittest.mock import patch

from tapir.bakery.models import BreadDelivery
from tapir.bakery.services.breaddelivery_service import (
    _sync_in_progress,
    ensure_bread_deliveries_for_member,
    get_weeks_in_range,
)
from tapir.bakery.tests.factories import BreadDeliveryFactory, BreadFactory
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    MemberPickupLocationFactory,
    PickupLocationFactory,
    ProductFactory,
    ProductTypeFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, set_bypass_keycloak

FROZEN_DATE = datetime.date(2026, 3, 14)  # Saturday, week 11


@patch("tapir.wirgarten.tests.factories.KeycloakUserManager.get_keycloak_client")
class TestGetWeeksInRange(TapirIntegrationTest):
    """Tests for the get_weeks_in_range utility."""

    def setUp(self):
        super().setUp()
        set_bypass_keycloak()

    def test_singleWeek_yieldsOneEntry(self, mock_kc):
        start = datetime.date(2026, 3, 9)  # Monday W11
        end = datetime.date(2026, 3, 13)  # Friday W11
        weeks = list(get_weeks_in_range(start, end))
        self.assertEqual(weeks, [(2026, 11)])

    def test_twoWeeks_yieldsTwoEntries(self, mock_kc):
        start = datetime.date(2026, 3, 9)  # Monday W11
        end = datetime.date(2026, 3, 16)  # Monday W12
        weeks = list(get_weeks_in_range(start, end))
        self.assertEqual(weeks, [(2026, 11), (2026, 12)])

    def test_sameDay_yieldsOneEntry(self, mock_kc):
        d = datetime.date(2026, 3, 9)
        weeks = list(get_weeks_in_range(d, d))
        self.assertEqual(len(weeks), 1)

    def test_endBeforeStart_yieldsNothing(self, mock_kc):
        start = datetime.date(2026, 3, 16)
        end = datetime.date(2026, 3, 9)
        weeks = list(get_weeks_in_range(start, end))
        self.assertEqual(weeks, [])

    def test_crossYearBoundary_yieldsCorrectIsoWeeks(self, mock_kc):
        start = datetime.date(2025, 12, 29)  # ISO week 1 of 2026
        end = datetime.date(2026, 1, 5)  # ISO week 2 of 2026 (Mon)
        weeks = list(get_weeks_in_range(start, end))
        # Dec 29 is W1, +7 days = Jan 5 is W2
        self.assertEqual(weeks, [(2026, 1), (2026, 2)])


@patch("tapir.wirgarten.tests.factories.KeycloakUserManager.get_keycloak_client")
@patch("tapir.bakery.services.breaddelivery_service.datetime")
class TestEnsureBreadDeliveries(TapirIntegrationTest):
    def setUp(self):
        super().setUp()
        set_bypass_keycloak()
        _sync_in_progress.clear()

    def _freeze_date(self, mock_datetime, date=FROZEN_DATE):
        mock_datetime.now.return_value.date.return_value = date
        mock_datetime.side_effect = lambda *args, **kwargs: datetime.datetime(
            *args, **kwargs
        )

    def _create_weekly_product_type(self):
        return ProductTypeFactory.create(name="Brot", delivery_cycle="weekly")

    def _create_member_with_pickup(self):
        member = MemberFactory.create()
        pl = PickupLocationFactory.create()
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=pl,
            valid_from=FROZEN_DATE - datetime.timedelta(days=30),
        )
        return member, pl

    def _create_subscription(
        self, member, product_type, start_date, end_date, quantity=1
    ):
        period = GrowingPeriodFactory.create(
            start_date=start_date,
            end_date=end_date,
        )
        product = ProductFactory.create(type=product_type)
        return SubscriptionFactory.create(
            member=member,
            product=product,
            period=period,
            start_date=start_date,
            end_date=end_date,
            quantity=quantity,
        )

    # ══════════════════════════════════════════════════════════════════
    # REENTRANCY GUARD
    # ══════════════════════════════════════════════════════════════════

    def test_reentrancyGuard_secondCallSkipped(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()

        # Simulate already in progress
        _sync_in_progress.add(member.pk)

        # Should return immediately without error
        ensure_bread_deliveries_for_member(member)

        # No deliveries created
        self.assertEqual(
            BreadDelivery.objects.filter(subscription__member=member).count(), 0
        )

        _sync_in_progress.discard(member.pk)

    def test_reentrancyGuard_clearedAfterCompletion(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()

        ensure_bread_deliveries_for_member(member)

        self.assertNotIn(member.pk, _sync_in_progress)

    def test_reentrancyGuard_clearedEvenOnError(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()

        with patch(
            "tapir.bakery.services.breaddelivery_service._sync_deliveries",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertRaises(RuntimeError):
                ensure_bread_deliveries_for_member(member)

        self.assertNotIn(member.pk, _sync_in_progress)

    # ══════════════════════════════════════════════════════════════════
    # NO SUBSCRIPTIONS
    # ══════════════════════════════════════════════════════════════════

    def test_noSubscriptions_noDeliveriesCreated(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()

        ensure_bread_deliveries_for_member(member)

        self.assertEqual(
            BreadDelivery.objects.filter(subscription__member=member).count(), 0
        )

    # ══════════════════════════════════════════════════════════════════
    # NON-WEEKLY SUBSCRIPTION SKIPPED
    # ══════════════════════════════════════════════════════════════════

    def test_nonWeeklySubscription_noDeliveriesCreated(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()

        monthly_type = ProductTypeFactory.create(
            name="Monatsbox", delivery_cycle="monthly"
        )
        self._create_subscription(
            member,
            monthly_type,
            start_date=FROZEN_DATE,
            end_date=FROZEN_DATE + datetime.timedelta(weeks=4),
        )

        ensure_bread_deliveries_for_member(member)

        self.assertEqual(
            BreadDelivery.objects.filter(subscription__member=member).count(), 0
        )

    # ══════════════════════════════════════════════════════════════════
    # CREATES DELIVERIES FOR WEEKLY SUBSCRIPTION
    # ══════════════════════════════════════════════════════════════════

    def test_weeklySubscription_createsDeliveriesForEachWeek(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()

        start = FROZEN_DATE
        end = FROZEN_DATE + datetime.timedelta(weeks=3)  # ~4 weeks
        sub = self._create_subscription(member, pt, start, end, quantity=1)

        ensure_bread_deliveries_for_member(member)

        weeks = list(get_weeks_in_range(start, end))
        deliveries = BreadDelivery.objects.filter(subscription=sub)
        self.assertEqual(deliveries.count(), len(weeks))

    def test_weeklySubscription_quantity2_creates2DeliveriesPerWeek(
        self, mock_dt, mock_kc
    ):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()

        start = FROZEN_DATE
        end = FROZEN_DATE + datetime.timedelta(weeks=1)
        sub = self._create_subscription(member, pt, start, end, quantity=2)

        ensure_bread_deliveries_for_member(member)

        weeks = list(get_weeks_in_range(start, end))
        deliveries = BreadDelivery.objects.filter(subscription=sub)
        self.assertEqual(deliveries.count(), len(weeks) * 2)

        # Each week should have slot_number 1 and 2
        for year, week in weeks:
            week_deliveries = deliveries.filter(year=year, delivery_week=week)
            self.assertEqual(week_deliveries.count(), 2)
            slots = set(week_deliveries.values_list("slot_number", flat=True))
            self.assertEqual(slots, {1, 2})

    # ══════════════════════════════════════════════════════════════════
    # PICKUP LOCATION ASSIGNMENT
    # ══════════════════════════════════════════════════════════════════

    def test_createdDeliveries_haveCorrectPickupLocation(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()

        start = FROZEN_DATE
        end = FROZEN_DATE + datetime.timedelta(weeks=1)
        sub = self._create_subscription(member, pt, start, end, quantity=1)

        ensure_bread_deliveries_for_member(member)

        delivery = BreadDelivery.objects.filter(subscription=sub).first()
        self.assertIsNotNone(delivery)
        self.assertEqual(delivery.pickup_location_id, pl.id)

    def test_createdDeliveries_breadIsNone(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()

        start = FROZEN_DATE
        end = FROZEN_DATE + datetime.timedelta(weeks=1)
        sub = self._create_subscription(member, pt, start, end, quantity=1)

        ensure_bread_deliveries_for_member(member)

        for delivery in BreadDelivery.objects.filter(subscription=sub):
            self.assertIsNone(delivery.bread)

    # ══════════════════════════════════════════════════════════════════
    # IDEMPOTENCY — running twice doesn't duplicate
    # ══════════════════════════════════════════════════════════════════

    def test_runTwice_doesNotDuplicate(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()

        start = FROZEN_DATE
        end = FROZEN_DATE + datetime.timedelta(weeks=2)
        sub = self._create_subscription(member, pt, start, end, quantity=1)

        ensure_bread_deliveries_for_member(member)
        count_after_first = BreadDelivery.objects.filter(subscription=sub).count()

        ensure_bread_deliveries_for_member(member)
        count_after_second = BreadDelivery.objects.filter(subscription=sub).count()

        self.assertEqual(count_after_first, count_after_second)

    # ══════════════════════════════════════════════════════════════════
    # REMOVES EXCESS DELIVERIES WHEN QUANTITY DECREASES
    # ══════════════════════════════════════════════════════════════════

    def test_quantityDecreased_removesExcessDeliveries(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()

        start = FROZEN_DATE
        end = FROZEN_DATE + datetime.timedelta(weeks=1)
        sub = self._create_subscription(member, pt, start, end, quantity=3)

        ensure_bread_deliveries_for_member(member)

        weeks = list(get_weeks_in_range(start, end))
        self.assertEqual(
            BreadDelivery.objects.filter(subscription=sub).count(),
            len(weeks) * 3,
        )

        # Decrease quantity
        sub.quantity = 1
        sub.save()

        ensure_bread_deliveries_for_member(member)

        self.assertEqual(
            BreadDelivery.objects.filter(subscription=sub).count(),
            len(weeks) * 1,
        )

    # ══════════════════════════════════════════════════════════════════
    # ADDS DELIVERIES WHEN QUANTITY INCREASES
    # ══════════════════════════════════════════════════════════════════

    def test_quantityIncreased_addsMoreDeliveries(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()

        start = FROZEN_DATE
        end = FROZEN_DATE + datetime.timedelta(weeks=1)
        sub = self._create_subscription(member, pt, start, end, quantity=1)

        ensure_bread_deliveries_for_member(member)

        weeks = list(get_weeks_in_range(start, end))
        self.assertEqual(
            BreadDelivery.objects.filter(subscription=sub).count(),
            len(weeks) * 1,
        )

        # Increase quantity
        sub.quantity = 3
        sub.save()

        ensure_bread_deliveries_for_member(member)

        self.assertEqual(
            BreadDelivery.objects.filter(subscription=sub).count(),
            len(weeks) * 3,
        )

    # ══════════════════════════════════════════════════════════════════
    # DELETES DELIVERIES OUTSIDE SUBSCRIPTION PERIOD
    # ══════════════════════════════════════════════════════════════════

    def test_deliveriesOutsidePeriod_deleted(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()

        start = FROZEN_DATE
        end = FROZEN_DATE + datetime.timedelta(weeks=2)
        sub = self._create_subscription(member, pt, start, end, quantity=1)

        # Manually create a delivery outside the period
        BreadDeliveryFactory.create(
            subscription=sub,
            year=2025,
            delivery_week=1,
            slot_number=1,
            pickup_location=pl,
            bread=None,
        )

        ensure_bread_deliveries_for_member(member)

        # The out-of-period delivery should be gone
        self.assertFalse(
            BreadDelivery.objects.filter(
                subscription=sub, year=2025, delivery_week=1
            ).exists()
        )

    # ══════════════════════════════════════════════════════════════════
    # UPDATES FUTURE PICKUP LOCATIONS
    # ══════════════════════════════════════════════════════════════════

    def test_futureDeliveries_pickupLocationUpdated(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl_old = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()

        start = FROZEN_DATE
        end = FROZEN_DATE + datetime.timedelta(weeks=4)
        sub = self._create_subscription(member, pt, start, end, quantity=1)

        ensure_bread_deliveries_for_member(member)

        # Now change pickup location
        pl_new = PickupLocationFactory.create()
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=pl_new,
            valid_from=FROZEN_DATE - datetime.timedelta(days=1),
        )

        ensure_bread_deliveries_for_member(member)

        # Current and future week deliveries should point to new location
        current_iso = FROZEN_DATE.isocalendar()
        future_deliveries = BreadDelivery.objects.filter(
            subscription=sub,
            year=current_iso[0],
            delivery_week__gte=current_iso[1],
        )
        for d in future_deliveries:
            self.assertEqual(d.pickup_location_id, pl_new.id)

    # ══════════════════════════════════════════════════════════════════
    # CLEANUP EXPIRED SUBSCRIPTIONS
    # ══════════════════════════════════════════════════════════════════

    def test_expiredSubscription_futureDeliveriesDeleted(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()

        # Subscription ended yesterday
        start = FROZEN_DATE - datetime.timedelta(weeks=4)
        end = FROZEN_DATE - datetime.timedelta(days=1)
        sub = self._create_subscription(member, pt, start, end, quantity=1)

        # Manually create a future delivery for the expired sub
        current_iso = FROZEN_DATE.isocalendar()
        BreadDeliveryFactory.create(
            subscription=sub,
            year=current_iso[0],
            delivery_week=current_iso[1] + 1,
            slot_number=1,
            pickup_location=pl,
            bread=None,
        )

        ensure_bread_deliveries_for_member(member)

        # Future delivery for expired sub should be gone
        future = BreadDelivery.objects.filter(
            subscription=sub,
            year=current_iso[0],
            delivery_week__gt=current_iso[1],
        )
        self.assertEqual(future.count(), 0)

    # ══════════════════════════════════════════════════════════════════
    # EXPIRED SUB — PAST DELIVERIES KEPT
    # ══════════════════════════════════════════════════════════════════

    def test_expiredSubscription_pastDeliveriesKept(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()

        start = FROZEN_DATE - datetime.timedelta(weeks=4)
        end = FROZEN_DATE - datetime.timedelta(days=1)
        sub = self._create_subscription(member, pt, start, end, quantity=1)

        # Past delivery (before current week)
        current_iso = FROZEN_DATE.isocalendar()
        past_week = current_iso[1] - 2
        BreadDeliveryFactory.create(
            subscription=sub,
            year=current_iso[0],
            delivery_week=past_week,
            slot_number=1,
            pickup_location=pl,
            bread=None,
        )

        ensure_bread_deliveries_for_member(member)

        # Past delivery should still exist
        self.assertTrue(
            BreadDelivery.objects.filter(
                subscription=sub,
                year=current_iso[0],
                delivery_week=past_week,
            ).exists()
        )

    # ══════════════════════════════════════════════════════════════════
    # MULTIPLE SUBSCRIPTIONS — EACH SYNCED INDEPENDENTLY
    # ══════════════════════════════════════════════════════════════════

    def test_multipleWeeklySubscriptions_eachSynced(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()

        start = FROZEN_DATE
        end = FROZEN_DATE + datetime.timedelta(weeks=2)

        sub1 = self._create_subscription(member, pt, start, end, quantity=1)
        sub2 = self._create_subscription(member, pt, start, end, quantity=2)

        ensure_bread_deliveries_for_member(member)

        weeks = list(get_weeks_in_range(start, end))
        self.assertEqual(
            BreadDelivery.objects.filter(subscription=sub1).count(),
            len(weeks) * 1,
        )
        self.assertEqual(
            BreadDelivery.objects.filter(subscription=sub2).count(),
            len(weeks) * 2,
        )

    # ══════════════════════════════════════════════════════════════════
    # NO PICKUP LOCATION — DELIVERIES STILL CREATED
    # ══════════════════════════════════════════════════════════════════

    def test_noPickupLocation_deliveriesCreatedWithNone(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member = MemberFactory.create()
        # No pickup location assigned
        pt = self._create_weekly_product_type()

        start = FROZEN_DATE
        end = FROZEN_DATE + datetime.timedelta(weeks=1)
        sub = self._create_subscription(member, pt, start, end, quantity=1)

        ensure_bread_deliveries_for_member(member)

        deliveries = BreadDelivery.objects.filter(subscription=sub)
        self.assertTrue(deliveries.exists())
        for d in deliveries:
            self.assertIsNone(d.pickup_location)

    # ══════════════════════════════════════════════════════════════════
    # PRESERVES EXISTING BREAD ASSIGNMENTS
    # ══════════════════════════════════════════════════════════════════

    def test_existingDeliveryWithBread_breadPreserved(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()

        start = FROZEN_DATE
        end = FROZEN_DATE + datetime.timedelta(weeks=1)
        sub = self._create_subscription(member, pt, start, end, quantity=1)

        ensure_bread_deliveries_for_member(member)

        # Assign a bread to the delivery
        bread = BreadFactory.create(name="Roggenbrot")
        delivery = BreadDelivery.objects.filter(subscription=sub).first()
        delivery.bread = bread
        delivery.save()

        # Sync again
        ensure_bread_deliveries_for_member(member)

        delivery.refresh_from_db()
        self.assertEqual(delivery.bread_id, bread.id)
