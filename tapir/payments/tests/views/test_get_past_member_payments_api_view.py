import datetime

from django.urls import reverse
from rest_framework import status

from tapir.configuration.models import TapirParameter
from tapir.wirgarten.models import Payment
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.service.member import get_or_create_mandate_ref
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

        mandate_ref = get_or_create_mandate_ref(member=member)
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
