from decimal import Decimal

from django.core.exceptions import ValidationError

from tapir.associations.services.association_deposit_amount_validator import (
    AssociationDepositAmountValidator,
)
from tapir.configuration.forms import ParameterForm
from tapir.configuration.models import TapirParameter
from tapir.configuration.parameter import get_parameter_value
from tapir.core.config import (
    LEGAL_STATUS_ASSOCIATION,
    LEGAL_STATUS_COMPANY,
    LEGAL_STATUS_COOPERATIVE,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestDepositParameterDefinitions(TapirIntegrationTest):
    parameter_keys = [
        ParameterKeys.ASSOCIATION_DEPOSIT_NAME,
        ParameterKeys.ASSOCIATION_DEPOSIT_MINIMUM,
        ParameterKeys.ASSOCIATION_DEPOSIT_INCREMENT,
    ]

    option_keys = [
        ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED,
        ParameterKeys.ASSOCIATION_DEPOSIT_SUPPORTING_MEMBERS_REQUIRED,
        ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_LARGER_SIGNUP,
        ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_MEMBER_INCREASE,
    ]

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_parameters_are_visible_only_for_associations(self):
        for legal_status in [
            LEGAL_STATUS_ASSOCIATION,
            LEGAL_STATUS_COMPANY,
            LEGAL_STATUS_COOPERATIVE,
        ]:
            with self.subTest(legal_status=legal_status):
                self._set_parameter(
                    ParameterKeys.ORGANISATION_LEGAL_STATUS, legal_status
                )
                form = ParameterForm()
                for key in [*self.parameter_keys, *self.option_keys]:
                    self.assertEqual(
                        legal_status == LEGAL_STATUS_ASSOCIATION, key in form.fields
                    )

    def test_reimport_preserves_custom_values_and_unrelated_parameters(self):
        custom_values = {
            ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED: "True",
            ParameterKeys.ASSOCIATION_DEPOSIT_SUPPORTING_MEMBERS_REQUIRED: "False",
            ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_LARGER_SIGNUP: "True",
            ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_MEMBER_INCREASE: "True",
            ParameterKeys.ASSOCIATION_DEPOSIT_NAME: "Investitionsbeitrag",
            ParameterKeys.ASSOCIATION_DEPOSIT_MINIMUM: "125.00",
            ParameterKeys.ASSOCIATION_DEPOSIT_INCREMENT: "12.50",
        }
        for key, value in custom_values.items():
            self._set_parameter(key, value)
        before = dict(TapirParameter.objects.values_list("key", "value"))

        ParameterDefinitions().import_definitions()

        self.assertEqual(
            before, dict(TapirParameter.objects.values_list("key", "value"))
        )
        self.assertEqual(
            "Investitionsbeitrag",
            get_parameter_value(ParameterKeys.ASSOCIATION_DEPOSIT_NAME, cache={}),
        )
        AssociationDepositAmountValidator.validate_regular_deposit_amount(
            Decimal("137.50"), cache={}
        )

    def test_parameter_form_rejects_invalid_monetary_values(self):
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION
        )
        form = ParameterForm()

        for key in self.parameter_keys[1:]:
            field = form.fields[key]
            for value in ["0", "-1", "0.001", "1000000", "NaN", "Infinity"]:
                with self.subTest(key=key, value=value), self.assertRaises(
                    ValidationError
                ):
                    field.clean(value)
            for value in ["0.01", "200.00", "999999.99"]:
                with self.subTest(key=key, value=value):
                    self.assertEqual(Decimal(value), field.clean(value))

    def test_validation_reuses_request_cache(self):
        cache = {}
        with self.assertNumQueries(1):
            AssociationDepositAmountValidator.validate_regular_deposit_amount(
                Decimal(200), cache=cache
            )
        with self.assertNumQueries(0):
            AssociationDepositAmountValidator.validate_regular_deposit_amount(
                Decimal(250), cache=cache
            )

    def test_stored_cent_values_are_validated_without_float_rounding(self):
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_MINIMUM, "200.01")
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_INCREMENT, "0.03")
        cache = {}

        AssociationDepositAmountValidator.validate_regular_deposit_amount(
            Decimal("200.04"), cache=cache
        )
        with self.assertRaisesMessage(ValidationError, "Schritte"):
            AssociationDepositAmountValidator.validate_regular_deposit_amount(
                Decimal("200.03"), cache=cache
            )
