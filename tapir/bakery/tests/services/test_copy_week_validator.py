from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from tapir.bakery.services.copy_week_validator import CopyWeekValidator


class TestCopyWeekValidator(SimpleTestCase):
    def test_validate_sourceBeforeTarget_doesNothing(self):
        for source_year, source_week in ((2026, 11), (2025, 52)):
            with self.subTest(source_year=source_year, source_week=source_week):
                CopyWeekValidator.validate(
                    source_year=source_year,
                    source_week=source_week,
                    target_year=2026,
                    target_week=12,
                )

    def test_validate_sourceNotBeforeTarget_raisesError(self):
        for source_year, source_week in ((2026, 12), (2026, 13), (2027, 1)):
            with self.subTest(source_year=source_year, source_week=source_week):
                with self.assertRaisesMessage(
                    ValidationError, CopyWeekValidator.SOURCE_NOT_BEFORE_TARGET
                ):
                    CopyWeekValidator.validate(
                        source_year=source_year,
                        source_week=source_week,
                        target_year=2026,
                        target_week=12,
                    )
