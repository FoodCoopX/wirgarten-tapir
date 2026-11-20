import datetime
from unittest.mock import patch, MagicMock

from tapir.deliveries.services.delivery_date_calculator import (
    DeliveryDateCalculator,
)
from tapir.subscriptions.services.start_date_week_options_builder import (
    StartDateWeekOptionsBuilder,
)
from tapir.wirgarten.constants import NO_DELIVERY, WEEKLY
from tapir.wirgarten.tests.factories import ProductTypeFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(
    DeliveryDateCalculator, "is_week_delivered", autospec=True, return_value=True
)
class TestStartDateWeekOptionsBuilderBuildWeekOptions(TapirUnitTest):
    def setUp(self):
        super().setUp()
        self.product_type = ProductTypeFactory.build(delivery_cycle=WEEKLY[0])

    def _build(
        self,
        first_date: datetime.date,
        last_date: datetime.date,
        next_possible_start: datetime.date,
    ):
        return StartDateWeekOptionsBuilder.build_week_options(
            product_type=self.product_type,
            first_date=first_date,
            last_date=last_date,
            next_possible_start=next_possible_start,
            cache={},
        )

    def test_buildWeekOptions_firstDateNotMonday_offersMondaysFromTheFollowingOne(
        self, _: MagicMock
    ):
        weeks = self._build(
            first_date=datetime.date(year=2027, month=1, day=1),
            last_date=datetime.date(year=2027, month=12, day=31),
            next_possible_start=datetime.date(year=2027, month=1, day=11),
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

    def test_buildWeekOptions_firstDateIsMonday_includesIt(self, _: MagicMock):
        weeks = self._build(
            first_date=datetime.date(year=2027, month=6, day=7),
            last_date=datetime.date(year=2027, month=12, day=31),
            next_possible_start=datetime.date(year=2027, month=6, day=14),
        )

        self.assertEqual(datetime.date(year=2027, month=6, day=7), weeks[0].date)

    def test_buildWeekOptions_lastDateBeforePeriodEnd_onlyOffersMondaysUntilLastDate(
        self, _: MagicMock
    ):
        weeks = self._build(
            first_date=datetime.date(year=2027, month=6, day=2),
            last_date=datetime.date(year=2027, month=6, day=20),
            next_possible_start=datetime.date(year=2027, month=6, day=7),
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
        mock_is_week_delivered.side_effect = lambda **kwargs: kwargs[
            "delivery_date"
        ] != datetime.date(year=2027, month=6, day=14)

        weeks = self._build(
            first_date=datetime.date(year=2027, month=6, day=2),
            last_date=datetime.date(year=2027, month=6, day=20),
            next_possible_start=datetime.date(year=2027, month=6, day=7),
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
        self.product_type.delivery_cycle = NO_DELIVERY[0]

        weeks = self._build(
            first_date=datetime.date(year=2027, month=6, day=2),
            last_date=datetime.date(year=2027, month=6, day=20),
            next_possible_start=datetime.date(year=2027, month=6, day=7),
        )

        self.assertFalse(any(week.has_no_delivery for week in weeks))
        mock_is_week_delivered.assert_not_called()
