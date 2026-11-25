import datetime
from unittest.mock import patch, MagicMock

from tapir.subscriptions.services.notice_period_manager import NoticePeriodManager
from tapir.subscriptions.services.renewal_cancellation_status_provider import (
    RenewalCancellationStatusProvider,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.factories import SubscriptionFactory, GrowingPeriodFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch(
    "tapir.subscriptions.services.renewal_cancellation_status_provider.get_today",
    autospec=True,
    return_value=datetime.date(year=2025, month=11, day=10),
)
@patch.object(
    NoticePeriodManager,
    "get_max_cancellation_date_subscription",
    autospec=True,
    return_value=datetime.date(year=2025, month=9, day=30),
)
@patch.object(
    TapirCache,
    "get_first_growing_period_starting_after",
    autospec=True,
    return_value=GrowingPeriodFactory.build(
        start_date=datetime.date(year=2026, month=1, day=1)
    ),
)
@patch.object(
    TapirCache, "get_all_subscriptions_for_member", autospec=True, return_value=[]
)
class TestRenewalCancellationStatusProvider(TapirUnitTest):
    def setUp(self) -> None:
        super().setUp()
        self.subscription = SubscriptionFactory.build(
            period=GrowingPeriodFactory.build(
                start_date=datetime.date(year=2025, month=1, day=1)
            ),
            cancellation_ts=None,
        )
        self.cache = {}
        mock_parameter_value(
            cache=self.cache,
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL,
            value=True,
        )

    def _get_status(self) -> str:
        return RenewalCancellationStatusProvider.get_status(
            subscription=self.subscription, cache=self.cache
        )

    def test_getStatus_automaticRenewalDisabled_returnsNotAvailable(
        self, _: MagicMock, __: MagicMock, ___: MagicMock, ____: MagicMock
    ):
        mock_parameter_value(
            cache=self.cache,
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL,
            value=False,
        )

        self.assertEqual(
            RenewalCancellationStatusProvider.STATUS_NOT_AVAILABLE, self._get_status()
        )

    def test_getStatus_renewalExists_returnsAvailable(
        self,
        mock_get_all_subscriptions_for_member: MagicMock,
        _: MagicMock,
        mock_get_max_cancellation_date_subscription: MagicMock,
        __: MagicMock,
    ):
        self.subscription.cancellation_ts = datetime.datetime(
            year=2025, month=11, day=1
        )
        mock_get_all_subscriptions_for_member.return_value = [
            self.subscription,
            SubscriptionFactory.build(
                member=self.subscription.member,
                product=self.subscription.product,
                period=GrowingPeriodFactory.build(
                    start_date=datetime.date(year=2026, month=1, day=1)
                ),
            ),
        ]
        mock_get_max_cancellation_date_subscription.return_value = datetime.date(
            year=2025, month=12, day=31
        )

        self.assertEqual(
            RenewalCancellationStatusProvider.STATUS_AVAILABLE, self._get_status()
        )
        mock_get_all_subscriptions_for_member.assert_called_once_with(
            member_id=self.subscription.member_id, cache=self.cache
        )

    def test_getStatus_renewalOfOtherProductExistsAndAlreadyCancelled_returnsNotAvailable(
        self,
        mock_get_all_subscriptions_for_member: MagicMock,
        _: MagicMock,
        __: MagicMock,
        ___: MagicMock,
    ):
        self.subscription.cancellation_ts = datetime.datetime(
            year=2025, month=11, day=1
        )
        mock_get_all_subscriptions_for_member.return_value = [
            SubscriptionFactory.build(
                member=self.subscription.member,
                period=GrowingPeriodFactory.build(
                    start_date=datetime.date(year=2026, month=1, day=1)
                ),
            ),
        ]

        self.assertEqual(
            RenewalCancellationStatusProvider.STATUS_NOT_AVAILABLE, self._get_status()
        )

    def test_getStatus_noNextGrowingPeriod_returnsNotAvailable(
        self,
        _: MagicMock,
        mock_get_first_growing_period_starting_after: MagicMock,
        __: MagicMock,
        ___: MagicMock,
    ):
        mock_get_first_growing_period_starting_after.return_value = None

        self.assertEqual(
            RenewalCancellationStatusProvider.STATUS_NOT_AVAILABLE, self._get_status()
        )
        mock_get_first_growing_period_starting_after.assert_called_once_with(
            reference_date=self.subscription.end_date, cache=self.cache
        )

    def test_getStatus_noticePeriodOver_returnsAvailable(
        self, _: MagicMock, __: MagicMock, ___: MagicMock, ____: MagicMock
    ):
        self.assertEqual(
            RenewalCancellationStatusProvider.STATUS_AVAILABLE, self._get_status()
        )

    def test_getStatus_noticePeriodNotOver_returnsBeforeNoticePeriodEnd(
        self,
        _: MagicMock,
        __: MagicMock,
        mock_get_max_cancellation_date_subscription: MagicMock,
        ___: MagicMock,
    ):
        mock_get_max_cancellation_date_subscription.return_value = datetime.date(
            year=2025, month=11, day=10
        )

        self.assertEqual(
            RenewalCancellationStatusProvider.STATUS_BEFORE_NOTICE_PERIOD_END,
            self._get_status(),
        )

    def test_getRenewal_followUpContractInSameGrowingPeriod_returnsNone(
        self,
        mock_get_all_subscriptions_for_member: MagicMock,
        _: MagicMock,
        __: MagicMock,
        ___: MagicMock,
    ):
        self.subscription.end_date = datetime.date(year=2025, month=6, day=29)
        mock_get_all_subscriptions_for_member.return_value = [
            self.subscription,
            self._build_same_product_subscription(
                start_date=datetime.date(year=2025, month=6, day=30)
            ),
            self._build_same_product_subscription(
                start_date=datetime.date(year=2026, month=1, day=1)
            ),
        ]

        self.assertIsNone(
            RenewalCancellationStatusProvider.get_renewal(
                subscription=self.subscription, cache=self.cache
            )
        )

    def test_getRenewal_severalLaterSubscriptions_returnsEarliest(
        self,
        mock_get_all_subscriptions_for_member: MagicMock,
        _: MagicMock,
        __: MagicMock,
        ___: MagicMock,
    ):
        renewal = self._build_same_product_subscription(
            start_date=datetime.date(year=2026, month=1, day=1)
        )
        mock_get_all_subscriptions_for_member.return_value = [
            self._build_same_product_subscription(
                start_date=datetime.date(year=2027, month=1, day=1)
            ),
            renewal,
            self.subscription,
        ]

        self.assertEqual(
            renewal,
            RenewalCancellationStatusProvider.get_renewal(
                subscription=self.subscription, cache=self.cache
            ),
        )

    def _build_same_product_subscription(
        self, start_date: datetime.date
    ) -> Subscription:
        return SubscriptionFactory.build(
            member=self.subscription.member,
            product=self.subscription.product,
            start_date=start_date,
            end_date=datetime.date(year=start_date.year, month=12, day=31),
        )
