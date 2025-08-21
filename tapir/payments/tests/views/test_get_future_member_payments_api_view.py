import datetime

from django.urls import reverse

from tapir.configuration.models import TapirParameter
from tapir.payments.models import MemberPaymentRhythm
from tapir.utils.shortcuts import get_last_day_of_month
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    SubscriptionFactory,
    GrowingPeriodFactory,
    ProductPriceFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestGetFutureMemberPaymentsAPIView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_normalMemberGetsOwnPayments_returns200(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        url = reverse("payments:member_future_payments")
        url = f"{url}?member_id={member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, 200)

    def test_get_normalMemberGetsPaymentsOfOtherMember_returns403(self):
        logged_in_member = MemberFactory.create(is_superuser=False)
        other_member = MemberFactory.create()
        self.client.force_login(logged_in_member)

        url = reverse("payments:member_future_payments")
        url = f"{url}?member_id={other_member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, 403)

    def test_get_adminUserGetsPaymentsOfOtherMember_returns200(self):
        logged_in_member = MemberFactory.create(is_superuser=True)
        other_member = MemberFactory.create()
        self.client.force_login(logged_in_member)

        url = reverse("payments:member_future_payments")
        url = f"{url}?member_id={other_member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, 200)

    def test_get_paymentRhythmMonthly_generatesCorrectPayments(self):
        self.now = mock_timezone(self, now=datetime.datetime(year=2020, month=1, day=1))
        member = MemberFactory.create()
        self.client.force_login(member)

        TapirParameter.objects.filter(key=ParameterKeys.PAYMENT_DUE_DAY).update(
            value=15
        )

        growing_period = GrowingPeriodFactory.create(
            start_date=self.now.date(),
            end_date=datetime.date(year=2020, month=12, day=31),
        )
        subscription = SubscriptionFactory.create(
            member=member,
            solidarity_price_percentage=0.1,
            period=growing_period,
            quantity=1,
        )
        ProductPriceFactory.create(
            product=subscription.product, price=10, valid_from=self.now.date()
        )
        MemberPaymentRhythm.objects.create(
            member=member,
            rhythm=MemberPaymentRhythm.Rhythm.MONTHLY,
            valid_from=self.now.date(),
        )

        url = reverse("payments:member_future_payments")
        url = f"{url}?member_id={member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, 200)

        response_content = response.json()

        self.assertEqual(
            12,
            len(response_content),
            "The should be a payment for each month of the growing period",
        )
        response_content.sort(
            key=lambda extended_payment: extended_payment["payment"]["due_date"]
        )
        for index, extended_payment in enumerate(response_content):
            self.assertEqual(11, extended_payment["payment"]["amount"])
            self.assertEqual(
                datetime.date(year=2020, month=index + 1, day=15),
                datetime.datetime.strptime(
                    extended_payment["payment"]["due_date"], "%Y-%m-%d"
                ).date(),
            )
            self.assertEqual(
                datetime.date(year=2020, month=index + 1, day=1),
                datetime.datetime.strptime(
                    extended_payment["payment"]["subscription_payment_range_start"],
                    "%Y-%m-%d",
                ).date(),
            )
            self.assertEqual(
                get_last_day_of_month(datetime.date(year=2020, month=index + 1, day=1)),
                datetime.datetime.strptime(
                    extended_payment["payment"]["subscription_payment_range_end"],
                    "%Y-%m-%d",
                ).date(),
            )
            self.assertEqual([], extended_payment["coop_share_transactions"])
            self.assertEqual(1, len(extended_payment["subscriptions"]))
            self.assertEqual(
                subscription.id, extended_payment["subscriptions"][0]["id"]
            )

    def test_get_paymentRhythmQuarterly_generatesCorrectPayments(self):
        self.now = mock_timezone(
            self, now=datetime.datetime(year=2020, month=11, day=7)
        )
        member = MemberFactory.create()
        self.client.force_login(member)

        TapirParameter.objects.filter(key=ParameterKeys.PAYMENT_DUE_DAY).update(value=6)
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        ).update(value=True)

        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2020, month=7, day=1),
            end_date=datetime.date(year=2021, month=6, day=30),
        )
        GrowingPeriodFactory.create(
            start_date=datetime.date(year=2021, month=7, day=1),
            end_date=datetime.date(year=2022, month=6, day=30),
        )
        subscription = SubscriptionFactory.create(
            member=member,
            solidarity_price_percentage=0,
            period=growing_period,
            quantity=1,
        )

        ProductPriceFactory.create(
            product=subscription.product, price=10, valid_from=self.now.date()
        )
        MemberPaymentRhythm.objects.create(
            member=member,
            rhythm=MemberPaymentRhythm.Rhythm.QUARTERLY,
            valid_from=datetime.date(year=2020, month=1, day=1),
        )

        url = reverse("payments:member_future_payments")
        url = f"{url}?member_id={member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, 200)

        response_content = response.json()

        response_content.sort(
            key=lambda extended_payment: extended_payment["payment"]["due_date"]
        )

        self.assertEqual(
            5,
            len(response_content),
            "The should be a payment for each month of the growing period",
        )

        expected_due_dates = [
            "2020-11-06",
            "2021-01-06",
            "2021-04-06",
            "2021-07-06",
            "2021-10-06",
        ]
        expected_ranges = [
            ("2020-10-01", "2020-12-31"),
            ("2021-01-01", "2021-03-31"),
            ("2021-04-01", "2021-06-30"),
            ("2021-07-01", "2021-09-30"),
            ("2021-10-01", "2021-12-31"),
        ]

        for index, extended_payment in enumerate(response_content):
            self.assertEqual(30, extended_payment["payment"]["amount"])
            self.assertEqual(
                expected_due_dates[index], extended_payment["payment"]["due_date"]
            )
            self.assertEqual(
                expected_ranges[index],
                (
                    extended_payment["payment"]["subscription_payment_range_start"],
                    extended_payment["payment"]["subscription_payment_range_end"],
                ),
            )
            self.assertEqual([], extended_payment["coop_share_transactions"])
            self.assertEqual(1, len(extended_payment["subscriptions"]))

    def test_get_somePaymentsAlreadyExist_existingPaymentsTakenIntoAccount(self):
        self.skipTest("TODO")

    def test_get_subscriptionInTrial_trialPeriodGetsPaidMonthly(self):
        self.skipTest("TODO")

    def test_get_subscriptionIsCancelled_noPaymentsGeneratedAfterEndDate(self):
        self.skipTest("TODO")

    def test_get_somePastPaymentsAreStillDue_includesThosePayments(self):
        self.skipTest("TODO")

    def test_get_coopSharePaymentsExisting_includesThosePayment(self):
        self.skipTest("TODO")
