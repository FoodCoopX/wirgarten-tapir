import datetime
from unittest.mock import patch, Mock

from django.urls import reverse
from rest_framework import status

from tapir.deliveries.models import Joker
from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests import factories
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestCancelJokerView(TapirIntegrationTest):
    def setUp(self) -> None:
        ParameterDefinitions().import_definitions()
        mock_timezone(self, factories.NOW)

    @patch.object(JokerManagementService, "cancel_joker")
    def test_cancelJokerView_tryToCancelJokerOfAnotherMember_returns403(
        self, mock_cancel_joker: Mock
    ):
        user = MemberFactory.create()
        other_member = MemberFactory.create()
        joker = Joker.objects.create(
            member=other_member, date=datetime.date(year=2024, month=5, day=1)
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("Deliveries:cancel_joker") + "?joker_id=" + joker.id
        )

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        mock_cancel_joker.assert_not_called()

    @patch.object(JokerManagementService, "cancel_joker")
    def test_cancelJokerView_cancelJokerOfAnotherMemberAsAdmin_callsCancelJoker(
        self, mock_cancel_joker: Mock
    ):
        user = MemberFactory.create(is_superuser=True)
        other_member = MemberFactory.create()
        joker = Joker.objects.create(
            member=other_member, date=datetime.date(year=2024, month=5, day=1)
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("Deliveries:cancel_joker") + "?joker_id=" + joker.id
        )

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        mock_cancel_joker.assert_called_once_with(joker)

    @patch.object(JokerManagementService, "cancel_joker")
    def test_cancelJokerView_cancelOwnJokerAsNormalMember_callsCancelJoker(
        self, mock_cancel_joker: Mock
    ):
        user = MemberFactory.create(is_superuser=False)
        joker = Joker.objects.create(
            member=user, date=datetime.date(year=2024, month=5, day=1)
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("Deliveries:cancel_joker") + "?joker_id=" + joker.id
        )

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        mock_cancel_joker.assert_called_once_with(joker)

    @patch.object(JokerManagementService, "can_joker_be_cancelled")
    @patch.object(JokerManagementService, "cancel_joker")
    def test_cancelJokerView_jokerCannotBeCancelled_returns403(
        self, mock_cancel_joker: Mock, mock_can_joker_be_cancelled: Mock
    ):
        user = MemberFactory.create(is_superuser=False)
        joker = Joker.objects.create(
            member=user, date=datetime.date(year=2024, month=5, day=1)
        )
        self.client.force_login(user)
        mock_can_joker_be_cancelled.return_value = False

        response = self.client.post(
            reverse("Deliveries:cancel_joker") + "?joker_id=" + joker.id
        )

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        mock_cancel_joker.assert_not_called()
        mock_can_joker_be_cancelled.assert_called_once_with(joker)
