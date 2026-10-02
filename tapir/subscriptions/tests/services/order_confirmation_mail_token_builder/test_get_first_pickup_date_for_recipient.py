import datetime
from unittest.mock import Mock, patch

from tapir.subscriptions.services.order_confirmation_mail_token_builder import (
    OrderConfirmationMailTokenBuilder,
)
from tapir.wirgarten.constants import NO_DELIVERY, WEEKLY
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestGetFirstPickupDateForRecipient(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_getFirstPickupDateForRecipient_memberWithoutSubscriptions_returnsKeineLieferung(
        self,
    ):
        member = MemberFactory.create()

        result = OrderConfirmationMailTokenBuilder.get_first_pickup_date_for_recipient(
            recipient=member, cache={}
        )

        self.assertEqual("Keine Lieferung", result)

    @patch(
        "tapir.subscriptions.services.order_confirmation_mail_token_builder.DeliveryDateCalculator.get_next_delivery_date_for_product_type",
        autospec=True,
    )
    def test_getFirstPickupDateForRecipient_memberWithDeliverySubscription_returnsFormattedDate(
        self, mock_get_next_delivery_date_for_product_type: Mock
    ):
        mock_timezone(self, datetime.datetime(year=2026, month=5, day=11))
        member = MemberFactory.create()
        SubscriptionFactory.create(
            member=member,
            start_date=datetime.date(year=2026, month=5, day=1),
            end_date=datetime.date(year=2027, month=4, day=30),
            product__type__delivery_cycle=WEEKLY[0],
        )
        mock_get_next_delivery_date_for_product_type.return_value = datetime.date(
            year=2026, month=5, day=14
        )

        result = OrderConfirmationMailTokenBuilder.get_first_pickup_date_for_recipient(
            recipient=member, cache={}
        )

        self.assertEqual("14.05.2026", result)
        mock_get_next_delivery_date_for_product_type.assert_called_once()

    def test_getFirstPickupDateForRecipient_memberWithOnlyNoDeliverySubscription_returnsKeineLieferung(
        self,
    ):
        mock_timezone(self, datetime.datetime(year=2026, month=5, day=11))
        member = MemberFactory.create()
        SubscriptionFactory.create(
            member=member,
            start_date=datetime.date(year=2026, month=5, day=1),
            end_date=datetime.date(year=2027, month=4, day=30),
            product__type__delivery_cycle=NO_DELIVERY[0],
        )

        result = OrderConfirmationMailTokenBuilder.get_first_pickup_date_for_recipient(
            recipient=member, cache={}
        )

        self.assertEqual("Keine Lieferung", result)
