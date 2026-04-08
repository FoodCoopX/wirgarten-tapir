import datetime
from unittest.mock import patch, Mock, ANY

from django.urls import reverse
from rest_framework import status
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.configuration.models import TapirParameter
from tapir.deliveries.models import Joker, JokerCancelledLogEntry
from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests import factories
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestCancelJokerView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self) -> None:
        super().setUp()
        mock_timezone(self, factories.NOW)

    @patch.object(TransactionalTrigger, "fire_action")
    @patch.object(JokerManagementService, "cancel_joker")
    def test_cancelJokerView_tryToCancelJokerOfAnotherMember_returns403(
        self, mock_cancel_joker: Mock, mock_fire_action: Mock
    ):
        user = MemberFactory.create()
        other_member = MemberFactory.create()
        joker = Joker.objects.create(
            member=other_member, date=datetime.date(year=2024, month=5, day=1)
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("deliveries:cancel_joker") + "?joker_id=" + joker.id
        )

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        mock_cancel_joker.assert_not_called()
        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action")
    @patch.object(JokerManagementService, "cancel_joker")
    def test_cancelJokerView_cancelJokerOfAnotherMemberAsAdmin_callsCancelJoker(
        self, mock_cancel_joker: Mock, mock_fire_action: Mock
    ):
        user = MemberFactory.create(is_superuser=True)
        other_member = MemberFactory.create()
        joker = Joker.objects.create(
            member=other_member, date=datetime.date(year=2024, month=5, day=1)
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("deliveries:cancel_joker") + "?joker_id=" + joker.id
        )

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        mock_cancel_joker.assert_called_once_with(joker)
        mock_cancel_joker.assert_called_once_with(joker)
        mock_fire_action.assert_called_once_with(
            trigger_data=TransactionalTriggerData(
                key="deliveries.joker_cancelled",
                recipient_id_in_base_queryset=other_member.id,
                token_data={"joker_date": datetime.date(year=2024, month=5, day=1)},
            )
        )

        self.assertEqual(1, JokerCancelledLogEntry.objects.count())
        log_entry = JokerCancelledLogEntry.objects.get()
        self.assertEqual(other_member.email, log_entry.user.email)
        self.assertEqual(user.email, log_entry.actor.email)
        self.assertEqual(joker.date, log_entry.date)

    @patch.object(TransactionalTrigger, "fire_action")
    @patch.object(JokerManagementService, "cancel_joker")
    def test_cancelJokerView_cancelOwnJokerAsNormalMember_callsCancelJoker(
        self, mock_cancel_joker: Mock, mock_fire_action: Mock
    ):
        member = MemberFactory.create(is_superuser=False)
        joker = Joker.objects.create(
            member=member, date=datetime.date(year=2024, month=5, day=1)
        )
        self.client.force_login(member)

        response = self.client.post(
            reverse("deliveries:cancel_joker") + "?joker_id=" + joker.id
        )

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        mock_cancel_joker.assert_called_once_with(joker)
        mock_fire_action.assert_called_once_with(
            trigger_data=TransactionalTriggerData(
                key="deliveries.joker_cancelled",
                recipient_id_in_base_queryset=member.id,
                token_data={"joker_date": datetime.date(year=2024, month=5, day=1)},
            ),
        )

        self.assertEqual(1, JokerCancelledLogEntry.objects.count())
        log_entry = JokerCancelledLogEntry.objects.get()
        self.assertEqual(member.email, log_entry.user.email)
        self.assertEqual(member.email, log_entry.actor.email)
        self.assertEqual(joker.date, log_entry.date)

    @patch.object(TransactionalTrigger, "fire_action")
    @patch.object(JokerManagementService, "can_joker_be_cancelled")
    @patch.object(JokerManagementService, "cancel_joker")
    def test_cancelJokerView_jokerCannotBeCancelled_returns403(
        self,
        mock_cancel_joker: Mock,
        mock_can_joker_be_cancelled: Mock,
        mock_fire_action: Mock,
    ):
        user = MemberFactory.create(is_superuser=False)
        joker = Joker.objects.create(
            member=user, date=datetime.date(year=2024, month=5, day=1)
        )
        self.client.force_login(user)
        mock_can_joker_be_cancelled.return_value = False

        response = self.client.post(
            reverse("deliveries:cancel_joker") + "?joker_id=" + joker.id
        )

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        mock_cancel_joker.assert_not_called()
        mock_can_joker_be_cancelled.assert_called_once_with(joker, cache=ANY)
        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action")
    @patch.object(JokerManagementService, "cancel_joker")
    def test_cancelJokerView_jokerFeatureDisabled_returns403(
        self, mock_cancel_joker: Mock, mock_fire_action: Mock
    ):
        TapirParameter.objects.filter(key=ParameterKeys.JOKERS_ENABLED).update(
            value="False"
        )

        user = MemberFactory.create(is_superuser=True)
        other_member = MemberFactory.create()
        joker = Joker.objects.create(
            member=other_member, date=datetime.date(year=2024, month=5, day=1)
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("deliveries:cancel_joker") + "?joker_id=" + joker.id
        )

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        mock_cancel_joker.assert_not_called()
        mock_fire_action.assert_not_called()
