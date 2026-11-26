import datetime
from unittest.mock import patch

from django.test import override_settings

from tapir.bakery.models import BreadDelivery
from tapir.bakery.services.bread_delivery_context_service import (
    BreadDeliveryContextService,
)
from tapir.bakery.services.breaddelivery_service import BreadDeliveryService
from tapir.bakery.tests.factories import (
    BreadDeliveryFactory,
    BreadFactory,
    offer_bread_at_pickup_location,
)
from tapir.pickup_locations.services.member_pickup_location_setter import (
    MemberPickupLocationSetter,
)
from tapir.pickup_locations.tests.factories import (
    create_pickup_location_with_opening_times,
)
from tapir.utils.shortcuts import week_to_monday
from tapir.wirgarten.constants import NO_DELIVERY
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.service.delivery import get_next_delivery_date
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    MemberPickupLocationFactory,
    PickupLocationFactory,
    ProductFactory,
    ProductTypeFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone

FROZEN_DATE = datetime.date(2026, 3, 14)  # Saturday, week 11


def delivered_weeks(start, end):
    """
    Reimplemented rather than imported so the assertions stay independent of
    the service under test.
    """
    return [
        (year, week)
        for year, week in BreadDeliveryService.get_weeks_in_range(start, end)
        if start <= get_next_delivery_date(week_to_monday(year, week)) <= end
    ]


@patch(
    "tapir.accounts.services.keycloak_user_manager.KeycloakUserManager.get_keycloak_client"
)
class TestGetWeeksInRange(TapirIntegrationTest):
    def test_singleWeek_yieldsOneEntry(self, mock_kc):
        start = datetime.date(2026, 3, 9)  # Monday W11
        end = datetime.date(2026, 3, 13)  # Friday W11
        weeks = list(BreadDeliveryService.get_weeks_in_range(start, end))
        self.assertEqual(weeks, [(2026, 11)])

    def test_twoWeeks_yieldsTwoEntries(self, mock_kc):
        start = datetime.date(2026, 3, 9)  # Monday W11
        end = datetime.date(2026, 3, 16)  # Monday W12
        weeks = list(BreadDeliveryService.get_weeks_in_range(start, end))
        self.assertEqual(weeks, [(2026, 11), (2026, 12)])

    def test_sameDay_yieldsOneEntry(self, mock_kc):
        d = datetime.date(2026, 3, 9)
        weeks = list(BreadDeliveryService.get_weeks_in_range(d, d))
        self.assertEqual(len(weeks), 1)

    def test_endBeforeStart_yieldsNothing(self, mock_kc):
        start = datetime.date(2026, 3, 16)
        end = datetime.date(2026, 3, 9)
        weeks = list(BreadDeliveryService.get_weeks_in_range(start, end))
        self.assertEqual(weeks, [])

    def test_crossYearBoundary_yieldsCorrectIsoWeeks(self, mock_kc):
        start = datetime.date(2025, 12, 29)  # ISO week 1 of 2026
        end = datetime.date(2026, 1, 5)  # ISO week 2 of 2026 (Mon)
        weeks = list(BreadDeliveryService.get_weeks_in_range(start, end))
        self.assertEqual(weeks, [(2026, 1), (2026, 2)])

    def test_endWeekdayBeforeStartWeekday_stillYieldsFinalWeek(self, mock_kc):
        start = datetime.date(2025, 1, 1)  # Wednesday, W1
        end = datetime.date(2025, 6, 30)  # Monday, W27
        weeks = list(BreadDeliveryService.get_weeks_in_range(start, end))
        self.assertEqual(weeks[0], (2025, 1))
        self.assertEqual(weeks[-1], (2025, 27))

    def test_periodShortenedToEarlierWeekday_stillYieldsFinalWeek(self, mock_kc):
        start = datetime.date(2026, 3, 1)  # Sunday, W9
        end = datetime.date(2026, 11, 18)  # Wednesday, W47
        weeks = list(BreadDeliveryService.get_weeks_in_range(start, end))
        self.assertEqual(weeks[0], (2026, 9))
        self.assertEqual(weeks[-1], (2026, 47))

    def test_endBeforeStartWithinSameIsoWeek_yieldsNothing(self, mock_kc):
        start = datetime.date(2026, 3, 13)  # Friday, W11
        end = datetime.date(2026, 3, 12)  # Thursday, W11
        weeks = list(BreadDeliveryService.get_weeks_in_range(start, end))
        self.assertEqual(weeks, [])


