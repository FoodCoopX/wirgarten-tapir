from unittest.mock import patch, Mock

from django.urls import reverse

from tapir.subscriptions.services.product_updater import ProductUpdater
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    ProductFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestExtendedProductViewPath(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()

    def test_patch_loggedInAsNormalUser_returns403(self):
        member = MemberFactory.create()
        self.client.force_login(member)
        product = ProductFactory.create()

        url = reverse("subscriptions:extended_product")
        response = self.client.patch(f"{url}?product_id={product.id}")

        self.assertStatusCode(response, 403)

    @patch.object(ProductUpdater, "update_product")
    def test_patch_default_callsProductUpdated(self, mock_update_product: Mock):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)
        product = ProductFactory.create()

        data = {
            "id": product.id,
            "name": product.name,
            "deleted": product.deleted,
            "base": product.base,
            "price": 0,
            "size": 0,
            "basket_size_equivalences": [],
            "description_in_bestellwizard": "test description",
            "url_of_image_in_bestellwizard": "https://test.url.com",
            "capacity": 123,
        }

        url = reverse("subscriptions:extended_product")
        response = self.client.patch(
            f"{url}?product_id={product.id}",
            data=data,
            content_type="application/json",
        )

        self.assertStatusCode(response, 200)

        mock_update_product.assert_called_once()
