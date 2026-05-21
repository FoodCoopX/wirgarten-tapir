import datetime

from tapir_mail.service.segment import resolve_segments

from tapir.subscriptions.apps import SubscriptionsConfig
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    ProductTypeFactory,
    MemberFactory,
    GrowingPeriodFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestMailSegments(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self) -> None:
        now = mock_timezone(
            test=self, now=datetime.datetime(year=2031, month=4, day=17)
        )
        self.growing_period = GrowingPeriodFactory.create(
            start_date=now.date().replace(month=1, day=1)
        )

    def test_subscriptionMailSegment_memberHasNoSubscription_memberNotIncluded(self):
        product_type = ProductTypeFactory.create()
        MemberFactory.create()

        result = resolve_segments(
            dynamic_segment_names_additive=[
                SubscriptionsConfig._build_segment_name_subscription_with_product_type(
                    product_type
                )
            ]
        )

        self.assertEqual([], result)

    def test_subscriptionMailSegment_memberHasSubscriptionForOtherProductType_memberNotIncluded(
        self,
    ):
        product_type_1 = ProductTypeFactory.create()
        product_type_2 = ProductTypeFactory.create()
        SubscriptionFactory.create(
            period=self.growing_period, product__type=product_type_2
        )

        result = resolve_segments(
            dynamic_segment_names_additive=[
                SubscriptionsConfig._build_segment_name_subscription_with_product_type(
                    product_type_1
                )
            ]
        )

        self.assertEqual([], result)

    def test_subscriptionMailSegment_memberHasPastSubscription_memberNotIncluded(self):
        product_type = ProductTypeFactory.create()
        past_growing_period = GrowingPeriodFactory.create(
            start_date=self.growing_period.start_date.replace(
                year=self.growing_period.start_date.year - 1
            )
        )
        SubscriptionFactory.create(
            period=past_growing_period, product__type=product_type
        )

        result = resolve_segments(
            dynamic_segment_names_additive=[
                SubscriptionsConfig._build_segment_name_subscription_with_product_type(
                    product_type
                )
            ]
        )

        self.assertEqual([], result)

    def test_subscriptionMailSegment_memberHasCurrentSubscription_memberIncluded(self):
        product_type = ProductTypeFactory.create()
        member = MemberFactory.create()
        SubscriptionFactory.create(
            member=member, period=self.growing_period, product__type=product_type
        )

        result = resolve_segments(
            dynamic_segment_names_additive=[
                SubscriptionsConfig._build_segment_name_subscription_with_product_type(
                    product_type
                )
            ]
        )

        self.assertEqual([member], result)

    def test_subscriptionMailSegment_memberHasFutureSubscription_memberIncluded(self):
        product_type = ProductTypeFactory.create()
        future_growing_period = GrowingPeriodFactory.create(
            start_date=self.growing_period.start_date.replace(
                year=self.growing_period.start_date.year + 1
            )
        )
        member = MemberFactory.create()
        SubscriptionFactory.create(
            member=member, period=future_growing_period, product__type=product_type
        )

        result = resolve_segments(
            dynamic_segment_names_additive=[
                SubscriptionsConfig._build_segment_name_subscription_with_product_type(
                    product_type
                )
            ]
        )

        self.assertEqual([member], result)
