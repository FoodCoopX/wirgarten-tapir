import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock

from tapir.configuration.models import TapirParameter
from tapir.utils.dataclasses import CalculationPart
from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.mandate_reference_provider import MandateReferenceProvider
from tapir.payments.services.member_credit_creator import MemberCreditCreator
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.payments.services.month_payment_builder_utils import MonthPaymentBuilderUtils
from tapir.payments.services.month_payment_builder_solidarity_contributions import (
    MonthPaymentBuilderSolidarityContributions,
)
from tapir.solidarity_contribution.tests.factories import SolidarityContributionFactory
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    GrowingPeriodFactory,
    PaymentFactory,
    SubscriptionFactory,
    ProductPriceFactory,
    ProductTypeFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestGetCreditCalculation(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(key=ParameterKeys.PAYMENT_START_DATE).update(
            value=datetime.date(year=2026, month=1, day=1)
        )

    def test_getCreditCalculation_parameterProductId_returnsCorrectValue(self):
        now = mock_timezone(self, datetime.datetime(year=2027, month=8, day=19))
        member = MemberFactory.create()
        growing_period = GrowingPeriodFactory.create(
            start_date=now.date().replace(month=1, day=1),
            end_date=now.date().replace(month=12, day=31),
        )
        MemberPaymentRhythmService.assign_payment_rhythm_to_member(
            member=member,
            actor=member,
            rhythm=MemberPaymentRhythm.Rhythm.SEMIANNUALLY,
            valid_from=datetime.date.today(),
            cache={},
        )

        PaymentFactory.create(
            due_date=datetime.date(year=2027, month=2, day=15),
            mandate_ref=MandateReferenceProvider.get_or_create_mandate_reference(
                member=member, cache={}
            ),
            amount=72.8,
            type="test_product_type",
            subscription_payment_range_start=datetime.date(year=2027, month=1, day=1),
            subscription_payment_range_end=datetime.date(year=2027, month=6, day=30),
        )  # should give MonthPaymentBuilder.get_already_paid_amount = 72.8

        subscription = SubscriptionFactory.create(
            member=member,
            period=growing_period,
            quantity=1,
            product__type__name="test_product_type",
            mandate_ref=MandateReferenceProvider.get_or_create_mandate_reference(
                member=member, cache={}
            ),
        )
        ProductPriceFactory.create(
            product=subscription.product, price=10, valid_from=growing_period.start_date
        )  # should give MonthPaymentBuilder.get_total_to_pay = 60 (6 month for 10 € each)

        result = MemberCreditCreator.get_credit_calculation(
            member=member,
            cache={},
            reference_date=datetime.date(year=2027, month=2, day=15),
            product_type_id_or_soli=subscription.product.type.id,
        )

        self.assertEqual(
            Decimal(12.8).quantize(Decimal("0.01")),
            result.amount.quantize(Decimal("0.01")),
        )

    def test_getCreditCalculation_parameterSoli_returnsCorrectValue(self):
        now = mock_timezone(self, datetime.datetime(year=2027, month=8, day=19))
        member = MemberFactory.create()
        growing_period = GrowingPeriodFactory.create(
            start_date=now.date().replace(month=1, day=1),
            end_date=now.date().replace(month=12, day=31),
        )
        MemberPaymentRhythmService.assign_payment_rhythm_to_member(
            member=member,
            actor=member,
            rhythm=MemberPaymentRhythm.Rhythm.SEMIANNUALLY,
            valid_from=datetime.date.today(),
            cache={},
        )

        PaymentFactory.create(
            due_date=datetime.date(year=2027, month=2, day=15),
            mandate_ref=MandateReferenceProvider.get_or_create_mandate_reference(
                member=member, cache={}
            ),
            amount=72.8,
            type=MonthPaymentBuilderSolidarityContributions.PAYMENT_TYPE_SOLIDARITY_CONTRIBUTION,
            subscription_payment_range_start=datetime.date(year=2027, month=1, day=1),
            subscription_payment_range_end=datetime.date(year=2027, month=6, day=30),
        )  # should give MonthPaymentBuilder.get_already_paid_amount = 72.8

        SolidarityContributionFactory.create(
            member=member, start_date=growing_period.start_date, amount=10
        )

        result = MemberCreditCreator.get_credit_calculation(
            member=member,
            cache={},
            reference_date=datetime.date(year=2027, month=2, day=15),
            product_type_id_or_soli=MonthPaymentBuilderSolidarityContributions.PAYMENT_TYPE_SOLIDARITY_CONTRIBUTION,
        )

        self.assertEqual(
            Decimal(12.8).quantize(Decimal("0.01")),
            result.amount.quantize(Decimal("0.01")),
        )
        self.assertEqual(
            "Berechnung der Gutschrift:\n"
            "Januar 2027, Solidarbeitrag: 10,00 € monatlich (voller Monat)\n"
            "Februar 2027, Solidarbeitrag: 10,00 € monatlich (voller Monat)\n"
            "März 2027, Solidarbeitrag: 10,00 € monatlich (voller Monat)\n"
            "April 2027, Solidarbeitrag: 10,00 € monatlich (voller Monat)\n"
            "Mai 2027, Solidarbeitrag: 10,00 € monatlich (voller Monat)\n"
            "Juni 2027, Solidarbeitrag: 10,00 € monatlich (voller Monat)\n"
            "Summe: 60,00 €\n"
            "Bereits bezahlt: 72,80 €\n"
            "Gutschrift: 12,80 €",
            result.explanation,
        )

    @patch.object(
        MonthPaymentBuilderUtils,
        "get_already_paid_amount",
        autospec=True,
        return_value=Decimal("9.67"),
    )
    @patch.object(
        MemberCreditCreator, "get_calculation_parts_subscriptions", autospec=True
    )
    def test_getCreditCalculation_differenceBelowOneCent_returnsZero(
        self,
        mock_get_calculation_parts_subscriptions: MagicMock,
        _: MagicMock,
    ):
        mock_timezone(self, datetime.datetime(year=2027, month=8, day=19))
        GrowingPeriodFactory.create(
            start_date=datetime.date(year=2027, month=1, day=1),
            end_date=datetime.date(year=2027, month=12, day=31),
        )
        # 29 € × 1 ÷ 3 delivery dates = 9.6666…, paid as 9.67
        mock_get_calculation_parts_subscriptions.return_value = [
            CalculationPart(explanation="part", value=Decimal(29) / 3)
        ]

        result = MemberCreditCreator.get_credit_calculation(
            member=MemberFactory.create(),
            cache={},
            reference_date=datetime.date(year=2027, month=2, day=15),
            product_type_id_or_soli=ProductTypeFactory.create().id,
        )

        self.assertEqual(Decimal("0.00"), result.amount)
