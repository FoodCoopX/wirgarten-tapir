from decimal import Decimal

from django.core.exceptions import ValidationError

from tapir.associations.services.association_deposit_amount_validator import (
    AssociationDepositAmountValidator,
)
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestAssociationDepositAmountValidator(TapirUnitTest):
    def setUp(self):
        super().setUp()
        self.cache = {}
        mock_parameter_value(
            self.cache, ParameterKeys.ASSOCIATION_DEPOSIT_MINIMUM, Decimal("200.00")
        )
        mock_parameter_value(
            self.cache, ParameterKeys.ASSOCIATION_DEPOSIT_INCREMENT, Decimal("50.00")
        )

    def test_validateRegularDepositAmount_default_acceptsAmount(self):
        for amount in ["200.00", "250.00", "300.00"]:
            with self.subTest(amount=amount):
                AssociationDepositAmountValidator.validate_regular_deposit_amount(
                    Decimal(amount), cache=self.cache
                )

    def test_validateRegularDepositAmount_belowMinimum_raisesError(self):
        with self.assertRaisesMessage(ValidationError, "Mindesteinlage"):
            AssociationDepositAmountValidator.validate_regular_deposit_amount(
                Decimal("199.99"), cache=self.cache
            )

    def test_validateRegularDepositAmount_betweenSteps_raisesError(self):
        with self.assertRaisesMessage(ValidationError, "Schritte"):
            AssociationDepositAmountValidator.validate_regular_deposit_amount(
                Decimal("225.00"), cache=self.cache
            )

    def test_validateRegularDepositAmount_centIncrement_checksStepsFromMinimum(self):
        mock_parameter_value(
            self.cache, ParameterKeys.ASSOCIATION_DEPOSIT_MINIMUM, Decimal("200.01")
        )
        mock_parameter_value(
            self.cache, ParameterKeys.ASSOCIATION_DEPOSIT_INCREMENT, Decimal("0.03")
        )

        AssociationDepositAmountValidator.validate_regular_deposit_amount(
            Decimal("200.04"), cache=self.cache
        )
        with self.assertRaisesMessage(ValidationError, "Schritte"):
            AssociationDepositAmountValidator.validate_regular_deposit_amount(
                Decimal("200.03"), cache=self.cache
            )

    def test_validateRegularDepositAmount_invalidPrecisionOrSize_raisesError(self):
        for amount in ["250.001", "1000000", "NaN", "Infinity"]:
            with self.subTest(amount=amount), self.assertRaises(ValidationError):
                AssociationDepositAmountValidator.validate_regular_deposit_amount(
                    Decimal(amount), cache=self.cache
                )
