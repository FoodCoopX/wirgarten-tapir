import datetime

from django.urls import reverse

from tapir.wirgarten.models import (
    Subscription,
    CoopShareTransaction,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberWithSubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import (
    TapirIntegrationTest,
    mock_timezone,
)


class TestCancelDuringTrialPeriod(TapirIntegrationTest):
    NOW = datetime.datetime(year=2023, month=6, day=12)

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
