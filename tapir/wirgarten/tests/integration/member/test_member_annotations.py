import datetime

from django.utils import timezone

from tapir.wirgarten.models import Member
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.service.member import annotate_member_queryset_with_monthly_payment
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    SubscriptionFactory,
    ProductPriceFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestMemberAnnotations(TapirIntegrationTest):
    NOW = timezone.make_aware(datetime.datetime(year=2023, month=6, day=1))
    REFERENCE_DATE = datetime.date(year=2023, month=8, day=12)

    def setUp(self):
        super().setUp()
        ParameterDefinitions().import_definitions()
        mock_timezone(self, self.NOW)

    def test_annotateMemberQuerysetWithMonthlyPayment_memberHasNotSubscription_annotatesZero(
        self,
    ):
        MemberFactory.create()

        member = annotate_member_queryset_with_monthly_payment(
            Member.objects.all(), self.REFERENCE_DATE
        ).get()

        self.assertEqual(0, member.monthly_payment)

    def test_annotateMemberQuerysetWithMonthlyPayment_default_annotatesCorrectPayment(
        self,
    ):
        member = MemberFactory.create()

        # subscription cost: 110
        subscription_1 = SubscriptionFactory.create(
            member=member, quantity=1, solidarity_price=0.1
        )
        ProductPriceFactory.create(product=subscription_1.product, price=100)

        # subscription cost: 144
        subscription_2 = SubscriptionFactory.create(
            member=member, quantity=2, solidarity_price=0
        )
        ProductPriceFactory.create(product=subscription_2.product, price=72)

        member = annotate_member_queryset_with_monthly_payment(
            Member.objects.all(), self.REFERENCE_DATE
        ).get()

        self.assertEqual(254, member.monthly_payment)
