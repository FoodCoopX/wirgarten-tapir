import datetime

from django.urls import reverse
from rest_framework import status

from tapir.configuration.models import TapirParameter
from tapir.payments.models import MemberPaymentRhythm
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, GrowingPeriodFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestGetMemberPaymentRhythmDataApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_normalMemberGetsOwnRhythmData_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        url = reverse("payments:member_payment_rhythm_data")
        url = f"{url}?member_id={member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_normalMemberGetsRhythmDataOfOtherMember_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)
        other_member = MemberFactory.create()

        url = reverse("payments:member_payment_rhythm_data")
        url = f"{url}?member_id={other_member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_adminGetsPaymentRhythmOfOtherMember_returns200(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)
        other_member = MemberFactory.create()

        url = reverse("payments:member_payment_rhythm_data")
        url = f"{url}?member_id={other_member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)

    def test_get_default_returnsCorrectData(self):
        mock_timezone(self, now=datetime.datetime(year=2028, month=4, day=15))
        GrowingPeriodFactory.create(
            start_date=datetime.datetime(year=2028, month=1, day=1),
            end_date=datetime.datetime(year=2029, month=12, day=31),
        )
        TapirParameter.objects.filter(key=ParameterKeys.PAYMENT_ALLOWED_RHYTHMS).update(
            value=",".join(
                [
                    str(MemberPaymentRhythm.Rhythm.MONTHLY.label),
                    str(MemberPaymentRhythm.Rhythm.QUARTERLY.label),
                    str(MemberPaymentRhythm.Rhythm.YEARLY.label),
                ]
            ),
        )
        member = MemberFactory.create(is_superuser=True)
        rhythms = MemberPaymentRhythm.objects.bulk_create(
            [
                MemberPaymentRhythm(
                    member=member,
                    rhythm=MemberPaymentRhythm.Rhythm.QUARTERLY,
                    valid_from=datetime.date(year=2028, month=1, day=1),
                ),
                MemberPaymentRhythm(
                    member=member,
                    rhythm=MemberPaymentRhythm.Rhythm.YEARLY,
                    valid_from=datetime.date(year=2028, month=4, day=1),
                ),
            ],
        )

        self.client.force_login(member)

        url = reverse("payments:member_payment_rhythm_data")
        url = f"{url}?member_id={member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()

        self.assertEqual(
            {
                "monthly": "Monatlich",
                "quarterly": "Vierteljährlich",
                "yearly": "Jährlich",
            },
            response_content["allowed_rhythms"],
        )
        self.assertEqual("yearly", response_content["current_rhythm"])
        self.assertEqual("2029-01-01", response_content["date_of_next_rhythm_change"])
        self.assertEqual(
            [
                {
                    "id": rhythms[0].id,
                    "member": member.id,
                    "rhythm": "quarterly",
                    "valid_from": "2028-01-01",
                },
                {
                    "id": rhythms[1].id,
                    "member": member.id,
                    "rhythm": "yearly",
                    "valid_from": "2028-04-01",
                },
            ],
            response_content["rhythm_history"],
        )
