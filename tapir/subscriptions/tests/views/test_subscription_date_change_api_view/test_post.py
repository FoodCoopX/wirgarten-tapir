import datetime

from django.urls import reverse

from tapir.configuration.models import TapirParameter
from tapir.payments.models import (
    MemberPaymentRhythm,
    MemberCredit,
    MemberCreditCreatedLogEntry,
)
from tapir.payments.services.mandate_reference_provider import MandateReferenceProvider
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    SubscriptionFactory,
    MemberFactory,
    ProductPriceFactory,
    PaymentFactory,
    GrowingPeriodFactory,
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
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

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

    def test_post_endDateChanged_deleteFutureSubscription(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

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

    def test_post_newEndDateIsBeforeEndOfPaymentInterval_createsAMemberCredit(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        mock_timezone(self, now=datetime.datetime(year=2025, month=7, day=12))

        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2025, month=1, day=1),
        )
        subscription = SubscriptionFactory.create(
            member=member,
            quantity=1,
            period=growing_period,
            product__type__delivery_cycle=WEEKLY[0],
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
            mandate_ref=MandateReferenceProvider.get_or_create_mandate_reference(
                member=member, cache={}
            ),
            amount=120,
            type=subscription.product.type.name,
            subscription_payment_range_start=datetime.date(year=2025, month=1, day=1),
            subscription_payment_range_end=datetime.date(year=2025, month=12, day=31),
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
