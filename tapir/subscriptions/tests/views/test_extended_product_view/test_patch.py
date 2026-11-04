from unittest.mock import patch, Mock

from django.urls import reverse

from tapir.subscriptions.services.product_updater import ProductUpdater
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    ProductFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestExtendedProductViewPatch(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_patch_loggedInAsNormalUser_returns403(self):
        member = MemberFactory.create()
        self.client.force_login(member)
        product = ProductFactory.create()

        url = reverse("subscriptions:extended_product")
        response = self.client.patch(f"{url}?product_id={product.id}")

        self.assertStatusCode(response, 403)

    @patch.object(ProductUpdater, "update_product", autospec=True)
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
            "min_coop_shares": 2,
            "hidden_in_bestell_wizard": True,
            "solidarity_choices": "-10,0,10",
        }

        url = reverse("subscriptions:extended_product")
        response = self.client.patch(
            f"{url}?product_id={product.id}",
            data=data,
            content_type="application/json",
        )

        self.assertStatusCode(response, 200)

        mock_update_product.assert_called_once()
        serializer = mock_update_product.call_args.args[-1]
        self.assertEqual("-10,0,10", serializer.validated_data["solidarity_choices"])

    @patch.object(ProductUpdater, "update_product", autospec=True)
    def test_patch_invalidSolidarityChoices_returns400(self, mock_update_product: Mock):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)
        product = ProductFactory.create()
        url = reverse("subscriptions:extended_product")

        for solidarity_choices in ["abc", "-10,nan", "inf"]:
            with self.subTest(solidarity_choices=solidarity_choices):
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
                    "min_coop_shares": 2,
                    "hidden_in_bestell_wizard": True,
                    "solidarity_choices": solidarity_choices,
                }

                response = self.client.patch(
                    f"{url}?product_id={product.id}",
                    data=data,
                    content_type="application/json",
                )

                self.assertStatusCode(response, 400)

        mock_update_product.assert_not_called()

    def test_patch_default_solidarityChoicesSaved(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)
        product = ProductFactory.create(solidarity_choices="")
        growing_period = GrowingPeriodFactory.create()

        data = {
            "id": product.id,
            "name": product.name,
            "deleted": product.deleted,
            "base": product.base,
            "price": 10,
            "size": 1,
            "basket_size_equivalences": [],
            "growing_period_id": growing_period.id,
            "description_in_bestellwizard": "test description",
            "url_of_image_in_bestellwizard": "https://test.url.com",
            "capacity": 123,
            "min_coop_shares": 2,
            "hidden_in_bestell_wizard": False,
            "solidarity_choices": "-10,0,10",
        }

        url = reverse("subscriptions:extended_product")
        response = self.client.patch(
            f"{url}?product_id={product.id}",
            data=data,
            content_type="application/json",
        )

        self.assertStatusCode(response, 200)
        product.refresh_from_db()
        self.assertEqual("-10,0,10", product.solidarity_choices)
