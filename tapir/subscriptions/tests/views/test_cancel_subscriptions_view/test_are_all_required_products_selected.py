from tapir.subscriptions.views.cancellations import CancelSubscriptionsView
from tapir.wirgarten.tests.factories import ProductTypeFactory, ProductFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestAreAllRequiredProductsSelected(TapirUnitTest):
    def test_areAllRequiredProductsSelected_allBaseProductsSelected_returnsTrue(self):
        required_product_type_1, required_product_type_2 = (
            ProductTypeFactory.build_batch(must_be_subscribed_to=True, size=2)
        )

        required_product_1 = ProductFactory.build(type=required_product_type_1)
        required_product_2 = ProductFactory.build(type=required_product_type_1)
        required_product_3 = ProductFactory.build(type=required_product_type_2)
        additional_product = ProductFactory.build(type__must_be_subscribed_to=False)
        subscribed_products = {
            required_product_1,
            required_product_2,
            required_product_3,
            additional_product,
        }
        products_selected_for_cancellation = {
            required_product_1,
            required_product_2,
            required_product_3,
        }

        result = CancelSubscriptionsView.are_all_required_products_selected(
            subscribed_products=subscribed_products,
            products_selected_for_cancellation=products_selected_for_cancellation,
        )

        self.assertTrue(result)

    def test_areAllRequiredProductsSelected_notAllBaseProductsSelected_returnsFalse(
        self,
    ):
        required_product_type_1, required_product_type_2 = (
            ProductTypeFactory.build_batch(must_be_subscribed_to=True, size=2)
        )

        required_product_1 = ProductFactory.build(type=required_product_type_1)
        required_product_2 = ProductFactory.build(type=required_product_type_1)
        required_product_3 = ProductFactory.build(type=required_product_type_2)
        additional_product = ProductFactory.build(type__must_be_subscribed_to=False)
        subscribed_products = {
            required_product_1,
            required_product_2,
            required_product_3,
            additional_product,
        }
        products_selected_for_cancellation = {
            required_product_1,
            required_product_3,
        }

        result = CancelSubscriptionsView.are_all_required_products_selected(
            subscribed_products=subscribed_products,
            products_selected_for_cancellation=products_selected_for_cancellation,
        )

        self.assertFalse(result)
