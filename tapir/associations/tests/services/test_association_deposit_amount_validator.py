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

    def test_minimum_and_higher_increments_are_valid(self):
        for amount in ["200.00", "250.00", "300.00"]:
            with self.subTest(amount=amount):
                AssociationDepositAmountValidator.validate_regular_deposit_amount(
                    Decimal(amount), cache=self.cache
                )

    def test_amount_below_minimum_is_rejected(self):
        with self.assertRaisesMessage(ValidationError, "Mindesteinlage"):
            AssociationDepositAmountValidator.validate_regular_deposit_amount(
                Decimal("199.99"), cache=self.cache
            )

    def test_amount_between_increments_is_rejected(self):
        with self.assertRaisesMessage(ValidationError, "Schritte"):
            AssociationDepositAmountValidator.validate_regular_deposit_amount(
                Decimal("225.00"), cache=self.cache
            )

    def test_cent_increments_are_measured_from_the_minimum(self):
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

    def test_invalid_amounts_are_rejected_without_rounding(self):
        for amount in ["0", "-1", "250.001", "1000000", "NaN", "sNaN", "Infinity"]:
            with self.subTest(amount=amount), self.assertRaises(ValidationError):
                AssociationDepositAmountValidator.validate_regular_deposit_amount(
                    Decimal(amount), cache=self.cache
                )

    def test_largest_amount_with_cent_increment_is_valid(self):
        mock_parameter_value(
            self.cache, ParameterKeys.ASSOCIATION_DEPOSIT_INCREMENT, Decimal("0.01")
        )

        AssociationDepositAmountValidator.validate_regular_deposit_amount(
            Decimal("999999.99"), cache=self.cache
        )

    def test_invalid_stored_rules_are_rejected(self):
        for key in [
            ParameterKeys.ASSOCIATION_DEPOSIT_MINIMUM,
            ParameterKeys.ASSOCIATION_DEPOSIT_INCREMENT,
        ]:
            for value in ["0", "-1", "0.001", "NaN"]:
                with self.subTest(key=key, value=value):
                    cache = {}
                    mock_parameter_value(
                        cache, ParameterKeys.ASSOCIATION_DEPOSIT_MINIMUM, Decimal(200)
                    )
                    mock_parameter_value(
                        cache, ParameterKeys.ASSOCIATION_DEPOSIT_INCREMENT, Decimal(50)
                    )
                    mock_parameter_value(cache, key, Decimal(value))
                    with self.assertRaises(ValidationError):
                        AssociationDepositAmountValidator.validate_regular_deposit_amount(
                            Decimal(200), cache=cache
                        )
