import datetime
from unittest.mock import patch, MagicMock

from django.core.exceptions import ValidationError

from tapir.subscriptions.services.admin_size_change_validator import (
    AdminSizeChangeValidator,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Product, Subscription
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    ProductFactory,
    ProductTypeFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(TapirCache, "get_all_subscriptions_for_member", autospec=True)
class TestAdminSizeChangeValidatorValidateNoOtherCancelledSubscription(TapirUnitTest):
    CHANGE_DATE = datetime.date(year=2027, month=6, day=7)

    def setUp(self):
        super().setUp()
        self.member = MemberFactory.build()
        self.growing_period = GrowingPeriodFactory.build(
            start_date=datetime.date(year=2027, month=1, day=1),
            end_date=datetime.date(year=2027, month=12, day=31),
        )
        self.product_type = ProductTypeFactory.build()
        self.subscription = self._build_subscription(
            product=ProductFactory.build(type=self.product_type), cancelled=False
        )

    def _build_subscription(self, product: Product, cancelled: bool) -> Subscription:
        return SubscriptionFactory.build(
            member=self.member,
            period=self.growing_period,
            product=product,
            cancellation_ts=(
                datetime.datetime(year=2027, month=3, day=1) if cancelled else None
            ),
        )

    def _validate(self, cache: dict):
        AdminSizeChangeValidator.validate_no_other_cancelled_subscription(
            member=self.member,
            subscription=self.subscription,
            change_date=self.CHANGE_DATE,
            cache=cache,
        )

    def test_validateNoOtherCancelledSubscription_otherSubscriptionOfTypeCancelled_raisesValidationError(
        self, mock_get_all_subscriptions_for_member: MagicMock
    ):
        mock_get_all_subscriptions_for_member.return_value = [
            self.subscription,
            self._build_subscription(
                product=ProductFactory.build(type=self.product_type), cancelled=True
            ),
        ]
        cache = {}

        with self.assertRaisesMessage(ValidationError, "Kündigung aufheben"):
            self._validate(cache=cache)

        mock_get_all_subscriptions_for_member.assert_called_once_with(
            member_id=self.member.id, cache=cache
        )

    def test_validateNoOtherCancelledSubscription_cancelledSubscriptionOfOtherType_doesNotRaise(
        self, mock_get_all_subscriptions_for_member: MagicMock
    ):
        mock_get_all_subscriptions_for_member.return_value = [
            self.subscription,
            self._build_subscription(product=ProductFactory.build(), cancelled=True),
        ]

        self._validate(cache={})

    def test_validateNoOtherCancelledSubscription_cancelledSubscriptionEndedBeforeDate_doesNotRaise(
        self, mock_get_all_subscriptions_for_member: MagicMock
    ):
        ended_subscription = self._build_subscription(
            product=ProductFactory.build(type=self.product_type), cancelled=True
        )
        ended_subscription.end_date = self.CHANGE_DATE - datetime.timedelta(days=1)
        mock_get_all_subscriptions_for_member.return_value = [
            self.subscription,
            ended_subscription,
        ]

        self._validate(cache={})

    def test_validateNoOtherCancelledSubscription_changeFromNextSeason_checksSubscriptionsOnLastDayOfPreviousContract(
        self, mock_get_all_subscriptions_for_member: MagicMock
    ):
        mock_get_all_subscriptions_for_member.return_value = [
            self.subscription,
            self._build_subscription(
                product=ProductFactory.build(type=self.product_type), cancelled=True
            ),
        ]

        with self.assertRaisesMessage(ValidationError, "Kündigung aufheben"):
            AdminSizeChangeValidator.validate_no_other_cancelled_subscription(
                member=self.member,
                subscription=self.subscription,
                change_date=datetime.date(year=2028, month=1, day=1),
                cache={},
            )
