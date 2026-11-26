import datetime
from unittest.mock import patch, MagicMock

from tapir.deliveries.services.get_deliveries_service import GetDeliveriesService
from tapir.subscriptions.services.subscription_delivered_in_week_checked import (
    SubscriptionDeliveredInWeekChecker,
)
from tapir.subscriptions.views.cancellations import CancelSubscriptionsView
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.tests.factories import MemberFactory, SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch(
    "tapir.subscriptions.views.cancellations.get_today",
    autospec=True,
    return_value=datetime.date(year=2023, month=3, day=15),
)
@patch.object(GetDeliveriesService, "get_deliveries", autospec=True, return_value=[])
@patch.object(
    SubscriptionDeliveredInWeekChecker,
    "is_subscription_delivered_in_week",
    autospec=True,
    return_value=True,
)
class TestBuildLastPickupDate(TapirUnitTest):
    def test_buildLastPickupDate_noDeliveriesLeft_returnsPastText(
        self, _: MagicMock, __: MagicMock, ___: MagicMock
    ):
        result = CancelSubscriptionsView()._build_last_pickup_date(
            member=MemberFactory.build(),
            contract_end_date=datetime.date(year=2023, month=4, day=2),
        )

        self.assertEqual("Letzte Abholung schon vergangen", result)

    def test_buildLastPickupDate_default_returnsDateOfLastDeliveryUntilContractEnd(
        self,
        mock_is_subscription_delivered_in_week: MagicMock,
        mock_get_deliveries: MagicMock,
        _: MagicMock,
    ):
        member = MemberFactory.build()
        subscription = SubscriptionFactory.build()
        mock_get_deliveries.return_value = [
            self._build_delivery(day=22, subscriptions=[subscription]),
            self._build_delivery(day=29, subscriptions=[subscription]),
        ]
        view = CancelSubscriptionsView()

        result = view._build_last_pickup_date(
            member=member,
            contract_end_date=datetime.date(year=2023, month=4, day=2),
        )

        self.assertEqual("29.03.2023", result)
        mock_get_deliveries.assert_called_once_with(
            member=member,
            date_from=datetime.date(year=2023, month=3, day=15),
            date_to=datetime.date(year=2023, month=4, day=2),
            cache=view.cache,
        )
        mock_is_subscription_delivered_in_week.assert_called_with(
            subscription=subscription,
            delivery_date=datetime.date(year=2023, month=3, day=29),
            cache=view.cache,
            skip_donation_check=False,
        )

    def test_buildLastPickupDate_lastDeliveryNotDelivered_returnsPreviousDelivery(
        self,
        mock_is_subscription_delivered_in_week: MagicMock,
        mock_get_deliveries: MagicMock,
        _: MagicMock,
    ):
        mock_get_deliveries.return_value = [
            self._build_delivery(day=22, subscriptions=[SubscriptionFactory.build()]),
            self._build_delivery(day=29, subscriptions=[SubscriptionFactory.build()]),
        ]
        mock_is_subscription_delivered_in_week.side_effect = (
            lambda subscription, delivery_date, cache, skip_donation_check: delivery_date.day
            == 22
        )

        result = CancelSubscriptionsView()._build_last_pickup_date(
            member=MemberFactory.build(),
            contract_end_date=datetime.date(year=2023, month=4, day=2),
        )

        self.assertEqual("22.03.2023", result)

    def test_buildLastPickupDate_onlyOneSubscriptionOfLastDeliveryDelivered_returnsLastDelivery(
        self,
        mock_is_subscription_delivered_in_week: MagicMock,
        mock_get_deliveries: MagicMock,
        _: MagicMock,
    ):
        delivered_subscription = SubscriptionFactory.build()
        mock_get_deliveries.return_value = [
            self._build_delivery(
                day=29,
                subscriptions=[SubscriptionFactory.build(), delivered_subscription],
            ),
        ]
        mock_is_subscription_delivered_in_week.side_effect = (
            lambda subscription, delivery_date, cache, skip_donation_check: subscription
            is delivered_subscription
        )

        result = CancelSubscriptionsView()._build_last_pickup_date(
            member=MemberFactory.build(),
            contract_end_date=datetime.date(year=2023, month=4, day=2),
        )

        self.assertEqual("29.03.2023", result)

    def test_buildLastPickupDate_noActualPickupLeft_returnsPastText(
        self,
        mock_is_subscription_delivered_in_week: MagicMock,
        mock_get_deliveries: MagicMock,
        _: MagicMock,
    ):
        mock_get_deliveries.return_value = [
            self._build_delivery(day=22, subscriptions=[SubscriptionFactory.build()]),
            self._build_delivery(day=29, subscriptions=[]),
        ]
        mock_is_subscription_delivered_in_week.return_value = False

        result = CancelSubscriptionsView()._build_last_pickup_date(
            member=MemberFactory.build(),
            contract_end_date=datetime.date(year=2023, month=4, day=2),
        )

        self.assertEqual("Letzte Abholung schon vergangen", result)

    @staticmethod
    def _build_delivery(day: int, subscriptions: list[Subscription]) -> dict:
        return {
            "delivery_date": datetime.date(year=2023, month=3, day=day),
            "subscriptions": subscriptions,
        }
