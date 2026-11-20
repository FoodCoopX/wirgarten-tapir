import datetime
from unittest.mock import patch, MagicMock

from django.urls import reverse
from rest_framework import status
from tapir_mail.triggers.transactional_trigger import TransactionalTrigger

from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    MemberPickupLocationFactory,
    PickupLocationCapabilityFactory,
    PickupLocationFactory,
    ProductCapacityFactory,
    ProductFactory,
    ProductPriceFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


@patch.object(TransactionalTrigger, "fire_action", autospec=True)
class TestAdminSubscriptionAdditionApplyApiView(TapirIntegrationTest):
    START_DATE = datetime.date(year=2030, month=6, day=10)

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls.product = ProductFactory.create(type__delivery_cycle=WEEKLY[0])
        ProductPriceFactory.create(
            product=cls.product,
            valid_from=datetime.date(year=2029, month=1, day=1),
            size=1,
        )
        cls.growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2030, month=1, day=1)
        )
        ProductCapacityFactory.create(
            period=cls.growing_period,
            product_type=cls.product.type,
            capacity=1000,
        )
        pickup_location = PickupLocationFactory.create()
        PickupLocationCapabilityFactory.create(
            pickup_location=pickup_location,
            product_type=cls.product.type,
            max_capacity=1000,
        )
        cls.member = MemberFactory.create()
        MemberPickupLocationFactory.create(
            member=cls.member,
            pickup_location=pickup_location,
            valid_from=datetime.date(year=2029, month=1, day=1),
        )

    def setUp(self) -> None:
        super().setUp()
        mock_timezone(test=self, now=datetime.datetime(year=2030, month=6, day=1))

    def _post(self, quantity: int):
        return self.client.post(
            reverse("subscriptions:admin_subscription_addition_apply"),
            {
                "member_id": self.member.id,
                "product_id": self.product.id,
                "quantity": quantity,
                "start_date": self.START_DATE,
                "prerequisites": {
                    "account_owner": "",
                    "iban": "",
                    "sepa_mandate_confirmed": False,
                },
            },
            content_type="application/json",
        )

    def test_post_normalMember_returns403AndWritesNothing(self, _: MagicMock):
        self.client.force_login(self.member)

        response = self._post(quantity=1)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Subscription.objects.exists())

    def test_post_invalidAddition_returnsErrorAndWritesNothing(
        self, mock_fire_action: MagicMock
    ):
        self._login_as_admin()

        response = self._post(quantity=0)

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_order_not_confirmed(
            response_content=response.json(),
            expected_error="Die Anzahl der Anteile muss mindestens 1 sein.",
        )
        self.assertFalse(Subscription.objects.exists())
        mock_fire_action.assert_not_called()

    def test_post_validAddition_createsSubscription(self, mock_fire_action: MagicMock):
        self._login_as_admin()

        response = self._post(quantity=2)

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_order_confirmed(response_content=response.json())
        subscription = Subscription.objects.get(member=self.member)
        self.assertEqual(self.product, subscription.product)
        self.assertEqual(2, subscription.quantity)
        self.assertEqual(self.START_DATE, subscription.start_date)
        mock_fire_action.assert_called_once()
