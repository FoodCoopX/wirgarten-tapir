import datetime

from tapir.payments.services.intended_use_pattern_expander import (
    ModelDateRangeOverlapChecker,
)
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestModelDateRangeOverlapChecker(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_filterObjectsThatOverlapWithRange_subscriptionFullyInsideRange_isIncluded(
        self,
    ):
        subscription = SubscriptionFactory.create(
            start_date=datetime.date(2026, 6, 5),
            end_date=datetime.date(2026, 6, 25),
        )

        result = ModelDateRangeOverlapChecker.filter_objects_that_overlap_with_range(
            queryset=Subscription.objects.all(),
            range_start=datetime.date(year=2026, month=6, day=1),
            range_end=datetime.date(year=2026, month=6, day=30),
        )

        self.assertQuerySetEqual(result, [subscription])

    def test_filterObjectsThatOverlapWithRange_subscriptionStartsOnRangeEnd_isIncluded(
        self,
    ):
        subscription = SubscriptionFactory.create(
            start_date=datetime.date(2026, 6, 30),
            end_date=datetime.date(2026, 7, 31),
        )

        result = ModelDateRangeOverlapChecker.filter_objects_that_overlap_with_range(
            queryset=Subscription.objects.all(),
            range_start=datetime.date(year=2026, month=6, day=1),
            range_end=datetime.date(year=2026, month=6, day=30),
        )

        self.assertQuerySetEqual(result, [subscription])

    def test_filterObjectsThatOverlapWithRange_subscriptionEndsOnRangeStart_isIncluded(
        self,
    ):
        subscription = SubscriptionFactory.create(
            start_date=datetime.date(2026, 5, 1),
            end_date=datetime.date(2026, 6, 1),
        )

        result = ModelDateRangeOverlapChecker.filter_objects_that_overlap_with_range(
            queryset=Subscription.objects.all(),
            range_start=datetime.date(year=2026, month=6, day=1),
            range_end=datetime.date(year=2026, month=6, day=30),
        )

        self.assertQuerySetEqual(result, [subscription])

    def test_filterObjectsThatOverlapWithRange_subscriptionEndsBeforeRangeStart_isExcluded(
        self,
    ):
        SubscriptionFactory.create(
            start_date=datetime.date(2026, 5, 1),
            end_date=datetime.date(2026, 5, 31),
        )

        result = ModelDateRangeOverlapChecker.filter_objects_that_overlap_with_range(
            queryset=Subscription.objects.all(),
            range_start=datetime.date(year=2026, month=6, day=1),
            range_end=datetime.date(year=2026, month=6, day=30),
        )

        self.assertQuerySetEqual(result, [])

    def test_filterObjectsThatOverlapWithRange_subscriptionStartsAfterRangeEnd_isExcluded(
        self,
    ):
        SubscriptionFactory.create(
            start_date=datetime.date(2026, 7, 1),
            end_date=datetime.date(2026, 7, 31),
        )

        result = ModelDateRangeOverlapChecker.filter_objects_that_overlap_with_range(
            queryset=Subscription.objects.all(),
            range_start=datetime.date(year=2026, month=6, day=1),
            range_end=datetime.date(year=2026, month=6, day=30),
        )

        self.assertQuerySetEqual(result, [])
