import datetime
from unittest.mock import Mock

from tapir.configuration.models import TapirParameter
from tapir.subscriptions.config import (
    NOTICE_PERIOD_UNIT_MONTHS,
    NOTICE_PERIOD_UNIT_WEEKS,
)
from tapir.subscriptions.models import NoticePeriod
from tapir.subscriptions.services.notice_period_manager import NoticePeriodManager
from tapir.wirgarten.parameters import ParameterDefinitions, Parameter
from tapir.wirgarten.tests.factories import ProductTypeFactory, GrowingPeriodFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestNoticePeriodManager(TapirIntegrationTest):
    def setUp(self):
        ParameterDefinitions().import_definitions()

    def test_setNoticePeriodDuration_noticePeriodObjectAlreadyExists_existingObjectUpdated(
        self,
    ):
        product_type = ProductTypeFactory.create()
        growing_period = GrowingPeriodFactory.create()
        notice_period = NoticePeriod.objects.create(
            product_type=product_type,
            growing_period=growing_period,
            duration=2,
        )

        NoticePeriodManager.set_notice_period_duration(
            product_type=product_type,
            growing_period=growing_period,
            notice_period_duration=3,
        )

        self.assertEqual(1, NoticePeriod.objects.count())
        notice_period.refresh_from_db()
        self.assertEqual(3, notice_period.duration)

    def test_setNoticePeriodDuration_noticePeriodObjectDoesntExists_objectCreated(
        self,
    ):
        product_type = ProductTypeFactory.create()
        growing_period = GrowingPeriodFactory.create()

        NoticePeriodManager.set_notice_period_duration(
            product_type=product_type,
            growing_period=growing_period,
            notice_period_duration=3,
        )

        self.assertEqual(1, NoticePeriod.objects.count())
        notice_period = NoticePeriod.objects.get()
        self.assertEqual(product_type, notice_period.product_type)
        self.assertEqual(growing_period, notice_period.growing_period)
        self.assertEqual(3, notice_period.duration)

    def test_getNoticePeriodDuration_noticePeriodObjectDoesntExist_returnsDefaultValue(
        self,
    ):
        product_type = ProductTypeFactory.create()
        growing_period = GrowingPeriodFactory.create()
        TapirParameter.objects.filter(
            key=Parameter.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD
        ).update(value=5)

        result = NoticePeriodManager.get_notice_period_duration(
            product_type=product_type,
            growing_period=growing_period,
        )

        self.assertEqual(5, result)

    def test_getNoticePeriodDuration_noticePeriodObjectExists_returnsCustomValue(
        self,
    ):
        product_type = ProductTypeFactory.create()
        growing_period = GrowingPeriodFactory.create()
        TapirParameter.objects.filter(
            key=Parameter.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD
        ).update(value=5)
        NoticePeriod.objects.create(
            product_type=product_type,
            growing_period=growing_period,
            duration=2,
        )

        result = NoticePeriodManager.get_notice_period_duration(
            product_type=product_type,
            growing_period=growing_period,
        )

        self.assertEqual(2, result)

    def test_getMaxCancellationDate_durationIsInWeeks_returnsCorrectDate(self):
        product_type = ProductTypeFactory.create()
        growing_period = GrowingPeriodFactory.create()
        TapirParameter.objects.filter(
            key=Parameter.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD
        ).update(value=2)
        TapirParameter.objects.filter(
            key=Parameter.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD_UNIT
        ).update(value=NOTICE_PERIOD_UNIT_WEEKS)

        subscription = Mock()
        subscription.product.type = product_type
        subscription.period = growing_period
        subscription.end_date = datetime.date(year=2025, month=5, day=31)
        subscription.notice_period_duration = None

        result = NoticePeriodManager.get_max_cancellation_date(subscription)

        self.assertEqual(datetime.date(year=2025, month=5, day=17), result)

    def test_getMaxCancellationDate_durationIsInMonth_returnsCorrectDate(self):
        product_type = ProductTypeFactory.create()
        growing_period = GrowingPeriodFactory.create()
        TapirParameter.objects.filter(
            key=Parameter.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD
        ).update(value=2)
        TapirParameter.objects.filter(
            key=Parameter.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD_UNIT
        ).update(value=NOTICE_PERIOD_UNIT_MONTHS)

        subscription = Mock()
        subscription.product.type = product_type
        subscription.period = growing_period
        subscription.end_date = datetime.date(year=2025, month=5, day=31)
        subscription.notice_period_duration = None

        result = NoticePeriodManager.get_max_cancellation_date(subscription)

        self.assertEqual(datetime.date(year=2025, month=3, day=31), result)

    def test_getMaxCancellationDate_subscriptionHasNoticePeriodField_usePeriodFromSubscriptionInsteadOfDefault(
        self,
    ):
        product_type = ProductTypeFactory.create()
        growing_period = GrowingPeriodFactory.create()
        TapirParameter.objects.filter(
            key=Parameter.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD
        ).update(value=2)

        subscription = Mock()
        subscription.product.type = product_type
        subscription.period = growing_period
        subscription.end_date = datetime.date(year=2025, month=5, day=31)
        subscription.notice_period_duration = 3

        result = NoticePeriodManager.get_max_cancellation_date(subscription)

        self.assertEqual(datetime.date(year=2025, month=2, day=28), result)

    def test_getMaxCancellationDate_maxCancellationDateIsPreviousYear_returnsCorrectDate(
        self,
    ):
        product_type = ProductTypeFactory.create()
        growing_period = GrowingPeriodFactory.create()
        TapirParameter.objects.filter(
            key=Parameter.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD
        ).update(value=1)

        subscription = Mock()
        subscription.product.type = product_type
        subscription.period = growing_period
        subscription.end_date = datetime.date(year=2025, month=1, day=31)
        subscription.notice_period_duration = None

        result = NoticePeriodManager.get_max_cancellation_date(subscription)

        self.assertEqual(datetime.date(year=2024, month=12, day=31), result)

    def test_getMaxCancellationDate_monthOfMaxDateHasLessDaysThanSubscriptionEndMonth_returnsCorrectDate(
        self,
    ):
        product_type = ProductTypeFactory.create()
        growing_period = GrowingPeriodFactory.create()
        TapirParameter.objects.filter(
            key=Parameter.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD
        ).update(value=2)

        subscription = Mock()
        subscription.product.type = product_type
        subscription.period = growing_period
        subscription.end_date = datetime.date(year=2025, month=4, day=29)
        subscription.notice_period_duration = None

        result = NoticePeriodManager.get_max_cancellation_date(subscription)

        self.assertEqual(datetime.date(year=2025, month=2, day=28), result)

    def test_getMaxCancellationDate_contractEndDateIsOnLastDayOfMonth_maxCancellationDateIsAlsoOnLastDayOfMonth(
        self,
    ):
        product_type = ProductTypeFactory.create()
        growing_period = GrowingPeriodFactory.create()
        TapirParameter.objects.filter(
            key=Parameter.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD
        ).update(value=1)

        subscription = Mock()
        subscription.product.type = product_type
        subscription.period = growing_period
        subscription.end_date = datetime.date(year=2025, month=11, day=30)
        subscription.notice_period_duration = None

        result = NoticePeriodManager.get_max_cancellation_date(subscription)

        self.assertEqual(datetime.date(year=2025, month=10, day=31), result)

    def test_getMaxCancellationDate_contractEndDateIsNotOnLastDayOfMonth_maxCancellationDateIsOnSameDay(
        self,
    ):
        product_type = ProductTypeFactory.create()
        growing_period = GrowingPeriodFactory.create()
        TapirParameter.objects.filter(
            key=Parameter.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD
        ).update(value=1)

        subscription = Mock()
        subscription.product.type = product_type
        subscription.period = growing_period
        subscription.end_date = datetime.date(year=2025, month=11, day=17)
        subscription.notice_period_duration = None

        result = NoticePeriodManager.get_max_cancellation_date(subscription)

        self.assertEqual(datetime.date(year=2025, month=10, day=17), result)
