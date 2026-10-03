import datetime
from decimal import Decimal

from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.solidarity_contribution.tests.factories import SolidarityContributionFactory
from tapir.subscriptions.services.subscription_cancellation_manager import (
    SubscriptionCancellationManager,
)
from tapir.wirgarten.models import Member, Product
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestNegativeSolidarityContributionMustBeCancelled(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self) -> None:
        super().setUp()
        mock_timezone(self, datetime.datetime(year=2023, month=3, day=15))

    def test_negativeSolidarityContributionMustBeCancelled_allSubscriptionsCancelledAndContributionIsNegative_returnsTrue(
        self,
    ):
        member = MemberFactory.create()
        products = self._create_subscribed_products(member=member, size=2)
        self._create_solidarity_contribution(member=member, amount=Decimal("-5"))

        result = self._must_be_cancelled(
            member=member,
            products_selected_for_cancellation=products,
            cancel_association_membership=False,
        )

        self.assertTrue(result)

    def test_negativeSolidarityContributionMustBeCancelled_contributionIsPositive_returnsFalse(
        self,
    ):
        member = MemberFactory.create()
        products = self._create_subscribed_products(member=member, size=2)
        self._create_solidarity_contribution(member=member, amount=Decimal("5"))

        result = self._must_be_cancelled(
            member=member,
            products_selected_for_cancellation=products,
            cancel_association_membership=False,
        )

        self.assertFalse(result)

    def test_negativeSolidarityContributionMustBeCancelled_noContribution_returnsFalse(
        self,
    ):
        member = MemberFactory.create()
        products = self._create_subscribed_products(member=member, size=2)

        result = self._must_be_cancelled(
            member=member,
            products_selected_for_cancellation=products,
            cancel_association_membership=False,
        )

        self.assertFalse(result)

    def test_negativeSolidarityContributionMustBeCancelled_notAllSubscriptionsCancelled_returnsFalse(
        self,
    ):
        member = MemberFactory.create()
        products = self._create_subscribed_products(member=member, size=2)
        self._create_solidarity_contribution(member=member, amount=Decimal("-5"))
        selected_product = products.pop()

        result = self._must_be_cancelled(
            member=member,
            products_selected_for_cancellation={selected_product},
            cancel_association_membership=False,
        )

        self.assertFalse(result)

    def test_negativeSolidarityContributionMustBeCancelled_nothingSelected_returnsFalse(
        self,
    ):
        member = MemberFactory.create()
        self._create_solidarity_contribution(member=member, amount=Decimal("-5"))

        result = self._must_be_cancelled(
            member=member,
            products_selected_for_cancellation=set(),
            cancel_association_membership=False,
        )

        self.assertFalse(result)

    def test_negativeSolidarityContributionMustBeCancelled_associationMembershipNotCancelled_returnsFalse(
        self,
    ):
        member = MemberFactory.create()
        products = self._create_subscribed_products(member=member, size=2)
        self._create_cancellable_association_membership(member=member)
        self._create_solidarity_contribution(member=member, amount=Decimal("-5"))

        result = self._must_be_cancelled(
            member=member,
            products_selected_for_cancellation=products,
            cancel_association_membership=False,
        )

        self.assertFalse(result)

    def test_negativeSolidarityContributionMustBeCancelled_allSubscriptionsAndAssociationMembershipCancelled_returnsTrue(
        self,
    ):
        member = MemberFactory.create()
        products = self._create_subscribed_products(member=member, size=2)
        self._create_cancellable_association_membership(member=member)
        self._create_solidarity_contribution(member=member, amount=Decimal("-5"))

        result = self._must_be_cancelled(
            member=member,
            products_selected_for_cancellation=products,
            cancel_association_membership=True,
        )

        self.assertTrue(result)

    def test_negativeSolidarityContributionMustBeCancelled_onlyAssociationMembershipCancelled_returnsTrue(
        self,
    ):
        member = MemberFactory.create()
        self._create_cancellable_association_membership(member=member)
        self._create_solidarity_contribution(member=member, amount=Decimal("-5"))

        result = self._must_be_cancelled(
            member=member,
            products_selected_for_cancellation=set(),
            cancel_association_membership=True,
        )

        self.assertTrue(result)

    def _must_be_cancelled(
        self,
        member: Member,
        products_selected_for_cancellation: set[Product],
        cancel_association_membership: bool,
    ) -> bool:
        return SubscriptionCancellationManager.negative_solidarity_contribution_must_be_cancelled(
            member=member,
            products_selected_for_cancellation=products_selected_for_cancellation,
            cancel_association_membership=cancel_association_membership,
            cache={},
        )

    def _create_subscribed_products(self, member: Member, size: int) -> set[Product]:
        period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2023, month=1, day=1),
            end_date=datetime.date(year=2023, month=12, day=31),
        )
        subscriptions = SubscriptionFactory.create_batch(
            size=size, member=member, period=period
        )
        return {subscription.product for subscription in subscriptions}

    def _create_solidarity_contribution(self, member: Member, amount: Decimal):
        return SolidarityContributionFactory.create(
            member=member,
            start_date=datetime.date(year=2023, month=1, day=1),
            end_date=datetime.date(year=2023, month=12, day=31),
            amount=amount,
        )

    def _create_cancellable_association_membership(self, member: Member):
        self._set_parameter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS,
            value=LEGAL_STATUS_ASSOCIATION,
        )
        return AssociationMembershipFactory.create(
            member=member,
            start_date=datetime.date(year=2023, month=1, day=1),
        )
