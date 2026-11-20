import datetime

from django.urls import reverse
from rest_framework import status

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


class TestAdminSubscriptionAdditionCheckApiView(TapirIntegrationTest):
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
            reverse("subscriptions:admin_subscription_addition_check"),
            {
                "member_id": self.member.id,
                "product_id": self.product.id,
                "quantity": quantity,
                "start_date": self.START_DATE,
                "account_owner": "",
                "iban": "",
                "sepa_mandate_confirmed": False,
            },
            format="json",
        )

    def test_post_normalMember_returns403(self):
        self.client.force_login(self.member)

        response = self._post(quantity=1)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_post_validAddition_returnsOkAndWritesNothing(self):
        self._login_as_admin()

        response = self._post(quantity=1)

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_order_confirmed(response_content=response.json())
        self.assertFalse(Subscription.objects.exists())

    def test_post_invalidAddition_returnsError(self):
        self._login_as_admin()

        response = self._post(quantity=0)

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_order_not_confirmed(
            response_content=response.json(),
            expected_error="Die Anzahl der Anteile muss mindestens 1 sein.",
        )
