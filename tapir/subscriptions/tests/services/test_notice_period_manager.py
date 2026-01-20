import datetime
from unittest.mock import Mock

from tapir.configuration.models import TapirParameter
from tapir.subscriptions.config import (
    NOTICE_PERIOD_UNIT_MONTHS,
    NOTICE_PERIOD_UNIT_WEEKS,
)
from tapir.subscriptions.models import NoticePeriod
from tapir.subscriptions.services.notice_period_manager import NoticePeriodManager
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    ProductTypeFactory,
    GrowingPeriodFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestNoticePeriodManager(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_setNoticePeriodDuration_noticePeriodObjectAlreadyExists_existingObjectUpdated(
        self,
    ):
        product_type = ProductTypeFactory.create()
        growing_period = GrowingPeriodFactory.create()
        notice_period = NoticePeriod.objects.create(
            product_type=product_type,
            growing_period=growing_period,
            duration=2,
            unit=NOTICE_PERIOD_UNIT_WEEKS,
        )

        NoticePeriodManager.set_notice_period_duration(
            product_type=product_type,
            growing_period=growing_period,
            notice_period_duration=3,
            notice_period_unit=NOTICE_PERIOD_UNIT_MONTHS,
        )

        self.assertEqual(1, NoticePeriod.objects.count())
        notice_period.refresh_from_db()
        self.assertEqual(3, notice_period.duration)
        self.assertEqual(NOTICE_PERIOD_UNIT_MONTHS, notice_period.unit)

    def test_setNoticePeriodDuration_noticePeriodObjectDoesntExists_objectCreated(
        self,
    ):
        product_type = ProductTypeFactory.create()
        growing_period = GrowingPeriodFactory.create()

        NoticePeriodManager.set_notice_period_duration(
            product_type=product_type,
            growing_period=growing_period,
            notice_period_duration=3,
            notice_period_unit=NOTICE_PERIOD_UNIT_WEEKS,
        )

        self.assertEqual(1, NoticePeriod.objects.count())
        notice_period = NoticePeriod.objects.get()
        self.assertEqual(product_type, notice_period.product_type)
        self.assertEqual(growing_period, notice_period.growing_period)
        self.assertEqual(3, notice_period.duration)
        self.assertEqual(NOTICE_PERIOD_UNIT_WEEKS, notice_period.unit)

    def test_getNoticePeriodDuration_noticePeriodObjectDoesntExist_returnsDefaultValue(
        self,
    ):
        product_type = ProductTypeFactory.create()
        growing_period = GrowingPeriodFactory.create()
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD
        ).update(value=5)

        result = NoticePeriodManager.get_notice_period_duration(
            product_type=product_type, growing_period=growing_period, cache={}
        )

        self.assertEqual(5, result)

    def test_getNoticePeriodDuration_noticePeriodObjectExists_returnsCustomValue(
        self,
    ):
        product_type = ProductTypeFactory.create()
        growing_period = GrowingPeriodFactory.create()
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD
        ).update(value=5)
        NoticePeriod.objects.create(
            product_type=product_type,
            growing_period=growing_period,
            duration=2,
        )

        result = NoticePeriodManager.get_notice_period_duration(
            product_type=product_type, growing_period=growing_period, cache={}
        )

        self.assertEqual(2, result)

    def test_getMaxCancellationDate_durationIsInWeeks_returnsCorrectDate(self):
        product_type = ProductTypeFactory.create()
        growing_period = GrowingPeriodFactory.create()

        subscription = Mock()
        subscription.product.type = product_type
        subscription.period = growing_period
        subscription.end_date = datetime.date(year=2025, month=5, day=31)
        subscription.notice_period_duration = 2
        subscription.notice_period_unit = NOTICE_PERIOD_UNIT_WEEKS

        result = NoticePeriodManager.get_max_cancellation_date_subscription(
            subscription, cache={}
        )

        self.assertEqual(datetime.date(year=2025, month=5, day=17), result)

    def test_getMaxCancellationDate_durationIsInMonth_returnsCorrectDate(self):
        subscription = SubscriptionFactory.build(
            notice_period_duration=2,
            notice_period_unit=NOTICE_PERIOD_UNIT_MONTHS,
            end_date=datetime.date(year=2025, month=5, day=31),
            mandate_ref__ref="test_ref",
        )

        result = NoticePeriodManager.get_max_cancellation_date_subscription(
            subscription, cache={}
        )

        self.assertEqual(datetime.date(year=2025, month=3, day=31), result)

    def test_getMaxCancellationDate_maxCancellationDateIsPreviousYear_returnsCorrectDate(
        self,
    ):
        subscription = SubscriptionFactory.build(
            notice_period_duration=1,
            notice_period_unit=NOTICE_PERIOD_UNIT_MONTHS,
            end_date=datetime.date(year=2025, month=1, day=31),
            mandate_ref__ref="test_ref",
        )

        result = NoticePeriodManager.get_max_cancellation_date_subscription(
            subscription, cache={}
        )

        self.assertEqual(datetime.date(year=2024, month=12, day=31), result)

    def test_getMaxCancellationDate_monthOfMaxDateHasLessDaysThanSubscriptionEndMonth_returnsCorrectDate(
        self,
    ):
        subscription = SubscriptionFactory.build(
            notice_period_duration=2,
            notice_period_unit=NOTICE_PERIOD_UNIT_MONTHS,
            end_date=datetime.date(year=2025, month=4, day=29),
            mandate_ref__ref="test_ref",
        )

        result = NoticePeriodManager.get_max_cancellation_date_subscription(
            subscription, cache={}
        )

        self.assertEqual(datetime.date(year=2025, month=2, day=28), result)

    def test_getMaxCancellationDate_contractEndDateIsOnLastDayOfMonth_maxCancellationDateIsAlsoOnLastDayOfMonth(
        self,
    ):
        subscription = SubscriptionFactory.build(
            notice_period_duration=1,
            notice_period_unit=NOTICE_PERIOD_UNIT_MONTHS,
            end_date=datetime.date(year=2025, month=11, day=30),
            mandate_ref__ref="test_ref",
        )

        result = NoticePeriodManager.get_max_cancellation_date_subscription(
            subscription, cache={}
        )

        self.assertEqual(datetime.date(year=2025, month=10, day=31), result)

    def test_getMaxCancellationDate_contractEndDateIsNotOnLastDayOfMonth_maxCancellationDateIsOnSameDay(
        self,
    ):
        subscription = SubscriptionFactory.build(
            notice_period_duration=1,
            notice_period_unit=NOTICE_PERIOD_UNIT_MONTHS,
            end_date=datetime.date(year=2025, month=11, day=17),
            mandate_ref__ref="test_ref",
        )

        result = NoticePeriodManager.get_max_cancellation_date_subscription(
            subscription, cache={}
        )

        self.assertEqual(datetime.date(year=2025, month=10, day=17), result)

    def test_getMaxCancellationDateUnitWeeks_subscriptionHasNoEndDate_returnsDateRelativeToToday(
        self,
    ):
        mock_timezone(self, datetime.datetime(year=2025, month=4, day=1))

        result = NoticePeriodManager.get_max_cancellation_date_unit_weeks(
            end_date=None, notice_period_duration=4, cache={}
        )

        self.assertEqual(datetime.date(year=2025, month=4, day=29), result)

    def test_getMaxCancellationDateUnitMonths_subscriptionHasNoEndDate_returnsDateRelativeToToday(
        self,
    ):
        mock_timezone(self, datetime.datetime(year=2025, month=4, day=1))

        result = NoticePeriodManager.get_max_cancellation_date_unit_months(
            end_date=None, notice_period_duration=2, cache={}
        )

        self.assertEqual(datetime.date(year=2025, month=6, day=1), result)
