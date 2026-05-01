from tapir.payments.services.payment_export_intended_use_builder import (
    PaymentExportIntendedUseBuilder,
)
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.factories import (
    MandateReferenceFactory,
    MemberFactory,
    PaymentFactory,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestBuildIntendedUseLegacy(TapirUnitTest):
    def setUp(self):
        super().setUp()
        member = MemberFactory.build(last_name="Schmidt")
        self.payment = PaymentFactory.build(
            mandate_ref=MandateReferenceFactory.build(member=member)
        )

    def test_buildIntendedUseLegacy_isContracts_returnsCorrectString(self):
        cache = {}
        mock_parameter_value(
            cache=cache, key=ParameterKeys.SITE_NAME, value="test site name"
        )

        result = PaymentExportIntendedUseBuilder._build_intended_use_legacy(
            payment=self.payment, is_contracts=True, cache=cache
        )

        self.assertEqual("test site name, Schmidt, Verträge", result)

    def test_buildIntendedUseLegacy_isCoopShares_returnsCorrectString(self):
        cache = {}
        mock_parameter_value(
            cache=cache, key=ParameterKeys.SITE_NAME, value="test site name"
        )

        result = PaymentExportIntendedUseBuilder._build_intended_use_legacy(
            payment=self.payment, is_contracts=False, cache=cache
        )

        self.assertEqual("test site name, Schmidt, Genossenschaftsanteile", result)
