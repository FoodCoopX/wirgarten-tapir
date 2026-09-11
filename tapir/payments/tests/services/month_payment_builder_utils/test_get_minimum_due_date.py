import datetime
from unittest.mock import Mock

from tapir.associations.models import AssociationMembership
from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.payments.services.month_payment_builder_utils import MonthPaymentBuilderUtils
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetMinimumDueDate(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_getMinimumDueDate_contractIsNotMembershipAndHasCreatedAt_returnsCreatedAt(
        self,
    ):
        created_at = datetime.datetime(year=2012, month=1, day=18)
        contract = SubscriptionFactory.build(
            created_at=created_at, start_date=datetime.date(year=2011, month=3, day=29)
        )

        result = MonthPaymentBuilderUtils.get_minimum_due_date(
            contract=contract, cache=Mock()
        )

        self.assertEqual(created_at.date(), result)

    def test_getMinimumDueDate_contractIsNotMembershipAndDoesntHaveCreatedAt_returnsStartDate(
        self,
    ):
        start_date = datetime.date(year=2011, month=3, day=29)
        contract = SubscriptionFactory.build(created_at=None, start_date=start_date)

        result = MonthPaymentBuilderUtils.get_minimum_due_date(
            contract=contract, cache=Mock()
        )

        self.assertEqual(start_date, result)

    def test_getMinimumDate_contractIsMembershipAndAllSubscriptionsOnTrial_returnMonthAfterMembershipStart(
        self,
    ):
        membership = AssociationMembershipFactory.create(
            start_date=datetime.date(year=2011, month=3, day=29)
        )
        SubscriptionFactory.create(
            member=membership.member,
            start_date=datetime.date(year=2011, month=3, day=1),
        )
        self._set_parameter(key=ParameterKeys.TRIAL_PERIOD_ENABLED, value=True)
        self._set_parameter(key=ParameterKeys.TRIAL_PERIOD_DURATION, value=8)

        result = MonthPaymentBuilderUtils.get_minimum_due_date(
            contract=membership, cache={}
        )

        self.assertEqual(datetime.date(year=2011, month=4, day=1), result)

    def test_getMinimumDate_contractIsMembershipAndAOneSubscriptionNotOnTrial_returnMembershipCreationDate(
        self,
    ):
        membership = AssociationMembershipFactory.create(
            start_date=datetime.date(year=2011, month=3, day=29)
        )
        AssociationMembership.objects.filter(id=membership.id).update(
            created_at=datetime.datetime(
                year=2011, month=2, day=14, hour=12, tzinfo=datetime.timezone.utc
            )
        )
        membership.refresh_from_db()
        SubscriptionFactory.create(
            member=membership.member,
            start_date=datetime.date(year=2011, month=3, day=1),
        )
        SubscriptionFactory.create(
            member=membership.member,
            start_date=datetime.date(year=2011, month=1, day=1),
        )
        self._set_parameter(key=ParameterKeys.TRIAL_PERIOD_ENABLED, value=True)
        self._set_parameter(key=ParameterKeys.TRIAL_PERIOD_DURATION, value=8)

        result = MonthPaymentBuilderUtils.get_minimum_due_date(
            contract=membership, cache={}
        )

        self.assertEqual(datetime.date(year=2011, month=2, day=14), result)

    def test_getMinimumDate_contractIsMembershipAndTrialDisabled_returnMembershipCreationDate(
        self,
    ):
        membership = AssociationMembershipFactory.create(
            start_date=datetime.date(year=2011, month=3, day=29)
        )
        AssociationMembership.objects.filter(id=membership.id).update(
            created_at=datetime.datetime(
                year=2011, month=2, day=14, hour=12, tzinfo=datetime.timezone.utc
            )
        )
        membership.refresh_from_db()
        SubscriptionFactory.create(
            member=membership.member,
            start_date=datetime.date(year=2011, month=3, day=1),
        )
        self._set_parameter(key=ParameterKeys.TRIAL_PERIOD_ENABLED, value=False)
        self._set_parameter(key=ParameterKeys.TRIAL_PERIOD_DURATION, value=8)

        result = MonthPaymentBuilderUtils.get_minimum_due_date(
            contract=membership, cache={}
        )

        self.assertEqual(datetime.date(year=2011, month=2, day=14), result)
