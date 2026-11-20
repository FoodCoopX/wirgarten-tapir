import datetime
from unittest.mock import patch, MagicMock

from tapir.deliveries.services.delivery_date_calculator import (
    DeliveryDateCalculator,
)
from tapir.subscriptions.services.admin_size_change_date_options_builder import (
    AdminSizeChangeDateOptionsBuilder,
)
from tapir.wirgarten.constants import NO_DELIVERY, WEEKLY
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    ProductFactory,
    ProductTypeFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest, mock_timezone


@patch.object(
    DeliveryDateCalculator, "is_week_delivered", autospec=True, return_value=True
)
class TestAdminSizeChangeDateOptionsBuilderBuildWeekOptions(TapirUnitTest):
    def setUp(self):
        super().setUp()
        self.growing_period = GrowingPeriodFactory.build(
            start_date=datetime.date(year=2027, month=1, day=1),
            end_date=datetime.date(year=2027, month=12, day=31),
        )
        self.product_type = ProductTypeFactory.build(delivery_cycle=WEEKLY[0])
        self.subscription = SubscriptionFactory.build(
            period=self.growing_period,
            product=ProductFactory.build(type=self.product_type),
        )

    def _build(self, next_possible_start: datetime.date):
        return AdminSizeChangeDateOptionsBuilder.build_week_options(
            subscription=self.subscription,
            next_possible_start=next_possible_start,
            cache={},
        )

    def test_buildWeekOptions_todayBeforePeriod_offersOnlyMondaysOfPeriod(
        self, _: MagicMock
    ):
        mock_timezone(test=self, now=datetime.datetime(year=2026, month=11, day=19))

        weeks = self._build(
            next_possible_start=datetime.date(year=2027, month=1, day=11)
        )

        self.assertEqual(
            [
                datetime.date(year=2027, month=1, day=4),
                datetime.date(year=2027, month=1, day=11),
                datetime.date(year=2027, month=1, day=18),
            ],
            [week.date for week in weeks[:3]],
        )
        self.assertEqual(datetime.date(year=2027, month=12, day=27), weeks[-1].date)
        self.assertTrue(weeks[0].is_before_next_possible_start)
        self.assertFalse(weeks[1].is_before_next_possible_start)

    def test_buildWeekOptions_todayInPeriod_onlyOffersDatesFromToday(
        self, _: MagicMock
    ):
        mock_timezone(test=self, now=datetime.datetime(year=2027, month=6, day=2))

        weeks = self._build(
            next_possible_start=datetime.date(year=2027, month=6, day=14)
        )

        self.assertEqual(datetime.date(year=2027, month=6, day=7), weeks[0].date)
        self.assertTrue(weeks[0].is_before_next_possible_start)

    def test_buildWeekOptions_subscriptionStartsInPeriod_onlyOffersDatesFromSubscriptionStart(
        self, _: MagicMock
    ):
        mock_timezone(test=self, now=datetime.datetime(year=2027, month=6, day=2))
        self.subscription.start_date = datetime.date(year=2027, month=7, day=12)

        weeks = self._build(
            next_possible_start=datetime.date(year=2027, month=6, day=14)
        )

        self.assertEqual(datetime.date(year=2027, month=7, day=12), weeks[0].date)

    def test_buildWeekOptions_subscriptionEndsEarly_onlyOffersDatesWithinSubscription(
        self, _: MagicMock
    ):
        mock_timezone(test=self, now=datetime.datetime(year=2027, month=6, day=2))
        self.subscription.end_date = datetime.date(year=2027, month=6, day=20)

        weeks = self._build(
            next_possible_start=datetime.date(year=2027, month=6, day=7)
        )

        self.assertEqual(
            [
                datetime.date(year=2027, month=6, day=7),
                datetime.date(year=2027, month=6, day=14),
            ],
            [week.date for week in weeks],
        )

    def test_buildWeekOptions_weekNotDelivered_isMarked(
        self,
        mock_is_week_delivered: MagicMock,
    ):
        mock_timezone(test=self, now=datetime.datetime(year=2027, month=6, day=2))
        self.subscription.end_date = datetime.date(year=2027, month=6, day=20)
        mock_is_week_delivered.side_effect = lambda **kwargs: kwargs[
            "delivery_date"
        ] != datetime.date(year=2027, month=6, day=14)

        weeks = self._build(
            next_possible_start=datetime.date(year=2027, month=6, day=7)
        )

        self.assertEqual(
            [datetime.date(year=2027, month=6, day=14)],
            [week.date for week in weeks if week.has_no_delivery],
        )
        mock_is_week_delivered.assert_any_call(
            product_type=self.product_type,
            delivery_date=datetime.date(year=2027, month=6, day=14),
            check_for_weeks_without_delivery=True,
            cache={},
        )

    def test_buildWeekOptions_productTypeWithoutDelivery_noWeekMarked(
        self,
        mock_is_week_delivered: MagicMock,
    ):
        mock_timezone(test=self, now=datetime.datetime(year=2027, month=6, day=2))
        self.product_type.delivery_cycle = NO_DELIVERY[0]

        weeks = self._build(
            next_possible_start=datetime.date(year=2027, month=6, day=7)
        )

        self.assertFalse(any(week.has_no_delivery for week in weeks))
        mock_is_week_delivered.assert_not_called()
