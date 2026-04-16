import datetime
from decimal import Decimal

from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.payments.services.monthly_sales_segment_provider import (
    MonthlySalesSegmentProvider,
)
from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    SubscriptionFactory,
    GrowingPeriodFactory,
    ProductPriceFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMonthlySalesSegmentProvider(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_getListMonthlySales_default_returnsCorrectData(self):
        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2025, month=1, day=1)
        )
        subscription_1 = (
            SubscriptionFactory.create(  # this one should cover the full month
                product__type__delivery_cycle=WEEKLY[0],
                period=growing_period,
                product__type__name="test type name",
                quantity=2,
            )
        )
        MemberPaymentRhythmService.assign_payment_rhythm_to_member(
            member=subscription_1.member,
            valid_from=growing_period.start_date,
            actor=None,
            rhythm=MemberPaymentRhythm.Rhythm.YEARLY,
            cache={},
        )  # The payment rhythm should not affect the result

        subscription_2 = (  # This one should have only 2 deliveries in the given month
            SubscriptionFactory.create(  # this one should cover the full month
                product__type=subscription_1.product.type,
                period=growing_period,
                start_date=datetime.date(year=2025, month=4, day=21),
                quantity=1,
            )
        )

        ProductPriceFactory.create(
            product=subscription_1.product,
            valid_from=growing_period.start_date,
            price=10,
        )
        ProductPriceFactory.create(
            product=subscription_2.product,
            valid_from=growing_period.start_date,
            price=15,
        )

        result = MonthlySalesSegmentProvider.get_list_monthly_sales(
            reference_datetime=datetime.datetime(year=2025, month=4, day=15, hour=12)
        )

        data_for_subscriptions = result[0]
        self.assertEqual("test type name", data_for_subscriptions.contract_type_name)
        self.assertEqual(
            Decimal("26.92"),
            data_for_subscriptions.sales.quantize(Decimal("0.01")),
            "The total monthly price should be 2x10 for subscription 1 (1 full month of a subscription with quantity 2) plus 6.92 for subscription 2 (partial month with 2 deliveries)",
        )
