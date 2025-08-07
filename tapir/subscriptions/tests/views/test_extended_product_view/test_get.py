from django.urls import reverse

from tapir.configuration.models import TapirParameter
from tapir.pickup_locations.config import PICKING_MODE_BASKET
from tapir.pickup_locations.models import ProductBasketSizeEquivalence
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    ProductFactory,
    ProductPriceFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestExtendedProductViewGet(TapirIntegrationTest):
    maxDiff = 2000

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_loggedInAsNormalUser_returns403(self):
        member = MemberFactory.create()
        self.client.force_login(member)
        product = ProductFactory.create()

        url = reverse("subscriptions:extended_product")
        response = self.client.get(f"{url}?product_id={product.id}")

        self.assertStatusCode(response, 403)

    def test_get_productWithoutPriceObjectOrEquivalences_returnsCorrectData(self):
        member = MemberFactory.create(is_superuser=True)
        TapirParameter.objects.filter(key=ParameterKeys.PICKING_MODE).update(
            value=PICKING_MODE_BASKET
        )
        self.client.force_login(member)
        product = ProductFactory.create(
            name="test product name",
            deleted=False,
            base=True,
            capacity=100,
            min_coop_shares=2,
        )

        url = reverse("subscriptions:extended_product")
        response = self.client.get(f"{url}?product_id={product.id}")

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertEqual(
            {
                "id": product.id,
                "name": "test product name",
                "deleted": False,
                "base": True,
                "picking_mode": PICKING_MODE_BASKET,
                "basket_size_equivalences": [
                    {"basket_size_name": "kleine Kiste", "quantity": 0},
                    {"basket_size_name": "normale Kiste", "quantity": 0},
                ],
                "price": 0.0,
                "size": 0.0,
                "description_in_bestellwizard": "",
                "url_of_image_in_bestellwizard": "",
                "capacity": 100,
                "min_coop_shares": 2,
            },
            response_content,
        )

    def test_get_default_returnsCorrectData(self):
        member = MemberFactory.create(is_superuser=True)
        TapirParameter.objects.filter(key=ParameterKeys.PICKING_MODE).update(
            value=PICKING_MODE_BASKET
        )
        self.client.force_login(member)
        product = ProductFactory.create(
            name="test product name",
            deleted=False,
            base=True,
            description_in_bestellwizard="test description",
            url_of_image_in_bestellwizard="test url",
            capacity=234,
            min_coop_shares=7,
        )
        ProductPriceFactory.create(product=product, price=15.2, size=1.3)
        ProductBasketSizeEquivalence.objects.create(
            basket_size_name="kleine Kiste", quantity=2, product=product
        )
        ProductBasketSizeEquivalence.objects.create(
            basket_size_name="normale Kiste", quantity=3, product=product
        )

        url = reverse("subscriptions:extended_product")
        response = self.client.get(f"{url}?product_id={product.id}")

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertEqual(
            {
                "id": product.id,
                "name": "test product name",
                "deleted": False,
                "base": True,
                "picking_mode": PICKING_MODE_BASKET,
                "basket_size_equivalences": [
                    {"basket_size_name": "kleine Kiste", "quantity": 2},
                    {"basket_size_name": "normale Kiste", "quantity": 3},
                ],
                "price": 15.2,
                "size": 1.3,
                "description_in_bestellwizard": "test description",
                "url_of_image_in_bestellwizard": "test url",
                "capacity": 234,
                "min_coop_shares": 7,
            },
            response_content,
        )
