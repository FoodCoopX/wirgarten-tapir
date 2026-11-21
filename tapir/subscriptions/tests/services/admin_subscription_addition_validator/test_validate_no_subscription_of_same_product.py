import datetime
from unittest.mock import patch, MagicMock

from django.core.exceptions import ValidationError

from tapir.subscriptions.services.admin_subscription_addition_validator import (
    AdminSubscriptionAdditionValidator,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    ProductFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(TapirCache, "get_all_subscriptions_for_member", autospec=True)
class TestAdminSubscriptionAdditionValidatorValidateNoSubscriptionOfSameProduct(
    TapirUnitTest
):
    START_DATE = datetime.date(year=2027, month=6, day=7)

    def setUp(self):
        super().setUp()
        self.member = MemberFactory.build()
        self.product = ProductFactory.build()
        self.growing_period = GrowingPeriodFactory.build(
            start_date=datetime.date(year=2027, month=1, day=1),
            end_date=datetime.date(year=2027, month=12, day=31),
        )

    def _validate(self, cache: dict):
        AdminSubscriptionAdditionValidator.validate_no_subscription_of_same_product(
            member=self.member,
            product=self.product,
            start_date=self.START_DATE,
            cache=cache,
        )

    def test_validateNoSubscriptionOfSameProduct_sameProductActiveAtStartDate_raisesValidationError(
        self, mock_get_all_subscriptions_for_member: MagicMock
    ):
        mock_get_all_subscriptions_for_member.return_value = [
            SubscriptionFactory.build(
                member=self.member, product=self.product, period=self.growing_period
            )
        ]
        cache = {}

        with self.assertRaisesMessage(ValidationError, "FoodCoopX-Admins"):
            self._validate(cache=cache)

        mock_get_all_subscriptions_for_member.assert_called_once_with(
            member_id=self.member.id, cache=cache
        )

    def test_validateNoSubscriptionOfSameProduct_sameProductStartsLater_raisesValidationError(
        self, mock_get_all_subscriptions_for_member: MagicMock
    ):
        mock_get_all_subscriptions_for_member.return_value = [
            SubscriptionFactory.build(
                member=self.member,
                product=self.product,
                period=GrowingPeriodFactory.build(
                    start_date=datetime.date(year=2028, month=1, day=1),
                    end_date=datetime.date(year=2028, month=12, day=31),
                ),
            )
        ]

        with self.assertRaisesMessage(ValidationError, "FoodCoopX-Admins"):
            self._validate(cache={})

    def test_validateNoSubscriptionOfSameProduct_sameProductEndedBeforeStartDate_doesNotRaise(
        self, mock_get_all_subscriptions_for_member: MagicMock
    ):
        ended_subscription = SubscriptionFactory.build(
            member=self.member, product=self.product, period=self.growing_period
        )
        ended_subscription.end_date = self.START_DATE - datetime.timedelta(days=1)
        mock_get_all_subscriptions_for_member.return_value = [ended_subscription]

        self._validate(cache={})

    def test_validateNoSubscriptionOfSameProduct_otherProductOfSameType_doesNotRaise(
        self, mock_get_all_subscriptions_for_member: MagicMock
    ):
        mock_get_all_subscriptions_for_member.return_value = [
            SubscriptionFactory.build(
                member=self.member,
                product=ProductFactory.build(type=self.product.type),
                period=self.growing_period,
            )
        ]

        self._validate(cache={})
