import datetime
from unittest.mock import Mock, patch

from tapir_mail.models import StaticSegmentRecipient

from tapir.subscriptions.services.order_confirmation_mail_token_builder import (
    OrderConfirmationMailTokenBuilder,
)
from tapir.wirgarten.constants import NO_DELIVERY, WEEKLY
from tapir.wirgarten.tests.factories import MemberFactory, SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetFirstPickupDate(TapirUnitTest):
    def test_getFirstPickupDateText_onlyNoDeliveryProducts_returnsKeineLieferung(self):
        member = MemberFactory.build()
        subscription = SubscriptionFactory.build(
            product__type__delivery_cycle=NO_DELIVERY[0]
        )

        result = OrderConfirmationMailTokenBuilder.get_first_pickup_date_text(
            member=member, subscriptions=[subscription], cache={}
        )

        self.assertEqual("Keine Lieferung", result)

    @patch(
        "tapir.subscriptions.services.order_confirmation_mail_token_builder.MemberPickupLocationGetter.get_member_pickup_location_id",
        autospec=True,
    )
    @patch(
        "tapir.subscriptions.services.order_confirmation_mail_token_builder.DeliveryDateCalculator.get_next_delivery_date_for_product_type",
        autospec=True,
    )
    def test_getFirstPickupDateText_severalDeliveries_returnsEarliestDate(
        self,
        mock_get_next_delivery_date_for_product_type: Mock,
        mock_get_member_pickup_location_id: Mock,
    ):
        member = MemberFactory.build()
        cache = {}
        subscription_later = SubscriptionFactory.build(
            product__type__delivery_cycle=WEEKLY[0],
            start_date=datetime.date(year=2026, month=6, day=1),
        )
        subscription_earlier = SubscriptionFactory.build(
            product__type__delivery_cycle=WEEKLY[0],
            start_date=datetime.date(year=2026, month=5, day=11),
        )
        mock_get_member_pickup_location_id.return_value = "pickup-location-id"
        mock_get_next_delivery_date_for_product_type.side_effect = [
            datetime.date(year=2026, month=6, day=4),
            datetime.date(year=2026, month=5, day=14),
        ]

        result = OrderConfirmationMailTokenBuilder.get_first_pickup_date_text(
            member=member,
            subscriptions=[subscription_later, subscription_earlier],
            cache=cache,
        )

        self.assertEqual("14.05.2026", result)
        self.assertEqual(2, mock_get_next_delivery_date_for_product_type.call_count)

    def test_getFirstPickupDateText_noSubscriptions_returnsKeineLieferung(self):
        result = OrderConfirmationMailTokenBuilder.get_first_pickup_date_text(
            member=MemberFactory.build(), subscriptions=[], cache={}
        )

        self.assertEqual("Keine Lieferung", result)

    def test_getFirstPickupDateForRecipient_staticRecipient_returnsKeineLieferung(self):
        result = OrderConfirmationMailTokenBuilder.get_first_pickup_date_for_recipient(
            recipient=StaticSegmentRecipient(), cache={}
        )

        self.assertEqual("Keine Lieferung", result)
