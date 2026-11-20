import datetime

from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.models import Product, Subscription
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberPickupLocationFactory,
    PickupLocationCapabilityFactory,
    PickupLocationFactory,
    ProductCapacityFactory,
    ProductFactory,
    ProductPriceFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestAdminSizeChangeCheckApiView(TapirIntegrationTest):
    CHANGE_DATE = datetime.date(year=2030, month=6, day=10)

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls.product_small = ProductFactory.create(type__delivery_cycle=WEEKLY[0])
        cls.product_medium = ProductFactory.create(type=cls.product_small.type)
        for product in [cls.product_small, cls.product_medium]:
            ProductPriceFactory.create(
                product=product,
                valid_from=datetime.date(year=2029, month=1, day=1),
                size=1,
            )
        cls.growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2030, month=1, day=1)
        )
        ProductCapacityFactory.create(
            period=cls.growing_period,
            product_type=cls.product_small.type,
            capacity=1000,
        )
        pickup_location = PickupLocationFactory.create()
        PickupLocationCapabilityFactory.create(
            pickup_location=pickup_location,
            product_type=cls.product_small.type,
            max_capacity=1000,
        )
        cls.subscription = SubscriptionFactory.create(
            period=cls.growing_period, product=cls.product_small
        )
        MemberPickupLocationFactory.create(
            member=cls.subscription.member,
            pickup_location=pickup_location,
            valid_from=datetime.date(year=2029, month=1, day=1),
        )

    def setUp(self) -> None:
        super().setUp()
        mock_timezone(test=self, now=datetime.datetime(year=2030, month=6, day=1))

    def _post(self, new_product: Product):
        return self.client.post(
            reverse("subscriptions:admin_size_change_check"),
            {
                "member_id": self.subscription.member.id,
                "subscription_id": self.subscription.id,
                "new_product_id": new_product.id,
                "change_date": self.CHANGE_DATE,
                "prerequisites": {
                    "account_owner": "",
                    "iban": "",
                    "sepa_mandate_confirmed": False,
                },
            },
            content_type="application/json",
        )

    def test_post_normalMember_returns403(self):
        self.client.force_login(self.subscription.member)

        response = self._post(new_product=self.product_medium)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_post_validChange_returnsOkAndWritesNothing(self):
        self._login_as_admin()

        response = self._post(new_product=self.product_medium)

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual({"order_confirmed": True, "error": None}, response.json())
        self.assertEqual(
            [self.subscription.id],
            list(Subscription.objects.values_list("id", flat=True)),
        )
        self.subscription.refresh_from_db()
        self.assertIsNone(self.subscription.cancellation_ts)

    def test_post_invalidChange_returnsError(self):
        self._login_as_admin()

        response = self._post(new_product=self.product_small)

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(
            {
                "order_confirmed": False,
                "error": "Die neue Produktanteilsgröße muss sich von der bisherigen unterscheiden.",
            },
            response.json(),
        )
