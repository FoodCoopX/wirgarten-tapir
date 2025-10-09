import datetime
from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from tapir.subscriptions.views.other import SubscriptionDateChangeApiView
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.factories import SubscriptionFactory, GrowingPeriodFactory


class TestValidateDates(SimpleTestCase):
    def test_validateDates_givenDatesAreTheSameAsSubscription_raisesError(self):
        subscription = SubscriptionFactory.build(
            start_date=datetime.date(year=2022, month=5, day=17),
            end_date=datetime.date(year=2022, month=7, day=28),
            mandate_ref__ref="test_ref",
        )

        with self.assertRaises(ValidationError):
            SubscriptionDateChangeApiView.validate_dates(
                subscription=subscription,
                start_date=datetime.date(year=2022, month=5, day=17),
                end_date=datetime.date(year=2022, month=7, day=28),
                cache=Mock(),
            )

    @patch("tapir.subscriptions.views.other.get_parameter_value")
    def test_validateDates_givenEndDateIsNotOnCorrectDay_raisesError(
        self, mock_get_parameter_value: Mock
    ):
        subscription = SubscriptionFactory.build(mandate_ref__ref="test_ref")
        parameter_values = {
            ParameterKeys.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL: 6,
        }
        mock_get_parameter_value.side_effect = lambda key, cache: parameter_values[key]
        cache = Mock()

        with self.assertRaises(ValidationError):
            SubscriptionDateChangeApiView.validate_dates(
                subscription=subscription,
                start_date=datetime.date(year=2022, month=5, day=17),
                end_date=datetime.date(
                    year=2025, month=10, day=9
                ),  # this is a wednesday
                cache=cache,
            )

        mock_get_parameter_value.assert_called_once_with(
            key=ParameterKeys.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL, cache=cache
        )

    @patch.object(TapirCache, "get_growing_period_at_date")
    def test_validateDates_givenStartDateIsNotOnSameGrowingPeriod_raisesError(
        self, mock_get_growing_period_at_date: Mock
    ):
        subscription = SubscriptionFactory.build(
            mandate_ref__ref="test_ref",
            start_date=datetime.date(year=2023, month=1, day=1),
        )
        cache = Mock()

        growing_periods = {
            2022: GrowingPeriodFactory.build(),
            2023: GrowingPeriodFactory.build(),
            2024: GrowingPeriodFactory.build(),
        }

        mock_get_growing_period_at_date.side_effect = (
            lambda date, cache: growing_periods[date.year]
        )

        with self.assertRaises(ValidationError) as error:
            SubscriptionDateChangeApiView.validate_dates(
                subscription=subscription,
                start_date=datetime.date(year=2022, month=5, day=17),
                end_date=subscription.end_date,
                cache=cache,
            )

        self.assertEqual(
            "Das neue Start-Datum muss im gleiche Vertragsperiode liegen wie das alte",
            error.exception.message,
        )
        self.assertEqual(2, mock_get_growing_period_at_date.call_count)

    @patch.object(TapirCache, "get_growing_period_at_date")
    @patch("tapir.subscriptions.views.other.get_parameter_value")
    def test_validateDates_givenEndDateIsNotOnSameGrowingPeriod_raisesError(
        self, mock_get_parameter_value: Mock, mock_get_growing_period_at_date: Mock
    ):
        subscription = SubscriptionFactory.build(
            mandate_ref__ref="test_ref",
            end_date=datetime.date(year=2023, month=12, day=31),
        )
        parameter_values = {
            ParameterKeys.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL: 0,
        }
        mock_get_parameter_value.side_effect = lambda key, cache: parameter_values[key]
        cache = Mock()

        growing_periods = {
            2022: GrowingPeriodFactory.build(),
            2023: GrowingPeriodFactory.build(),
            2024: GrowingPeriodFactory.build(),
        }

        mock_get_growing_period_at_date.side_effect = (
            lambda date, cache: growing_periods[date.year]
        )

        with self.assertRaises(ValidationError) as error:
            SubscriptionDateChangeApiView.validate_dates(
                subscription=subscription,
                start_date=subscription.start_date,
                end_date=datetime.date(year=2024, month=1, day=1),
                cache=cache,
            )

        self.assertEqual(
            "Das neue End-Datum muss im gleiche Vertragsperiode liegen wie das alte",
            error.exception.message,
        )
        self.assertEqual(4, mock_get_growing_period_at_date.call_count)
