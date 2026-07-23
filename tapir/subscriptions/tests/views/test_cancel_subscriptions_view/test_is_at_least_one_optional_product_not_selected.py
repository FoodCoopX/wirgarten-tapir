from tapir.subscriptions.views.cancellations import CancelSubscriptionsView
from tapir.wirgarten.tests.factories import ProductFactory, ProductTypeFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestIsAtLeastOneOptionalProductNotSelected(TapirUnitTest):
    def test_isAtLeastOneOptionalProductNotSelected_oneOptionalProductNotSelected_returnsTrue(
        self,
    ):
        required_product_type = ProductTypeFactory.build(must_be_subscribed_to=True)

        required_product = ProductFactory.build(type=required_product_type)
        optional_product_selected = ProductFactory.build(
            type__must_be_subscribed_to=False
        )
        optional_product_not_selected = ProductFactory.build(
            type__must_be_subscribed_to=False
        )
        subscribed_products = {
            required_product,
            optional_product_selected,
            optional_product_not_selected,
        }
        products_selected_for_cancellation = {
            required_product,
            optional_product_selected,
        }

        result = CancelSubscriptionsView.is_at_least_one_optional_product_not_selected(
            subscribed_products=subscribed_products,
            products_selected_for_cancellation=products_selected_for_cancellation,
        )

        self.assertTrue(result)

    def test_isAtLeastOneOptionalProductNotSelected_allOptionalProductsSelected_returnsFalse(
        self,
    ):
        required_product_type = ProductTypeFactory.build(must_be_subscribed_to=True)

        required_product = ProductFactory.build(type=required_product_type)
        optional_product_1 = ProductFactory.build(type__must_be_subscribed_to=False)
        optional_product_2 = ProductFactory.build(type__must_be_subscribed_to=False)
        subscribed_products = {
            required_product,
            optional_product_1,
            optional_product_2,
        }
        products_selected_for_cancellation = {
            required_product,
            optional_product_1,
            optional_product_2,
        }

        result = CancelSubscriptionsView.is_at_least_one_optional_product_not_selected(
            subscribed_products=subscribed_products,
            products_selected_for_cancellation=products_selected_for_cancellation,
        )

        self.assertFalse(result)
