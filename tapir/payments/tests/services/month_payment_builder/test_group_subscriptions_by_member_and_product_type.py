from django.test import SimpleTestCase

from tapir.payments.services.month_payment_builder import MonthPaymentBuilder
from tapir.wirgarten.tests.factories import (
    ProductTypeFactory,
    MemberFactory,
    SubscriptionFactory,
)


class TestGroupSubscriptionsByMemberAndProductType(SimpleTestCase):
    def test_groupSubscriptionsByMemberAndProductType_default_groupsCorrectly(self):
        product_type_1 = ProductTypeFactory.build(pk="pt1")
        product_type_2 = ProductTypeFactory.build(pk="pt2")
        member_1 = MemberFactory.build(pk="m1")
        member_2 = MemberFactory.build(pk="m2")
        subscription_m1_pt1_a = SubscriptionFactory.build(
            member=member_1, product__type=product_type_1, mandate_ref__ref="test_ref_1"
        )
        subscription_m1_pt1_b = SubscriptionFactory.build(
            member=member_1, product__type=product_type_1, mandate_ref__ref="test_ref_1"
        )
        subscription_m1_pt2 = SubscriptionFactory.build(
            member=member_1, product__type=product_type_2, mandate_ref__ref="test_ref_1"
        )
        subscription_m2_pt1 = SubscriptionFactory.build(
            member=member_2, product__type=product_type_1, mandate_ref__ref="test_ref_2"
        )

        result = MonthPaymentBuilder.group_subscriptions_by_member_and_product_type(
            subscriptions=[
                subscription_m1_pt1_a,
                subscription_m1_pt1_b,
                subscription_m1_pt2,
                subscription_m2_pt1,
            ]
        )

        self.assertEqual(
            {
                member_1: {
                    product_type_1: {subscription_m1_pt1_a, subscription_m1_pt1_b},
                    product_type_2: {subscription_m1_pt2},
                },
                member_2: {product_type_1: {subscription_m2_pt1}},
            },
            result,
        )
