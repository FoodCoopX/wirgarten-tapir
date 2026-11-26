import datetime

from django.core.exceptions import ValidationError

from tapir.bakery.services.weekly_plan_validator import WeeklyPlanValidator
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone

FROZEN_DATE = datetime.date(2026, 3, 14)  # Saturday, week 11


class TestValidateSetBreadBaked(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        mock_timezone(self, datetime.datetime.combine(FROZEN_DATE, datetime.time(12)))

    def test_validateSetBreadBaked_dayAhead_doesNothing(self):
        for delivery_week, delivery_day in ((11, 6), (12, 0)):
            with self.subTest(delivery_week=delivery_week, delivery_day=delivery_day):
                WeeklyPlanValidator.validate_set_bread_baked(
                    year=2026,
                    delivery_week=delivery_week,
                    delivery_day=delivery_day,
                    cache={},
                )

    def test_validateSetBreadBaked_todayOrEarlier_raisesError(self):
        for delivery_week, delivery_day in ((11, 5), (11, 1), (10, 6)):
            with self.subTest(delivery_week=delivery_week, delivery_day=delivery_day):
                with self.assertRaisesMessage(
                    ValidationError, WeeklyPlanValidator.DELIVERY_DAY_IS_OVER
                ):
                    WeeklyPlanValidator.validate_set_bread_baked(
                        year=2026,
                        delivery_week=delivery_week,
                        delivery_day=delivery_day,
                        cache={},
                    )
