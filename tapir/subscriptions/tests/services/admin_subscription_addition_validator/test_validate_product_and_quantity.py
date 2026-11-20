from django.core.exceptions import ValidationError

from tapir.subscriptions.services.admin_subscription_addition_validator import (
    AdminSubscriptionAdditionValidator,
)
from tapir.wirgarten.tests.factories import ProductFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestAdminSubscriptionAdditionValidatorValidateProductAndQuantity(TapirUnitTest):
    def test_validateProductAndQuantity_quantityZero_raisesValidationError(self):
        with self.assertRaisesMessage(ValidationError, "mindestens 1"):
            AdminSubscriptionAdditionValidator.validate_product_and_quantity(
                product=ProductFactory.build(), quantity=0
            )

    def test_validateProductAndQuantity_deletedProduct_raisesValidationError(self):
        with self.assertRaisesMessage(ValidationError, "nicht mehr verfügbar"):
            AdminSubscriptionAdditionValidator.validate_product_and_quantity(
                product=ProductFactory.build(deleted=True), quantity=1
            )

    def test_validateProductAndQuantity_validProductAndQuantity_doesNotRaise(self):
        AdminSubscriptionAdditionValidator.validate_product_and_quantity(
            product=ProductFactory.build(), quantity=2
        )
