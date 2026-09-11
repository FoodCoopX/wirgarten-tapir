import datetime
from decimal import Decimal

from django.urls import reverse

from tapir.configuration.models import TapirParameter
from tapir.payments.models import (
    MemberPaymentRhythm,
    MemberCredit,
    MemberCreditCreatedLogEntry,
)
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.payments.services.month_payment_builder_solidarity_contributions import (
    MonthPaymentBuilderSolidarityContributions,
)
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.solidarity_contribution.tests.factories import SolidarityContributionFactory
from tapir.subscriptions.models import SubscriptionChangedLogEntry
from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.models import Subscription, GrowingPeriod, Member, MandateReference
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    SubscriptionFactory,
    MemberFactory,
    ProductPriceFactory,
    PaymentFactory,
    GrowingPeriodFactory,
    MandateReferenceFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestPost(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(key=ParameterKeys.PAYMENT_START_DATE).update(
            value=datetime.date(year=2025, month=1, day=1)
        )

    def test_post_normalMemberTriesToChangeDates_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        subscription = SubscriptionFactory.create(
            period__start_date=datetime.date(year=2025, month=1, day=1)
        )

        response = self.client.post(
            reverse("subscriptions:dates_change"),
            data={
                "subscription_id": subscription.id,
                "start_date_is_on_period_start": False,
                "end_date_is_on_period_end": False,
                "start_week": 1,
                "end_week": 50,
            },
        )

        self.assertStatusCode(response, 403)

        subscription.refresh_from_db()
        self.assertEqual(
            datetime.date(year=2025, month=12, day=31), subscription.end_date
        )

    def test_post_validationFails_dontChangeDatesAndReturnErrorMessage(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        subscription = SubscriptionFactory.create(
            period__start_date=datetime.date(year=2025, month=1, day=1)
        )

        response = self.client.post(
            reverse("subscriptions:dates_change"),
            data={
                "subscription_id": subscription.id,
                "start_date_is_on_period_start": False,
                "end_date_is_on_period_end": False,
                "start_week": 20,
                "end_week": 19,
            },
        )

        self.assertStatusCode(response, 200)
        self.assertEqual(
            {
                "error": "Das Start-Datum (12.05.2025) muss vor dem End-Datum (11.05.2025) liegen.",
                "order_confirmed": False,
            },
            response.json(),
        )

        subscription.refresh_from_db()
        self.assertEqual(
            datetime.date(year=2025, month=12, day=31), subscription.end_date
        )

    def test_post_endDateNotChanged_dontDeleteFutureSubscription(self):
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)

        subscription = SubscriptionFactory.create(
            period__start_date=datetime.date(year=2025, month=1, day=1),
        )
        SubscriptionFactory.create(
            period__start_date=datetime.date(year=2026, month=1, day=1),
            product=subscription.product,
            member=subscription.member,
        )
        ProductPriceFactory.create(
            product=subscription.product,
            valid_from=datetime.date(year=2025, month=1, day=1),
        )

        response = self.client.post(
            reverse("subscriptions:dates_change"),
            data={
                "subscription_id": subscription.id,
                "start_date_is_on_period_start": False,
                "end_date_is_on_period_end": True,
                "start_week": 10,
                "end_week": 10,
            },
        )

        self.assertStatusCode(response, 200)
        self.assertEqual(
            {
                "error": None,
                "order_confirmed": True,
            },
            response.json(),
        )

        subscription.refresh_from_db()
        self.assertEqual(
            datetime.date(year=2025, month=12, day=31), subscription.end_date
        )
        self.assertEqual(
            datetime.date(year=2025, month=3, day=3), subscription.start_date
        )
        self.assertEqual(2, Subscription.objects.count())

        self.assertEqual(1, SubscriptionChangedLogEntry.objects.count())
        log_entry = SubscriptionChangedLogEntry.objects.get()
        self.assertEqual(admin.email, log_entry.actor.email)
        self.assertEqual(subscription.member.email, log_entry.user.email)
        self.assertEqual("2025-01-01", log_entry.old_values["start_date"])
        self.assertEqual("2025-03-03", log_entry.new_values["start_date"])
        self.assertNotIn("end_date", log_entry.old_values)
        self.assertNotIn("end_date", log_entry.new_values)

    def test_post_endDateChanged_deleteFutureSubscription(self):
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)

        subscription = SubscriptionFactory.create(
            period__start_date=datetime.date(year=2025, month=1, day=1),
        )
        SubscriptionFactory.create(
            period__start_date=datetime.date(year=2026, month=1, day=1),
            product=subscription.product,
            member=subscription.member,
        )
        ProductPriceFactory.create(
            product=subscription.product,
            valid_from=datetime.date(year=2025, month=1, day=1),
        )
        created_at_before = subscription.created_at

        response = self.client.post(
            reverse("subscriptions:dates_change"),
            data={
                "subscription_id": subscription.id,
                "start_date_is_on_period_start": False,
                "end_date_is_on_period_end": False,
                "start_week": 1,
                "end_week": 20,
            },
        )

        self.assertStatusCode(response, 200)
        self.assertEqual(
            {
                "error": None,
                "order_confirmed": True,
            },
            response.json(),
        )

        subscription.refresh_from_db()
        self.assertEqual(
            datetime.date(year=2025, month=5, day=18), subscription.end_date
        )
        self.assertEqual(1, Subscription.objects.count())
        self.assertEqual(
            created_at_before,
            subscription.created_at,
            "Regression test for infra#56, "
            "we used to delete and re-create the subscription on date changes, "
            "causing the creating date to be updated, leading to payment problems.",
        )

        self.assertEqual(1, SubscriptionChangedLogEntry.objects.count())
        log_entry = SubscriptionChangedLogEntry.objects.get()
        self.assertEqual(admin.email, log_entry.actor.email)
        self.assertEqual(subscription.member.email, log_entry.user.email)
        self.assertEqual("2025-12-31", log_entry.old_values["end_date"])
        self.assertEqual("2025-05-18", log_entry.new_values["end_date"])
        self.assertNotIn("start_date", log_entry.old_values)
        self.assertNotIn("start_date", log_entry.new_values)

    def test_post_newEndDateIsBeforeEndOfPaymentInterval_createsAMemberCredit(self):
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)

        mock_timezone(self, now=datetime.datetime(year=2025, month=7, day=12))

        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2025, month=1, day=1),
        )
        member = MemberFactory.create()
        subscription = self._create_subscription_and_payment(
            member=member,
            growing_period=growing_period,
            mandate_ref=MandateReferenceFactory.create(member=member),
        )

        response = self.client.post(
            reverse("subscriptions:dates_change"),
            data={
                "subscription_id": subscription.id,
                "start_date_is_on_period_start": True,
                "end_date_is_on_period_end": False,
                "start_week": 1,
                "end_week": 48,  # This ends the subscription on the last day of November
            },
        )

        self.assertStatusCode(response, 200)
        self.assertEqual(
            {
                "error": None,
                "order_confirmed": True,
            },
            response.json(),
        )

        subscription.refresh_from_db()
        self.assertEqual(
            datetime.date(year=2025, month=11, day=30), subscription.end_date
        )

        self.assertEqual(1, MemberCredit.objects.count())
        member_credit = MemberCredit.objects.get()
        self.assertEqual(10, member_credit.amount)
        self.assertEqual(
            datetime.date(year=2025, month=7, day=31), member_credit.due_date
        )
        self.assertEqual(member, member_credit.member)

        self.assertEqual(1, MemberCreditCreatedLogEntry.objects.count())

    def test_post_solidarityContributionMustBeUpdatedAndContributionExists_updatesCurrentContributionAndDeleteFutureContribution(
        self,
    ):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        subscription = SubscriptionFactory.create(
            period__start_date=datetime.date(year=2025, month=1, day=1),
        )
        current_contribution = SolidarityContributionFactory.create(
            start_date=subscription.start_date, member=subscription.member
        )
        future_contribution = SolidarityContributionFactory.create(
            start_date=subscription.end_date + datetime.timedelta(days=1),
            member=subscription.member,
        )
        contribution_of_other_member = SolidarityContributionFactory.create(
            start_date=subscription.end_date + datetime.timedelta(days=1),
        )

        response = self.client.post(
            reverse("subscriptions:dates_change"),
            data={
                "subscription_id": subscription.id,
                "start_date_is_on_period_start": False,
                "end_date_is_on_period_end": False,
                "start_week": 1,
                "end_week": 20,
                "update_end_date_of_other_contracts": True,
            },
        )

        self.assertStatusCode(response, 200)
        self.assert_order_confirmed(response.json())

        subscription.refresh_from_db()
        self.assertEqual(
            datetime.date(year=2025, month=5, day=18), subscription.end_date
        )

        self.assertEqual(2, SolidarityContribution.objects.count())
        current_contribution.refresh_from_db()
        self.assertEqual(subscription.end_date, current_contribution.end_date)
        self.assertEqual(
            contribution_of_other_member.end_date,
            SolidarityContribution.objects.get(
                id=contribution_of_other_member.id
            ).end_date,
            "This one should not have been changed",
        )
        self.assertFalse(
            SolidarityContribution.objects.filter(id=future_contribution.id).exists()
        )
        self.assertEqual(1, SubscriptionChangedLogEntry.objects.count())

    def test_post_solidarityContributionUpdatedAndContributionWasAlreadyPaid_createCredit(
        self,
    ):
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)

        member = MemberFactory.create()
        mandate_ref = MandateReferenceFactory.create(member=member)
        subscription = SubscriptionFactory.create(
            period__start_date=datetime.date(year=2025, month=1, day=1),
            mandate_ref=mandate_ref,
            member=member,
        )
        current_contribution = SolidarityContributionFactory.create(
            start_date=subscription.start_date, member=subscription.member, amount=10
        )
        MemberPaymentRhythmService.assign_payment_rhythm_to_member(
            member=member,
            actor=admin,
            rhythm=MemberPaymentRhythm.Rhythm.YEARLY,
            valid_from=subscription.start_date,
            cache={},
        )
        PaymentFactory.create(
            mandate_ref=mandate_ref,
            due_date=subscription.start_date,
            amount=120,
            type=MonthPaymentBuilderSolidarityContributions.PAYMENT_TYPE_SOLIDARITY_CONTRIBUTION,
            subscription_payment_range_start=subscription.start_date,
            subscription_payment_range_end=subscription.end_date,
        )

        response = self.client.post(
            reverse("subscriptions:dates_change"),
            data={
                "subscription_id": subscription.id,
                "start_date_is_on_period_start": False,
                "end_date_is_on_period_end": False,
                "start_week": 1,
                "end_week": 20,
                "update_end_date_of_other_contracts": True,
            },
        )

        self.assertStatusCode(response, 200)
        self.assert_order_confirmed(response.json())

        subscription.refresh_from_db()
        self.assertEqual(
            datetime.date(year=2025, month=5, day=18), subscription.end_date
        )

        self.assertEqual(1, SolidarityContribution.objects.count())
        current_contribution.refresh_from_db()
        self.assertEqual(subscription.end_date, current_contribution.end_date)

        self.assertEqual(1, MemberCredit.objects.count())
        credit = MemberCredit.objects.get()
        self.assertEqual(subscription.member, credit.member)
        self.assertEqual(Decimal("74.19"), credit.amount)

    def test_post_endDateOfOtherSubscriptionMustAlsoBeSet_updateOtherSubscriptionAndCreateLogEntryAndCreateMemberCredit(
        self,
    ):
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)

        mock_timezone(self, now=datetime.datetime(year=2025, month=7, day=12))

        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2025, month=1, day=1),
        )
        member = MemberFactory.create()
        mandate_ref = MandateReferenceFactory.create(member=member)
        main_subscription = self._create_subscription_and_payment(
            member=member, growing_period=growing_period, mandate_ref=mandate_ref
        )
        side_subscription = self._create_subscription_and_payment(
            member=member, growing_period=growing_period, mandate_ref=mandate_ref
        )

        response = self.client.post(
            reverse("subscriptions:dates_change"),
            data={
                "subscription_id": main_subscription.id,
                "start_date_is_on_period_start": True,
                "end_date_is_on_period_end": False,
                "start_week": 1,
                "end_week": 48,  # This ends the subscription on the last day of November
                "update_end_date_of_other_contracts": True,
            },
        )

        self.assertStatusCode(response, 200)
        self.assertEqual(
            {
                "error": None,
                "order_confirmed": True,
            },
            response.json(),
        )

        side_subscription.refresh_from_db()
        self.assertEqual(
            datetime.date(year=2025, month=11, day=30), side_subscription.end_date
        )

        self.assertEqual(2, MemberCredit.objects.count())
        for member_credit in MemberCredit.objects.all():
            self.assertEqual(10, member_credit.amount)
            self.assertEqual(
                datetime.date(year=2025, month=7, day=31), member_credit.due_date
            )
            self.assertEqual(member, member_credit.member)

        self.assertEqual(2, MemberCreditCreatedLogEntry.objects.count())

        self.assertEqual(2, SubscriptionChangedLogEntry.objects.count())
        log_entry = SubscriptionChangedLogEntry.objects.order_by("created_date").last()
        self.assertEqual(admin.email, log_entry.actor.email)
        self.assertEqual(side_subscription.member.email, log_entry.user.email)
        self.assertEqual("2025-12-31", log_entry.old_values["end_date"])
        self.assertEqual("2025-11-30", log_entry.new_values["end_date"])
        self.assertNotIn("start_date", log_entry.old_values)
        self.assertNotIn("start_date", log_entry.new_values)

    @classmethod
    def _create_subscription_and_payment(
        cls,
        member: Member,
        growing_period: GrowingPeriod,
        mandate_ref: MandateReference,
    ) -> Subscription:
        subscription = SubscriptionFactory.create(
            member=member,
            quantity=1,
            period=growing_period,
            product__type__delivery_cycle=WEEKLY[0],
            mandate_ref=mandate_ref,
        )
        ProductPriceFactory.create(
            product=subscription.product,
            valid_from=datetime.date(year=2025, month=1, day=1),
            price=10,
        )
        MemberPaymentRhythmService.assign_payment_rhythm_to_member(
            member=member,
            rhythm=MemberPaymentRhythm.Rhythm.YEARLY,
            valid_from=datetime.date(year=2025, month=1, day=1),
            cache={},
            actor=member,
        )
        PaymentFactory.create(
            due_date=datetime.date(year=2025, month=1, day=1),
            mandate_ref=mandate_ref,
            amount=120,
            type=subscription.product.type.name,
            subscription_payment_range_start=datetime.date(year=2025, month=1, day=1),
            subscription_payment_range_end=datetime.date(year=2025, month=12, day=31),
        )
        return subscription
