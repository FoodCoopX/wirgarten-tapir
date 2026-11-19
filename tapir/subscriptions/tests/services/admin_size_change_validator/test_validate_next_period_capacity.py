import datetime
from unittest.mock import patch, MagicMock

from tapir.subscriptions.services.admin_size_change_next_period_finder import (
    AdminSizeChangeNextPeriodFinder,
)
from tapir.subscriptions.services.admin_size_change_validator import (
    AdminSizeChangeValidator,
)
from tapir.subscriptions.services.order_validator import OrderValidator
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    PickupLocationFactory,
    ProductFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(OrderValidator, "validate_capacities", autospec=True)
@patch.object(
    AdminSizeChangeNextPeriodFinder,
    "get_next_period_with_subscriptions",
    autospec=True,
)
class TestAdminSizeChangeValidatorValidateNextPeriodCapacity(TapirUnitTest):
    CHANGE_DATE = datetime.date(year=2027, month=6, day=7)

    def setUp(self):
        super().setUp()
        self.member = MemberFactory.build()
        self.subscription = SubscriptionFactory.build(
            member=self.member,
            period=GrowingPeriodFactory.build(
                start_date=datetime.date(year=2027, month=1, day=1),
                end_date=datetime.date(year=2027, month=12, day=31),
            ),
        )
        self.next_growing_period = GrowingPeriodFactory.build(
            start_date=datetime.date(year=2028, month=1, day=1),
            end_date=datetime.date(year=2028, month=12, day=31),
        )
        self.order = {ProductFactory.build(): 1}
        self.pickup_location = PickupLocationFactory.build()
        self.cache = {}

    def _validate(self, change_date: datetime.date):
        AdminSizeChangeValidator.validate_next_period_capacity(
            member=self.member,
            subscription=self.subscription,
            change_date=change_date,
            order=self.order,
            pickup_location=self.pickup_location,
            cache=self.cache,
        )

    def test_validateNextPeriodCapacity_nextPeriodSubscriptionsExist_validatesOrderAtNextPeriodStart(
        self,
        mock_get_next_period_with_subscriptions: MagicMock,
        mock_validate_capacities: MagicMock,
    ):
        mock_get_next_period_with_subscriptions.return_value = self.next_growing_period

        self._validate(change_date=self.CHANGE_DATE)

        mock_get_next_period_with_subscriptions.assert_called_once_with(
            member=self.member, subscription=self.subscription, cache=self.cache
        )
        mock_validate_capacities.assert_called_once_with(
            order=self.order,
            contract_start_date=self.next_growing_period.start_date,
            member=self.member,
            pickup_location=self.pickup_location,
            cache=self.cache,
        )

    def test_validateNextPeriodCapacity_noNextPeriodSubscriptions_doesNotValidate(
        self,
        mock_get_next_period_with_subscriptions: MagicMock,
        mock_validate_capacities: MagicMock,
    ):
        mock_get_next_period_with_subscriptions.return_value = None

        self._validate(change_date=self.CHANGE_DATE)

        mock_validate_capacities.assert_not_called()

    def test_validateNextPeriodCapacity_changeFromNextPeriod_doesNotValidate(
        self,
        mock_get_next_period_with_subscriptions: MagicMock,
        mock_validate_capacities: MagicMock,
    ):
        self._validate(change_date=datetime.date(year=2028, month=1, day=1))

        mock_get_next_period_with_subscriptions.assert_not_called()
        mock_validate_capacities.assert_not_called()
