import datetime

from django.urls import reverse
from django.utils import timezone

from tapir.wirgarten.models import (
    Subscription,
    CoopShareTransaction,
    GrowingPeriod,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberWithSubscriptionFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import (
    TapirIntegrationTest,
    mock_timezone,
)


class TestCancelDuringTrialPeriod(TapirIntegrationTest):
    NOW = datetime.datetime(year=2023, month=6, day=12, tzinfo=timezone.now().tzinfo)
    END_OF_CURRENT_MONTH = datetime.datetime(year=2023, month=6, day=30)

    def setUp(self):
        ParameterDefinitions().import_definitions()
        mock_timezone(self, self.NOW)

    def test_trialCancellationForm_cancelMembershipAfterLastDelivery_succeeds(
        self,
    ):
        # Regression test for WLS-266 https://foodcoopx.atlassian.net/browse/WLS-266
        member = MemberWithSubscriptionFactory.create()
        self.client.force_login(member)
        Subscription.objects.update(
            start_date=self.NOW - datetime.timedelta(days=1),
            end_date=self.NOW + datetime.timedelta(days=1),
        )
        CoopShareTransaction.objects.update(
            valid_at=datetime.date(year=2023, month=7, day=1)
        )
        self.assertEqual(1, CoopShareTransaction.objects.count())

        response = self.client.post(
            reverse("wirgarten:member_cancel_trial", args=[member.id]),
            data={"cancel_coop": True},
        )

        self.assertStatusCode(response, 200)
        self.assertEqual(0, CoopShareTransaction.objects.count())

    def test_trialCancellationForm_cancelAfterRenewal_alsoCancelsRenewedContract(
        self,
    ):
        member = MemberWithSubscriptionFactory.create()
        self.client.force_login(member)

        current_growing_period = GrowingPeriod.objects.get()
        current_growing_period.start_date = self.NOW - datetime.timedelta(days=1)
        current_growing_period.end_date = self.END_OF_CURRENT_MONTH
        current_growing_period.save()

        current_subscription = Subscription.objects.get()  # The one in trial period
        current_subscription.start_date = current_growing_period.start_date
        current_subscription.end_date = current_growing_period.end_date
        current_subscription.save()

        next_growing_period = GrowingPeriod.objects.create(
            start_date=self.END_OF_CURRENT_MONTH + datetime.timedelta(days=1),
            end_date=self.END_OF_CURRENT_MONTH + datetime.timedelta(days=60),
        )
        renewed_subscription: Subscription = SubscriptionFactory.create(
            member=member,
            period=next_growing_period,
            product=current_subscription.product,
        )

        response = self.client.post(
            reverse("wirgarten:member_cancel_trial", args=[member.id]),
            data={f"sub_{current_subscription.id}": True},
        )

        self.assertStatusCode(response, 200)
        current_subscription.refresh_from_db()
        renewed_subscription.refresh_from_db()
        self.assertEqual(self.NOW, current_subscription.cancellation_ts)
        self.assertEqual(self.NOW, renewed_subscription.cancellation_ts)
        self.assertEqual(self.END_OF_CURRENT_MONTH, current_subscription.end_date)
        self.assertEqual(self.END_OF_CURRENT_MONTH, renewed_subscription.end_date)
