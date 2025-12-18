import datetime
from decimal import Decimal

from tapir.configuration.models import TapirParameter
from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.member_credit_creator import MemberCreditCreator
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.service.member import get_or_create_mandate_ref
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    GrowingPeriodFactory,
    PaymentFactory,
    SubscriptionFactory,
    ProductPriceFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestGetAmountToCredit(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(key=ParameterKeys.PAYMENT_START_DATE).update(
            value=datetime.date(year=2026, month=1, day=1)
        )

    def test_getAmountToCredit_default_returnsCorrectValue(self):
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
            mandate_ref=get_or_create_mandate_ref(member=member, cache={}),
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
            mandate_ref=get_or_create_mandate_ref(member=member, cache={}),
        )
        ProductPriceFactory.create(
            product=subscription.product, price=10, valid_from=growing_period.start_date
        )  # should give MonthPaymentBuilder.get_total_to_pay = 60 (6 month for 10 € each)

        result = MemberCreditCreator.get_amount_to_credit(
            member=member,
            cache={},
            reference_date=datetime.date(year=2027, month=2, day=15),
            product_type_id_or_soli=subscription.product.type.id,
        )

        self.assertEqual(
            Decimal(12.8).quantize(Decimal("0.01")), result.quantize(Decimal("0.01"))
        )
