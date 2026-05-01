import datetime
from decimal import Decimal

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.generic_exports.services.payment_column_provider import PaymentColumnProvider
from tapir.payments.services.month_payment_builder_solidarity_contributions import (
    MonthPaymentBuilderSolidarityContributions,
)
from tapir.wirgarten.tests.factories import MemberFactory, PaymentFactory


class TestPaymentColumnProvider(TapirUnitTest):
    def test_getValueMemberFullName_default_returnsCorrectName(self):
        member = MemberFactory.build(first_name="John", last_name="Doe")
        payment = PaymentFactory.build(mandate_ref__member=member)

        result = PaymentColumnProvider.get_value_member_full_name(payment, None, None)

        self.assertEqual("John Doe", result)

    def test_getValueMemberIban_default_returnsCorrectIban(self):
        member = MemberFactory.build(iban="test_iban")
        payment = PaymentFactory.build(mandate_ref__member=member)

        result = PaymentColumnProvider.get_value_member_iban(payment, None, None)

        self.assertEqual("test_iban", result)

    def test_getValueAmount_default_returnsCorrectlyFormatedValue(self):
        payment = PaymentFactory.build(amount=Decimal("-12.348"))

        result = PaymentColumnProvider.get_value_amount(payment, None, None)

        self.assertEqual("-12.35", result)

    def test_getValuePurpose_paymentTypeIsSolidarityContribution_returnsPurposeWithCustomName(
        self,
    ):
        member = MemberFactory.build(last_name="Doe")
        payment = PaymentFactory.build(
            mandate_ref__member=member,
            type=MonthPaymentBuilderSolidarityContributions.PAYMENT_TYPE_SOLIDARITY_CONTRIBUTION,
        )

        result = PaymentColumnProvider.get_value_purpose(payment, None, None)

        self.assertEqual("Doe Solidarbeitrag", result)

    def test_getValuePurpose_paymentTypeIsNotSolidarityContribution_returnsPurposeWithPaymentType(
        self,
    ):
        member = MemberFactory.build(last_name="Doe")
        payment = PaymentFactory.build(
            mandate_ref__member=member,
            type="test_type",
        )

        result = PaymentColumnProvider.get_value_purpose(payment, None, None)

        self.assertEqual("Doe test_type", result)

    def test_getValueMandateRef_default_returnsCorrectRef(
        self,
    ):
        payment = PaymentFactory.build(mandate_ref__ref="test_ref")

        result = PaymentColumnProvider.get_value_mandate_ref(payment, None, None)

        self.assertEqual("test_ref", result)

    def test_getValueMandateDate_default_returnsCorrectlyFormattedRefDate(
        self,
    ):
        payment = PaymentFactory.build(
            mandate_ref__member__sepa_consent=datetime.date(year=1999, month=2, day=13),
        )

        result = PaymentColumnProvider.get_value_mandate_date(payment, None, None)

        self.assertEqual("13.02.1999", result)
