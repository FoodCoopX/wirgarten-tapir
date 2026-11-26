from django.core.exceptions import ValidationError

from tapir.bakery.services.weekly_plan_validator import WeeklyPlanValidator
from tapir.bakery.tests.factories import (
    AvailableBreadsForDeliveryDayFactory,
    BreadFactory,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestValidateCopyWeek(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def _bake(self, year, delivery_week, is_active=True):
        AvailableBreadsForDeliveryDayFactory.create(
            year=year,
            delivery_week=delivery_week,
            delivery_day=1,
            bread=BreadFactory.create(is_active=is_active),
        )

    def test_validateCopyWeek_earlierSourceWithBreads_doesNothing(self):
        for source_year, source_week in ((2026, 11), (2025, 52)):
            with self.subTest(source_year=source_year, source_week=source_week):
                self._bake(source_year, source_week)

                WeeklyPlanValidator.validate_copy_week(
                    source_year=source_year,
                    source_week=source_week,
                    target_year=2026,
                    target_week=12,
                )

    def test_validateCopyWeek_sourceNotBeforeTarget_raisesError(self):
        for source_year, source_week in ((2026, 12), (2026, 13), (2027, 1)):
            with self.subTest(source_year=source_year, source_week=source_week):
                self._bake(source_year, source_week)

                with self.assertRaisesMessage(
                    ValidationError, WeeklyPlanValidator.SOURCE_NOT_BEFORE_TARGET
                ):
                    WeeklyPlanValidator.validate_copy_week(
                        source_year=source_year,
                        source_week=source_week,
                        target_year=2026,
                        target_week=12,
                    )

    def test_validateCopyWeek_sourceWithoutActiveBreads_raisesError(self):
        self._bake(2026, 10, is_active=False)

        for source_week in (9, 10):
            with self.subTest(source_week=source_week):
                with self.assertRaisesMessage(
                    ValidationError, WeeklyPlanValidator.SOURCE_WITHOUT_BREADS
                ):
                    WeeklyPlanValidator.validate_copy_week(
                        source_year=2026,
                        source_week=source_week,
                        target_year=2026,
                        target_week=12,
                    )
