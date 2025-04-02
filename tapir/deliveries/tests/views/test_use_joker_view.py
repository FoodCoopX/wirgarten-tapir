import datetime
from unittest.mock import patch, Mock

from django.urls import reverse
from rest_framework import status
from tapir_mail.triggers.transactional_trigger import TransactionalTrigger

from tapir.configuration.models import TapirParameter
from tapir.deliveries.models import Joker
from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests import factories
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestUseJokerView(TapirIntegrationTest):
    def setUp(self) -> None:
        ParameterDefinitions().import_definitions()
        mock_timezone(self, factories.NOW)

    @patch.object(TransactionalTrigger, "fire_action")
    @patch.object(JokerManagementService, "can_joker_be_used_in_week")
    def test_useJokerView_tryToUseJokerOfAnotherMember_returns403(
        self, mock_can_joker_be_used_in_week: Mock, mock_fire_action: Mock
    ):
        user = MemberFactory.create()
        other_member = MemberFactory.create()
        self.client.force_login(user)

        response = self.client.post(
            f"{reverse('Deliveries:use_joker')}?member_id={other_member.id}&date=2024-07-23"
        )

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.assertFalse(Joker.objects.exists())
        mock_can_joker_be_used_in_week.assert_not_called()
        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action")
    @patch.object(JokerManagementService, "can_joker_be_used_in_week")
    def test_useJokerView_useJokerOfAnotherMemberAsAdmin_jokerCreated(
        self, mock_can_joker_be_used_in_week: Mock, mock_fire_action: Mock
    ):
        user = MemberFactory.create(is_superuser=True)
        other_member = MemberFactory.create()
        self.client.force_login(user)
        mock_can_joker_be_used_in_week.return_value = True

        response = self.client.post(
            f"{reverse('Deliveries:use_joker')}?member_id={other_member.id}&date=2024-07-23"
        )

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(1, Joker.objects.count())
        date = datetime.date(year=2024, month=7, day=23)
        mock_can_joker_be_used_in_week.assert_called_once_with(other_member, date)
        mock_fire_action.assert_called_once_with(
            "deliveries.joker_used",
            other_member.email,
            {"joker_date": date},
        )

    @patch.object(TransactionalTrigger, "fire_action")
    @patch.object(JokerManagementService, "can_joker_be_used_in_week")
    def test_useJokerView_useOwnJokerAsNormalMember_jokerCreated(
        self, mock_can_joker_be_used_in_week: Mock, mock_fire_action: Mock
    ):
        user = MemberFactory.create(is_superuser=False)
        self.client.force_login(user)
        mock_can_joker_be_used_in_week.return_value = True

        response = self.client.post(
            f"{reverse('Deliveries:use_joker')}?member_id={user.id}&date=2024-07-23"
        )

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(1, Joker.objects.count())
        joker = Joker.objects.get()
        self.assertEqual(user, joker.member)
        date = datetime.date(year=2024, month=7, day=23)
        self.assertEqual(date, joker.date)
        mock_can_joker_be_used_in_week.assert_called_once_with(user, date)
        mock_fire_action.assert_called_once_with(
            "deliveries.joker_used",
            user.email,
            {"joker_date": date},
        )

    @patch.object(TransactionalTrigger, "fire_action")
    @patch.object(JokerManagementService, "can_joker_be_used_in_week")
    def test_useJokerView_notAllowedToUseJoker_returns403(
        self, mock_can_joker_be_used_in_week: Mock, mock_fire_action: Mock
    ):
        user = MemberFactory.create(is_superuser=False)
        self.client.force_login(user)
        mock_can_joker_be_used_in_week.return_value = False

        response = self.client.post(
            f"{reverse('Deliveries:use_joker')}?member_id={user.id}&date=2024-07-23"
        )

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.assertFalse(Joker.objects.exists())
        date = datetime.date(year=2024, month=7, day=23)
        mock_can_joker_be_used_in_week.assert_called_once_with(user, date)
        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action")
    @patch.object(JokerManagementService, "can_joker_be_used_in_week")
    def test_useJokerView_jokerFeatureDisabled_returns403(
        self, mock_can_joker_be_used_in_week: Mock, mock_fire_action: Mock
    ):
        TapirParameter.objects.filter(key=ParameterKeys.JOKERS_ENABLED).update(
            value="False"
        )

        user = MemberFactory.create(is_superuser=True)
        other_member = MemberFactory.create()
        self.client.force_login(user)
        mock_can_joker_be_used_in_week.return_value = True

        response = self.client.post(
            f"{reverse('Deliveries:use_joker')}?member_id={other_member.id}&date=2024-07-23"
        )

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.assertEqual(0, Joker.objects.count())
        mock_can_joker_be_used_in_week.assert_not_called()
        mock_fire_action.assert_not_called()
