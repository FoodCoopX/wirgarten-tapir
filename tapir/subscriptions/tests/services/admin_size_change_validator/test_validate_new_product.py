from django.core.exceptions import ValidationError

from tapir.subscriptions.services.admin_size_change_validator import (
    AdminSizeChangeValidator,
)
from tapir.wirgarten.tests.factories import (
    ProductFactory,
    ProductTypeFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestAdminSizeChangeValidatorValidateNewProduct(TapirUnitTest):
    def setUp(self):
        super().setUp()
        self.product_type = ProductTypeFactory.build()
        self.subscription = SubscriptionFactory.build(
            product=ProductFactory.build(type=self.product_type)
        )

    def test_validateNewProduct_otherProductOfSameType_doesNotRaise(self):
        AdminSizeChangeValidator.validate_new_product(
            subscription=self.subscription,
            new_product=ProductFactory.build(type=self.product_type),
        )

    def test_validateNewProduct_productOfOtherType_raisesValidationError(self):
        with self.assertRaisesMessage(ValidationError, "gleichen Produktanteil"):
            AdminSizeChangeValidator.validate_new_product(
                subscription=self.subscription, new_product=ProductFactory.build()
            )

    def test_validateNewProduct_productDeleted_raisesValidationError(self):
        with self.assertRaisesMessage(ValidationError, "nicht mehr verfügbar"):
            AdminSizeChangeValidator.validate_new_product(
                subscription=self.subscription,
                new_product=ProductFactory.build(type=self.product_type, deleted=True),
            )

    def test_validateNewProduct_sameProduct_raisesValidationError(self):
        with self.assertRaisesMessage(ValidationError, "von der bisherigen"):
            AdminSizeChangeValidator.validate_new_product(
                subscription=self.subscription,
                new_product=self.subscription.product,
            )
