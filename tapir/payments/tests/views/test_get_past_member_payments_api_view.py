import datetime

from django.urls import reverse
from rest_framework import status

from tapir.configuration.models import TapirParameter
from tapir.payments.services.mandate_reference_provider import MandateReferenceProvider
from tapir.payments.tests.factories import MemberCreditFactory
from tapir.wirgarten.models import Payment
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestGetPastMemberPaymentsAPIView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_normalMemberGetsOwnPastPayments_returns200(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        url = reverse("payments:member_past_payments")
        url = f"{url}?member_id={member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, 200)

    def test_get_normalMemberGetsOwnPaymentsButSelfViewIsDisabled_returns403(self):
        TapirParameter.objects.filter(
            key=ParameterKeys.MEMBERS_CAN_SEE_OWN_PAYMENTS
        ).update(value=False)
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        url = reverse("payments:member_past_payments")
        url = f"{url}?member_id={member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_normalMemberGetsPaymentsOfOtherMember_returns403(self):
        logged_in_member = MemberFactory.create(is_superuser=False)
        other_member = MemberFactory.create()
        self.client.force_login(logged_in_member)

        url = reverse("payments:member_past_payments")
        url = f"{url}?member_id={other_member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, 403)

    def test_get_adminUserGetsPaymentsOfOtherMember_returns200(self):
        logged_in_member = MemberFactory.create(is_superuser=True)
        other_member = MemberFactory.create()
        self.client.force_login(logged_in_member)

        url = reverse("payments:member_past_payments")
        url = f"{url}?member_id={other_member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, 200)

    def test_get_adminUserGetsPaymentsOfOtherMemberWithSelfViewDisabled_returns200Anyway(
        self,
    ):
        TapirParameter.objects.filter(
            key=ParameterKeys.MEMBERS_CAN_SEE_OWN_PAYMENTS
        ).update(value=False)

        logged_in_member = MemberFactory.create(is_superuser=True)
        other_member = MemberFactory.create()
        self.client.force_login(logged_in_member)

        url = reverse("payments:member_past_payments")
        url = f"{url}?member_id={other_member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, 200)

    def test_get_default_returnsCorrectData(self):
        mock_timezone(test=self, now=datetime.datetime(year=2021, month=5, day=1))
        member = MemberFactory.create()
        self.client.force_login(member)

        mandate_ref = MandateReferenceProvider.get_or_create_mandate_reference(
            member=member, cache={}
        )
        past_payment_1 = Payment.objects.create(
            due_date=datetime.date(year=2020, month=1, day=1),
            amount=126,
            mandate_ref=mandate_ref,
            type="test_type",
        )
        past_payment_2 = Payment.objects.create(
            due_date=datetime.date(year=2021, month=2, day=3),
            amount=137,
            mandate_ref=mandate_ref,
            type="test_type",
        )
        Payment.objects.create(
            due_date=datetime.date(year=2022, month=1, day=1),
            amount=126,
            mandate_ref=mandate_ref,
            type="test_type",
        )

        url = reverse("payments:member_past_payments")
        url = f"{url}?member_id={member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, 200)

        response_content = response.json()
        self.assertEqual(
            2,
            len(response_content["payments"]),
            "The 3rd payment should not be included because it's in the future",
        )
        self.assertEqual(
            past_payment_2.id,
            response_content["payments"][0]["payment"]["id"],
            "past_payment_2 should be first because it's more recent",
        )
        self.assertEqual(
            past_payment_1.id, response_content["payments"][1]["payment"]["id"]
        )

    def test_get_memberHasSettledAndUnsettledPastCredits_bothAreReturned(self):
        mock_timezone(test=self, now=datetime.datetime(year=2021, month=5, day=1))
        member = MemberFactory.create()
        self.client.force_login(member)

        settled_credit = MemberCreditFactory.create(
            member=member,
            due_date=datetime.date(year=2021, month=1, day=1),
            settled_on=datetime.datetime(year=2021, month=1, day=5),
        )
        unsettled_credit = MemberCreditFactory.create(
            member=member,
            due_date=datetime.date(year=2021, month=2, day=1),
            settled_on=None,
        )
        MemberCreditFactory.create(
            member=member,
            due_date=datetime.date(year=2022, month=1, day=1),
        )

        url = reverse("payments:member_past_payments")
        url = f"{url}?member_id={member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, 200)
        returned_credit_ids = {credit["id"] for credit in response.json()["credits"]}
        self.assertEqual(
            {str(settled_credit.id), str(unsettled_credit.id)}, returned_credit_ids
        )

    def test_get_creditSettledBeforeItsDueDate_stillReturnedInPastView(self):
        mock_timezone(test=self, now=datetime.datetime(year=2021, month=5, day=1))
        member = MemberFactory.create()
        self.client.force_login(member)

        credit_settled_early = MemberCreditFactory.create(
            member=member,
            due_date=datetime.date(year=2021, month=6, day=1),
            settled_on=datetime.datetime(year=2021, month=5, day=1),
        )

        url = reverse("payments:member_past_payments")
        url = f"{url}?member_id={member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, 200)
        returned_credit_ids = {credit["id"] for credit in response.json()["credits"]}
        self.assertIn(
            str(credit_settled_early.id),
            returned_credit_ids,
            "A credit settled ahead of its due date must still appear "
            "under past payments, not disappear from the view entirely.",
        )

    def test_get_creditSettledBeforeItsDueDate_neverDisappearsFromEitherView(self):
        mock_timezone(test=self, now=datetime.datetime(year=2021, month=5, day=1))
        member = MemberFactory.create()
        self.client.force_login(member)

        credit_settled_early = MemberCreditFactory.create(
            member=member,
            due_date=datetime.date(year=2021, month=6, day=1),
            settled_on=datetime.datetime(year=2021, month=5, day=1),
        )

        past_url = reverse("payments:member_past_payments")
        past_url = f"{past_url}?member_id={member.id}"
        past_response = self.client.get(past_url)
        self.assertStatusCode(past_response, 200)
        past_credit_ids = {credit["id"] for credit in past_response.json()["credits"]}

        future_url = reverse("payments:member_future_payments")
        future_url = f"{future_url}?member_id={member.id}"
        future_response = self.client.get(future_url)
        self.assertStatusCode(future_response, 200)
        future_credit_ids = {
            credit["id"] for credit in future_response.json()["credits"]
        }

        self.assertIn(str(credit_settled_early.id), past_credit_ids)
        self.assertNotIn(str(credit_settled_early.id), future_credit_ids)
