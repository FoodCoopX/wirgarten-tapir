from django.core.exceptions import ValidationError

from tapir.subscriptions.services.admin_subscription_addition_validator import (
    AdminSubscriptionAdditionValidator,
)
from tapir.wirgarten.tests.factories import ProductFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestAdminSubscriptionAdditionValidatorValidateProduct(TapirUnitTest):
    def test_validateProduct_quantityZero_raisesValidationError(self):
        with self.assertRaisesMessage(ValidationError, "mindestens 1"):
            AdminSubscriptionAdditionValidator.validate_product(
                product=ProductFactory.build(), quantity=0
            )

    def test_validateProduct_deletedProduct_raisesValidationError(self):
        with self.assertRaisesMessage(ValidationError, "nicht mehr verfügbar"):
            AdminSubscriptionAdditionValidator.validate_product(
                product=ProductFactory.build(deleted=True), quantity=1
            )

    def test_validateProduct_validProductAndQuantity_doesNotRaise(self):
        AdminSubscriptionAdditionValidator.validate_product(
            product=ProductFactory.build(), quantity=2
        )