@override_settings(BAKERY_ENABLED=True)
@patch(
    "tapir.accounts.services.keycloak_user_manager.KeycloakUserManager.get_keycloak_client"
)
@patch("tapir.bakery.services.breaddelivery_service.datetime")
class TestEnsureBreadDeliveries(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()

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

    def test_noSubscriptions_noDeliveriesCreated(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        self.assertEqual(
            BreadDelivery.objects.filter(subscription__member=member).count(), 0
        )

    def test_subscriptionWithoutDeliveries_noDeliveriesCreated(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()

        undelivered_type = ProductTypeFactory.create(
            name="Anteil ohne Lieferung", delivery_cycle=NO_DELIVERY[0]
        )
        self._create_subscription(
            member,
            undelivered_type,
            start_date=FROZEN_DATE,
            end_date=FROZEN_DATE + datetime.timedelta(weeks=4),
        )

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        self.assertEqual(
            BreadDelivery.objects.filter(subscription__member=member).count(), 0
        )

    def test_weeklySubscription_createsDeliveriesForEachWeek(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()

        start = FROZEN_DATE
        end = FROZEN_DATE + datetime.timedelta(weeks=3)
        sub = self._create_subscription(member, pt, start, end, quantity=1)

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        weeks = delivered_weeks(start, end)
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

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        weeks = delivered_weeks(start, end)
        deliveries = BreadDelivery.objects.filter(subscription=sub)
        self.assertEqual(deliveries.count(), len(weeks) * 2)

        for year, week in weeks:
            week_deliveries = deliveries.filter(year=year, delivery_week=week)
            self.assertEqual(week_deliveries.count(), 2)
            slots = set(week_deliveries.values_list("slot_number", flat=True))
            self.assertEqual(slots, {1, 2})

    def test_createdDeliveries_haveCorrectPickupLocation(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()

        start = FROZEN_DATE
        end = FROZEN_DATE + datetime.timedelta(weeks=1)
        sub = self._create_subscription(member, pt, start, end, quantity=1)

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        delivery = BreadDelivery.objects.filter(subscription=sub).first()
        self.assertIsNotNone(delivery)
        self.assertEqual(
            BreadDeliveryContextService.get_pickup_location_id(delivery, cache={}),
            pl.id,
        )

    def test_createdDeliveries_breadIsNone(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()

        start = FROZEN_DATE
        end = FROZEN_DATE + datetime.timedelta(weeks=1)
        sub = self._create_subscription(member, pt, start, end, quantity=1)

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        for delivery in BreadDelivery.objects.filter(subscription=sub):
            self.assertIsNone(delivery.bread)

    def test_runTwice_doesNotDuplicate(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()

        start = FROZEN_DATE
        end = FROZEN_DATE + datetime.timedelta(weeks=2)
        sub = self._create_subscription(member, pt, start, end, quantity=1)

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)
        count_after_first = BreadDelivery.objects.filter(subscription=sub).count()

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)
        count_after_second = BreadDelivery.objects.filter(subscription=sub).count()

        self.assertEqual(count_after_first, count_after_second)

    def test_quantityDecreased_removesExcessDeliveries(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()

        start = FROZEN_DATE
        end = FROZEN_DATE + datetime.timedelta(weeks=1)
        sub = self._create_subscription(member, pt, start, end, quantity=3)

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        weeks = delivered_weeks(start, end)
        self.assertEqual(
            BreadDelivery.objects.filter(subscription=sub).count(),
            len(weeks) * 3,
        )

        sub.quantity = 1
        sub.save()

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        self.assertEqual(
            BreadDelivery.objects.filter(subscription=sub).count(),
            len(weeks) * 1,
        )

    def test_quantityIncreased_addsMoreDeliveries(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()

        start = FROZEN_DATE
        end = FROZEN_DATE + datetime.timedelta(weeks=1)
        sub = self._create_subscription(member, pt, start, end, quantity=1)

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        weeks = delivered_weeks(start, end)
        self.assertEqual(
            BreadDelivery.objects.filter(subscription=sub).count(),
            len(weeks) * 1,
        )

        sub.quantity = 3
        sub.save()

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        self.assertEqual(
            BreadDelivery.objects.filter(subscription=sub).count(),
            len(weeks) * 3,
        )

    def test_deliveriesOutsidePeriod_deleted(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()

        start = FROZEN_DATE
        end = FROZEN_DATE + datetime.timedelta(weeks=2)
        sub = self._create_subscription(member, pt, start, end, quantity=1)

        BreadDeliveryFactory.create(
            subscription=sub,
            year=2025,
            delivery_week=1,
            slot_number=1,
            pickup_location=pl,
            bread=None,
        )

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        self.assertFalse(
            BreadDelivery.objects.filter(
                subscription=sub, year=2025, delivery_week=1
            ).exists()
        )

    def test_futureDeliveries_pickupLocationUpdated(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl_old = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()

        start = FROZEN_DATE
        end = FROZEN_DATE + datetime.timedelta(weeks=4)
        sub = self._create_subscription(member, pt, start, end, quantity=1)

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        pl_new = PickupLocationFactory.create()
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=pl_new,
            valid_from=FROZEN_DATE - datetime.timedelta(days=14),
        )

        current_iso = FROZEN_DATE.isocalendar()
        future_deliveries = BreadDelivery.objects.filter(
            subscription=sub,
            year=current_iso[0],
            delivery_week__gte=current_iso[1],
        ).select_related("subscription")
        cache = {}
        for d in future_deliveries:
            self.assertEqual(
                BreadDeliveryContextService.get_pickup_location_id(d, cache=cache),
                pl_new.id,
            )

    def test_expiredSubscription_futureDeliveriesDeleted(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()

        start = FROZEN_DATE - datetime.timedelta(weeks=4)
        end = FROZEN_DATE - datetime.timedelta(days=1)
        sub = self._create_subscription(member, pt, start, end, quantity=1)

        current_iso = FROZEN_DATE.isocalendar()
        BreadDeliveryFactory.create(
            subscription=sub,
            year=current_iso[0],
            delivery_week=current_iso[1] + 1,
            slot_number=1,
            pickup_location=pl,
            bread=None,
        )

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        future = BreadDelivery.objects.filter(
            subscription=sub,
            year=current_iso[0],
            delivery_week__gt=current_iso[1],
        )
        self.assertEqual(future.count(), 0)

    def test_expiredSubscription_pastDeliveriesKept(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()

        start = FROZEN_DATE - datetime.timedelta(weeks=4)
        end = FROZEN_DATE - datetime.timedelta(days=1)
        sub = self._create_subscription(member, pt, start, end, quantity=1)

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

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        self.assertTrue(
            BreadDelivery.objects.filter(
                subscription=sub,
                year=current_iso[0],
                delivery_week=past_week,
            ).exists()
        )

    def test_multipleWeeklySubscriptions_eachSynced(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()

        start = FROZEN_DATE
        end = FROZEN_DATE + datetime.timedelta(weeks=2)

        sub1 = self._create_subscription(member, pt, start, end, quantity=1)
        sub2 = self._create_subscription(member, pt, start, end, quantity=2)

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        weeks = delivered_weeks(start, end)
        self.assertEqual(
            BreadDelivery.objects.filter(subscription=sub1).count(),
            len(weeks) * 1,
        )
        self.assertEqual(
            BreadDelivery.objects.filter(subscription=sub2).count(),
            len(weeks) * 2,
        )

    def test_noPickupLocation_deliveriesCreatedWithNone(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member = MemberFactory.create()
        pt = self._create_weekly_product_type()

        start = FROZEN_DATE
        end = FROZEN_DATE + datetime.timedelta(weeks=1)
        sub = self._create_subscription(member, pt, start, end, quantity=1)

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        deliveries = BreadDelivery.objects.filter(subscription=sub).select_related(
            "subscription"
        )
        self.assertTrue(deliveries.exists())
        cache = {}
        for d in deliveries:
            self.assertIsNone(
                BreadDeliveryContextService.get_pickup_location_id(d, cache=cache)
            )

    def test_existingDeliveryWithBread_breadPreserved(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()

        start = FROZEN_DATE
        end = FROZEN_DATE + datetime.timedelta(weeks=1)
        sub = self._create_subscription(member, pt, start, end, quantity=1)

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        bread = BreadFactory.create(name="Roggenbrot")
        delivery = BreadDelivery.objects.filter(subscription=sub).first()
        offer_bread_at_pickup_location(
            bread, pl, year=delivery.year, delivery_week=delivery.delivery_week
        )
        delivery.bread = bread
        delivery.save()

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        delivery.refresh_from_db()
        self.assertEqual(delivery.bread_id, bread.id)

    def _create_subscription_in_period(
        self, member, product_type, start_date, end_date, period, quantity=1
    ):
        product = ProductFactory.create(type=product_type)
        return SubscriptionFactory.create(
            member=member,
            product=product,
            period=period,
            start_date=start_date,
            end_date=end_date,
            quantity=quantity,
        )

    def test_weekWithoutDelivery_noSlotsCreated(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()

        start = datetime.date(2026, 3, 9)  # Monday W11
        end = datetime.date(2026, 4, 5)  # Sunday W14
        period = GrowingPeriodFactory.create(
            start_date=start, end_date=end, weeks_without_delivery=[13]
        )
        sub = self._create_subscription_in_period(member, pt, start, end, period)

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        self.assertEqual(
            BreadDelivery.objects.filter(
                subscription=sub, year=2026, delivery_week=13
            ).count(),
            0,
        )
        for week in [11, 12, 14]:
            self.assertEqual(
                BreadDelivery.objects.filter(
                    subscription=sub, year=2026, delivery_week=week
                ).count(),
                1,
                f"week {week} is delivered and must keep its slot",
            )

    def test_weekWithoutDelivery_existingRowsDeleted(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()

        start = datetime.date(2026, 3, 9)  # Monday W11
        end = datetime.date(2026, 4, 5)  # Sunday W14
        period = GrowingPeriodFactory.create(start_date=start, end_date=end)
        sub = self._create_subscription_in_period(member, pt, start, end, period)

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)
        self.assertTrue(
            BreadDelivery.objects.filter(
                subscription=sub, year=2026, delivery_week=13
            ).exists()
        )

        period.weeks_without_delivery = [13]
        period.save()

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        self.assertEqual(
            BreadDelivery.objects.filter(
                subscription=sub, year=2026, delivery_week=13
            ).count(),
            0,
        )

    def test_resyncForGrowingPeriod_weekWithoutDeliveryAdded_removesItsSlots(
        self, mock_dt, mock_kc
    ):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()

        start = datetime.date(2026, 3, 9)
        end = datetime.date(2026, 4, 5)
        period = GrowingPeriodFactory.create(start_date=start, end_date=end)
        sub = self._create_subscription_in_period(member, pt, start, end, period)

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)
        self.assertTrue(
            BreadDelivery.objects.filter(
                subscription=sub, year=2026, delivery_week=13
            ).exists()
        )

        period.weeks_without_delivery = [13]
        period.save()
        BreadDeliveryService.resync_bread_deliveries_for_growing_period(period)

        self.assertEqual(
            BreadDelivery.objects.filter(
                subscription=sub, year=2026, delivery_week=13
            ).count(),
            0,
        )

    def test_oddWeeksCycle_onlyOddWeeksGetSlots(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()
        pt = ProductTypeFactory.create(name="Brot 14-tägig", delivery_cycle="odd_weeks")

        start = datetime.date(2026, 3, 9)  # Monday W11
        end = datetime.date(2026, 4, 5)  # Sunday W14
        period = GrowingPeriodFactory.create(start_date=start, end_date=end)
        sub = self._create_subscription_in_period(member, pt, start, end, period)

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        weeks = set(
            BreadDelivery.objects.filter(subscription=sub).values_list(
                "delivery_week", flat=True
            )
        )
        self.assertEqual(weeks, {11, 13})

    def test_missingLowerSlot_renumberedInsteadOfDuplicated(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()

        # A whole ISO week, so the week's delivery date falls inside it.
        start = FROZEN_DATE - datetime.timedelta(days=FROZEN_DATE.weekday())
        end = start + datetime.timedelta(days=6)
        sub = self._create_subscription(member, pt, start, end, quantity=2)

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        year, week, _ = FROZEN_DATE.isocalendar()
        BreadDelivery.objects.filter(
            subscription=sub, year=year, delivery_week=week, slot_number=1
        ).delete()

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        slots = sorted(
            BreadDelivery.objects.filter(
                subscription=sub, year=year, delivery_week=week
            ).values_list("slot_number", flat=True)
        )
        self.assertEqual(slots, [1, 2])

    def test_slotRenumbering_keepsTheBreadChoice(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, pl = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()

        # A whole ISO week, so the week's delivery date falls inside it.
        start = FROZEN_DATE - datetime.timedelta(days=FROZEN_DATE.weekday())
        end = start + datetime.timedelta(days=6)
        sub = self._create_subscription(member, pt, start, end, quantity=2)

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        year, week, _ = FROZEN_DATE.isocalendar()
        bread = BreadFactory.create(name="Roggenbrot")
        offer_bread_at_pickup_location(bread, pl, year=year, delivery_week=week)
        slot_two = BreadDelivery.objects.get(
            subscription=sub, year=year, delivery_week=week, slot_number=2
        )
        slot_two.bread = bread
        slot_two.save()

        BreadDelivery.objects.filter(
            subscription=sub, year=year, delivery_week=week, slot_number=1
        ).delete()
        sub.quantity = 1
        sub.save()

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        slot_two.refresh_from_db()
        self.assertEqual(slot_two.slot_number, 1)
        self.assertEqual(slot_two.bread_id, bread.id)

    def _choose_bread(self, delivery, pickup_location):
        bread = BreadFactory.create()
        offer_bread_at_pickup_location(
            bread,
            pickup_location,
            year=delivery.year,
            delivery_week=delivery.delivery_week,
        )
        delivery.bread = bread
        delivery.save()
        return bread

    def _move_member(self, member, pickup_location, valid_from):
        MemberPickupLocationSetter.link_member_to_pickup_location(
            pickup_location_id=pickup_location.id,
            member=member,
            valid_from=valid_from,
            actor=member,
            cache={},
        )

    def test_movedStation_breadNotBakedThere_isCleared(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, old_location = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()
        sub = self._create_subscription(
            member, pt, FROZEN_DATE, FROZEN_DATE + datetime.timedelta(weeks=2)
        )
        BreadDeliveryService.ensure_bread_deliveries_for_member(member)
        delivery = BreadDelivery.objects.filter(subscription=sub).last()
        self._choose_bread(delivery, old_location)

        # Delivered on Friday, while the bread is baked for Wednesday only.
        new_location = create_pickup_location_with_opening_times(open_days=[4])
        self._move_member(member, new_location, FROZEN_DATE)

        delivery.refresh_from_db()
        self.assertIsNone(delivery.bread)

    def test_movedStation_breadAlsoBakedThere_isKept(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, old_location = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()
        sub = self._create_subscription(
            member, pt, FROZEN_DATE, FROZEN_DATE + datetime.timedelta(weeks=2)
        )
        BreadDeliveryService.ensure_bread_deliveries_for_member(member)
        delivery = BreadDelivery.objects.filter(subscription=sub).last()
        bread = self._choose_bread(delivery, old_location)

        # Delivered on the same day as the old station.
        new_location = create_pickup_location_with_opening_times(open_days=[2])
        self._move_member(member, new_location, FROZEN_DATE)

        delivery.refresh_from_db()
        self.assertEqual(delivery.bread_id, bread.id)

    def test_movedStation_pastWeeks_areLeftAlone(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, old_location = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()
        sub = self._create_subscription(
            member, pt, FROZEN_DATE - datetime.timedelta(weeks=3), FROZEN_DATE
        )
        BreadDeliveryService.ensure_bread_deliveries_for_member(member)
        past = (
            BreadDelivery.objects.filter(subscription=sub)
            .order_by("year", "delivery_week")
            .first()
        )
        bread = self._choose_bread(past, old_location)

        self._move_member(member, PickupLocationFactory.create(), FROZEN_DATE)

        past.refresh_from_db()
        self.assertEqual(past.bread_id, bread.id)

    def _weeks_with_slots(self, member):
        return set(
            BreadDelivery.objects.filter(subscription__member=member).values_list(
                "delivery_week", flat=True
            )
        )

    def test_periodStartsAfterThatWeeksDelivery_weekGetsNoSlot(self, mock_dt, mock_kc):
        # Week 11 is delivered on Wednesday.
        self._freeze_date(mock_dt)
        member, _ = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()
        monday = FROZEN_DATE - datetime.timedelta(days=FROZEN_DATE.weekday())
        friday = monday + datetime.timedelta(days=4)
        self._create_subscription(
            member, pt, friday, monday + datetime.timedelta(days=13)
        )

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        week_11 = monday.isocalendar()[1]
        self.assertNotIn(week_11, self._weeks_with_slots(member))
        self.assertIn(week_11 + 1, self._weeks_with_slots(member))

    def test_periodEndsBeforeThatWeeksDelivery_weekGetsNoSlot(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, _ = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()
        monday = FROZEN_DATE - datetime.timedelta(days=FROZEN_DATE.weekday())
        self._create_subscription(
            member, pt, monday, monday + datetime.timedelta(days=8)
        )

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        week_11 = monday.isocalendar()[1]
        self.assertEqual(self._weeks_with_slots(member), {week_11})

    def test_wholeWeekPeriod_everyOverlappedWeekGetsSlots(self, mock_dt, mock_kc):
        self._freeze_date(mock_dt)
        member, _ = self._create_member_with_pickup()
        pt = self._create_weekly_product_type()
        monday = FROZEN_DATE - datetime.timedelta(days=FROZEN_DATE.weekday())
        self._create_subscription(
            member, pt, monday, monday + datetime.timedelta(days=20)
        )

        BreadDeliveryService.ensure_bread_deliveries_for_member(member)

        week_11 = monday.isocalendar()[1]
        self.assertEqual(
            self._weeks_with_slots(member), {week_11, week_11 + 1, week_11 + 2}
        )


@override_settings(BAKERY_ENABLED=True)
class TestClearChoicesOfBreadsForDeliveryDay(TapirIntegrationTest):
    """FROZEN_DATE is the Saturday of week 11."""

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        mock_timezone(self, datetime.datetime.combine(FROZEN_DATE, datetime.time(12)))
        self.bread = BreadFactory.create(name="Roggenbrot")

    def _choice(self, week, day, **kwargs):
        return BreadDeliveryFactory.create(
            year=2026,
            delivery_week=week,
            pickup_location=create_pickup_location_with_opening_times(open_days=[day]),
            bread=self.bread,
            **kwargs,
        )

    def _clear(self, week, day):
        return BreadDeliveryService.clear_choices_of_breads_for_delivery_day(
            [self.bread.id], 2026, week, day, cache={}
        )

    def test_laterDayOfTheWeek_isCleared(self):
        delivery = self._choice(week=11, day=6)

        self.assertEqual(self._clear(week=11, day=6), 1)
        delivery.refresh_from_db()
        self.assertIsNone(delivery.bread_id)

    def test_todayAndEarlierDaysOfTheWeek_areKept(self):
        for day in (2, 5):
            with self.subTest(day=day):
                delivery = self._choice(week=11, day=day)

                self.assertEqual(self._clear(week=11, day=day), 0)
                delivery.refresh_from_db()
                self.assertEqual(delivery.bread_id, self.bread.id)

    def test_jokeredSlot_isCleared(self):
        delivery = self._choice(week=12, day=2, joker_taken=True)

        self.assertEqual(self._clear(week=12, day=2), 1)
        delivery.refresh_from_db()
        self.assertIsNone(delivery.bread_id)

    def test_memberWhoSwitchedSinceTheRead_keepsTheNewChoice(self):
        delivery = self._choice(week=12, day=2)
        other_bread = BreadFactory.create(name="Dinkelbrot")
        found = BreadDeliveryService.get_choices_of_breads_for_delivery_day

        def switch_after_reading(*args, **kwargs):
            choices = found(*args, **kwargs)
            BreadDelivery.objects.filter(pk=delivery.pk).update(bread=other_bread)
            return choices

        with patch.object(
            BreadDeliveryService,
            "get_choices_of_breads_for_delivery_day",
            side_effect=switch_after_reading,
        ):
            cleared = self._clear(week=12, day=2)

        self.assertEqual(cleared, 0)
        delivery.refresh_from_db()
        self.assertEqual(delivery.bread_id, other_bread.id)


@override_settings(BAKERY_ENABLED=True)
class TestClearBreadsUnavailableAtPickupLocationLimits(TapirIntegrationTest):
    """A choice kept on a station change must fit the new day's limit."""

    # Far enough ahead that no day of it is over.
    FUTURE_YEAR = 2099
    WEEK = 10
    DAY = 1

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.station = create_pickup_location_with_opening_times(open_days=[self.DAY])

    def _bread(self, max_pieces):
        bread = BreadFactory.create(
            name="Saaten", max_pieces=max_pieces, min_remaining_pieces=0
        )
        offer_bread_at_pickup_location(
            bread, self.station, year=self.FUTURE_YEAR, delivery_week=self.WEEK
        )
        return bread

    def _choice(self, bread):
        return BreadDeliveryFactory.create(
            year=self.FUTURE_YEAR,
            delivery_week=self.WEEK,
            pickup_location=self.station,
            bread=bread,
        )

    def _recheck(self, delivery):
        BreadDeliveryService.clear_breads_unavailable_at_pickup_location(
            delivery.subscription.member, cache={}
        )
        delivery.refresh_from_db()

    def test_keptChoiceOverTheNewDaysLimit_isCleared(self):
        bread = self._bread(max_pieces=2)
        others = [self._choice(bread) for _ in range(2)]
        mover = self._choice(bread)

        self._recheck(mover)

        self.assertIsNone(mover.bread_id)
        for other in others:
            other.refresh_from_db()
            self.assertEqual(other.bread_id, bread.id)

    def test_keptChoiceWithinTheNewDaysLimit_isKept(self):
        bread = self._bread(max_pieces=3)
        self._choice(bread)
        self._choice(bread)
        mover = self._choice(bread)

        self._recheck(mover)

        self.assertEqual(mover.bread_id, bread.id)
