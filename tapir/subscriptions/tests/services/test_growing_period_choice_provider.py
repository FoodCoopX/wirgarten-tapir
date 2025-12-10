import datetime

from tapir.configuration.models import TapirParameter
from tapir.subscriptions.services.growing_period_choice_provider import (
    GrowingPeriodChoiceProvider,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import GrowingPeriodFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestGrowingPeriodChoiceProvider(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.ENABLE_GROWING_PERIOD_CHOICE_DAYS_BEFORE
        ).update(value=61)

    def test_getAvailableGrowingPeriods_noFuturePeriod_returnsOnlyCurrentPeriod(self):
        now = mock_timezone(self, now=datetime.datetime(year=2023, month=6, day=1))
        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2023, month=1, day=1)
        )
        cache = {}

        result = GrowingPeriodChoiceProvider.get_available_growing_periods(
            reference_date=now.date(), cache=cache
        )

        self.assertEqual([growing_period], result)

    def test_getAvailableGrowingPeriods_nowIsAfterThreshold_returnsCurrentAndFuturePeriod(
        self,
    ):
        now = mock_timezone(self, now=datetime.datetime(year=2023, month=11, day=1))
        current_growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2023, month=1, day=1)
        )
        future_growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2024, month=1, day=1)
        )
        cache = {}

        result = GrowingPeriodChoiceProvider.get_available_growing_periods(
            reference_date=now.date(), cache=cache
        )

        self.assertEqual([current_growing_period, future_growing_period], result)

    def test_getAvailableGrowingPeriods_nowIsBeforeThreshold_returnsOnlyCurrentPeriod(
        self,
    ):
        now = mock_timezone(self, now=datetime.datetime(year=2023, month=10, day=31))
        current_growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2023, month=1, day=1)
        )
        GrowingPeriodFactory.create(start_date=datetime.date(year=2024, month=1, day=1))
        cache = {}

        result = GrowingPeriodChoiceProvider.get_available_growing_periods(
            reference_date=now.date(), cache=cache
        )

        self.assertEqual([current_growing_period], result)

    def test_getAvailableGrowingPeriods_futurePeriodIsDisabled_returnsOnlyCurrentPeriod(
        self,
    ):
        now = mock_timezone(self, now=datetime.datetime(year=2023, month=11, day=1))
        current_growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2023, month=1, day=1)
        )
        GrowingPeriodFactory.create(
            start_date=datetime.date(year=2024, month=1, day=1),
            is_available_in_bestell_wizard=False,
        )
        cache = {}

        result = GrowingPeriodChoiceProvider.get_available_growing_periods(
            reference_date=now.date(), cache=cache
        )

        self.assertEqual([current_growing_period], result)

    def test_getAvailableGrowingPeriods_currentPeriodIsDisabled_returnsOnlyFuturePeriod(
        self,
    ):
        now = mock_timezone(self, now=datetime.datetime(year=2023, month=11, day=1))
        GrowingPeriodFactory.create(
            start_date=datetime.date(year=2023, month=1, day=1),
            is_available_in_bestell_wizard=False,
        )
        future_growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2024, month=1, day=1)
        )
        cache = {}

        result = GrowingPeriodChoiceProvider.get_available_growing_periods(
            reference_date=now.date(), cache=cache
        )

        self.assertEqual([future_growing_period], result)

    def test_getAvailableGrowingPeriods_pastPeriodExists_pastPeriodNotReturned(
        self,
    ):
        now = mock_timezone(self, now=datetime.datetime(year=2023, month=11, day=1))
        GrowingPeriodFactory.create(start_date=datetime.date(year=2022, month=1, day=1))
        current_growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2023, month=1, day=1)
        )
        future_growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2024, month=1, day=1)
        )
        cache = {}

        result = GrowingPeriodChoiceProvider.get_available_growing_periods(
            reference_date=now.date(), cache=cache
        )

        self.assertEqual([current_growing_period, future_growing_period], result)

    def test_getAvailableGrowingPeriods_bothPeriodsWouldResultInTheSameContractStartDate_returnsOnlyTheFuturePeriod(
        self,
    ):
        now = mock_timezone(self, now=datetime.datetime(year=2025, month=12, day=29))
        GrowingPeriodFactory.create(start_date=datetime.date(year=2025, month=1, day=1))
        future_growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2026, month=1, day=1)
        )
        cache = {}

        result = GrowingPeriodChoiceProvider.get_available_growing_periods(
            reference_date=now.date(), cache=cache
        )

        self.assertEqual([future_growing_period], result)
