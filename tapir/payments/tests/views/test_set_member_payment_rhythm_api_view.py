import datetime
from unittest.mock import patch, Mock

from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework import status

from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestSetPaymentRhythmApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_post_normalMemberSetsOwnPaymentRhythm_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        data = {"member_id": member.id, "rhythm": "yearly"}
        response = self.client.post(
            reverse("payments:set_member_payment_rhythm"), data=data
        )

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        self.assertEqual(0, MemberPaymentRhythm.objects.count())

    def test_post_normalMemberSetsPaymentRhythmOfOtherMember_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)
        other_member = MemberFactory.create()

        data = {"member_id": other_member.id, "rhythm": "yearly"}
        response = self.client.post(
            reverse("payments:set_member_payment_rhythm"), data=data
        )

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        self.assertEqual(0, MemberPaymentRhythm.objects.count())

    def test_post_adminSetsPaymentRhythmOfOtherMember_setsPaymentRhythm(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)
        other_member = MemberFactory.create()

        data = {"member_id": other_member.id, "rhythm": "yearly"}
        response = self.client.post(
            reverse("payments:set_member_payment_rhythm"), data=data
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(1, MemberPaymentRhythm.objects.count())
        self.assertEqual(
            MemberPaymentRhythm.Rhythm.YEARLY,
            MemberPaymentRhythm.objects.first().rhythm,
        )

    def test_post_adminSetsInvalidRhythm_raisesValidationError(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        data = {"member_id": member.id, "rhythm": "yearlie"}
        with self.assertRaises(ValidationError):
            self.client.post(reverse("payments:set_member_payment_rhythm"), data=data)

        self.assertEqual(0, MemberPaymentRhythm.objects.count())

    @patch.object(
        MemberPaymentRhythmService,
        "get_date_of_next_payment_rhythm_change",
        autospec=True,
    )
    @patch.object(
        MemberPaymentRhythmService, "assign_payment_rhythm_to_member", autospec=True
    )
    def test_post_default_callsServicesCorrectly(
        self,
        mock_assign_payment_rhythm_to_member: Mock,
        mock_get_date_of_next_payment_rhythm_change: Mock,
    ):
        mock_timezone(self, now=datetime.datetime(year=2027, month=8, day=13))
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)
        other_member = MemberFactory.create()

        mock_get_date_of_next_payment_rhythm_change.return_value = datetime.date(
            year=2028, month=10, day=1
        )

        data = {"member_id": other_member.id, "rhythm": "yearly"}
        response = self.client.post(
            reverse("payments:set_member_payment_rhythm"), data=data
        )

        self.assertStatusCode(response, status.HTTP_200_OK)

        mock_get_date_of_next_payment_rhythm_change.assert_called_once()
        self.assertEqual(
            other_member,
            mock_get_date_of_next_payment_rhythm_change.call_args.kwargs["member"],
        )
        self.assertEqual(
            datetime.date(year=2027, month=8, day=13),
            mock_get_date_of_next_payment_rhythm_change.call_args.kwargs[
                "reference_date"
            ],
        )

        mock_assign_payment_rhythm_to_member.assert_called_once()
        self.assertEqual(
            other_member,
            mock_assign_payment_rhythm_to_member.call_args.kwargs["member"],
        )
        self.assertEqual(
            datetime.date(year=2028, month=10, day=1),
            mock_assign_payment_rhythm_to_member.call_args.kwargs["valid_from"],
        )
