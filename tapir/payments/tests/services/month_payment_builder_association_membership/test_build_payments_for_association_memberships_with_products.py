import datetime
from decimal import Decimal

from tapir.associations.tests.factories import (
    AssociationMembershipFactory,
    AssociationMembershipTypeFactory,
    AssociationMembershipTypePriceFactory,
)
from tapir.payments.services.month_payment_builder_association_membership import (
    MonthPaymentBuilderAssociationMembership,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestBuildPaymentsForAssociationMembershipsWithProducts(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        mock_timezone(self, datetime.datetime(year=2026, month=1, day=15))
        self._set_parameter(
            key=ParameterKeys.PAYMENT_START_DATE,
            value=datetime.date(year=2026, month=1, day=1),
        )
        self._set_parameter(
            key=ParameterKeys.ASSOCIATIONS_MEMBERSHIP_FEE_WAIVED_WITH_PRODUCTS,
            value=True,
        )
        self.growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=12, day=31),
        )
        self.membership_type = AssociationMembershipTypeFactory.create()
        AssociationMembershipTypePriceFactory.create(
            type=self.membership_type,
            valid_from=datetime.date(year=2026, month=1, day=1),
            price=Decimal("10.00"),
        )

    def create_membership(self, member):
        return AssociationMembershipFactory.create(
            member=member,
            type=self.membership_type,
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=None,
        )

    def create_product_subscription(self, member):
        return SubscriptionFactory.create(
            member=member,
            period=self.growing_period,
            start_date=self.growing_period.start_date,
            end_date=self.growing_period.end_date,
        )

    def build(self):
        return MonthPaymentBuilderAssociationMembership.build_payments_for_association_memberships(
            current_month=datetime.date(year=2026, month=1, day=1),
            cache={},
            generated_payments=set(),
        )

    def test_memberWithProductContract_getsNoMembershipPayment(self):
        member = MemberFactory.create()
        self.create_membership(member)
        self.create_product_subscription(member)

        payments = self.build()

        self.assertEqual([], payments)

    def test_memberWithoutProductContract_getsMembershipPayment(self):
        member = MemberFactory.create()
        self.create_membership(member)

        payments = self.build()

        self.assertEqual(1, len(payments))
        self.assertEqual(
            MonthPaymentBuilderAssociationMembership.PAYMENT_TYPE_ASSOCIATION_MEMBERSHIP,
            payments[0].type,
        )
        self.assertEqual(Decimal("10.00"), payments[0].amount)

    def test_parameterOff_memberWithProductContract_getsMembershipPayment(self):
        self._set_parameter(
            key=ParameterKeys.ASSOCIATIONS_MEMBERSHIP_FEE_WAIVED_WITH_PRODUCTS,
            value=False,
        )
        member = MemberFactory.create()
        self.create_membership(member)
        self.create_product_subscription(member)

        payments = self.build()

        self.assertEqual(1, len(payments))
        self.assertEqual(Decimal("10.00"), payments[0].amount)
