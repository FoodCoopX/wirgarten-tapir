import datetime
from unittest.mock import patch, Mock

from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework import status

from tapir.payments.models import MemberPaymentRhythm, MemberPaymentRhythmChangeLogEntry
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    GrowingPeriodFactory,
    SubscriptionFactory,
)
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

    def test_post_adminSetsPaymentRhythmOfOtherMemberWithASubscription_setsPaymentRhythmAtEndOfOldRhythm(
        self,
    ):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)
        other_member = MemberFactory.create()

        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2021, month=1, day=1)
        )
        SubscriptionFactory.create(period=growing_period, member=other_member)
        self._set_parameter(
            key=ParameterKeys.PAYMENT_DEFAULT_RHYTHM,
            value=MemberPaymentRhythm.Rhythm.QUARTERLY,
        )
        mock_timezone(test=self, now=datetime.datetime(year=2021, month=2, day=10))

        data = {"member_id": other_member.id, "rhythm": "yearly"}
        response = self.client.post(
            reverse("payments:set_member_payment_rhythm"), data=data
        )

        self.assertStatusCode(response, status.HTTP_200_OK)

        self.assertEqual(1, MemberPaymentRhythm.objects.count())
        rhythm_object = MemberPaymentRhythm.objects.get()
        self.assertEqual(
            MemberPaymentRhythm.Rhythm.YEARLY,
            rhythm_object.rhythm,
        )
        self.assertEqual(other_member.id, rhythm_object.member_id)
        self.assertEqual(
            datetime.date(year=2021, month=4, day=1),
            rhythm_object.valid_from,
            "Previously the member was using the default rhythm (quarterly), whose interval ends on 31.03.2021. The new interval should start one day after",
        )

        self.assertEqual(1, MemberPaymentRhythmChangeLogEntry.objects.count())
        log_entry = MemberPaymentRhythmChangeLogEntry.objects.get()
        self.assertEqual("yearly", log_entry.new_rhythm)
        self.assertEqual("quarterly", log_entry.old_rhythm)
        self.assertEqual(other_member.email, log_entry.user.email)
        self.assertEqual(member.email, log_entry.actor.email)

    def test_post_adminSetsPaymentRhythmOfOtherMemberWithoutSubscription_setsPaymentRhythmToday(
        self,
    ):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)
        other_member = MemberFactory.create()

        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2021, month=1, day=1)
        )
        self._set_parameter(
            key=ParameterKeys.PAYMENT_DEFAULT_RHYTHM,
            value=MemberPaymentRhythm.Rhythm.QUARTERLY,
        )
        mock_timezone(test=self, now=datetime.datetime(year=2021, month=2, day=10))

        data = {"member_id": other_member.id, "rhythm": "yearly"}
        response = self.client.post(
            reverse("payments:set_member_payment_rhythm"), data=data
        )

        self.assertStatusCode(response, status.HTTP_200_OK)

        self.assertEqual(1, MemberPaymentRhythm.objects.count())
        rhythm_object = MemberPaymentRhythm.objects.get()
        self.assertEqual(
            MemberPaymentRhythm.Rhythm.YEARLY,
            rhythm_object.rhythm,
        )
        self.assertEqual(other_member.id, rhythm_object.member_id)
        self.assertEqual(
            datetime.date(year=2021, month=2, day=10),
            rhythm_object.valid_from,
            "Since this member doesn't have any monthly payment yet, the rhythm should be set right away.",
        )

        self.assertEqual(1, MemberPaymentRhythmChangeLogEntry.objects.count())
        log_entry = MemberPaymentRhythmChangeLogEntry.objects.get()
        self.assertEqual("yearly", log_entry.new_rhythm)
        self.assertEqual("quarterly", log_entry.old_rhythm)
        self.assertEqual(other_member.email, log_entry.user.email)
        self.assertEqual(member.email, log_entry.actor.email)

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
