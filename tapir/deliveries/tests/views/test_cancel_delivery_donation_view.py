import datetime
from unittest.mock import patch, Mock

from django.urls import reverse
from rest_framework import status
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.configuration.models import TapirParameter
from tapir.deliveries.apps import DeliveriesConfig
from tapir.deliveries.config import (
    DELIVERY_DONATION_MODE_DISABLED,
    DELIVERY_DONATION_MODE_ALWAYS_POSSIBLE,
)
from tapir.deliveries.models import DeliveryDonation, DeliveryDonationCancelledLogEntry
from tapir.deliveries.tests.factories import DeliveryDonationFactory
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestCancelDeliveryDonationView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(key=ParameterKeys.DELIVERY_DONATION_MODE).update(
            value=DELIVERY_DONATION_MODE_ALWAYS_POSSIBLE
        )

    @patch.object(TransactionalTrigger, "fire_action")
    def test_post_featureDisabled_returns403(self, mock_fire_action: Mock):
        TapirParameter.objects.filter(key=ParameterKeys.DELIVERY_DONATION_MODE).update(
            value=DELIVERY_DONATION_MODE_DISABLED
        )
        donation = DeliveryDonationFactory.create()
        user = MemberFactory.create(is_superuser=True)
        self.client.force_login(user)

        response = self.client.post(
            reverse("deliveries:cancel_donation"), data={"donation_id": donation.id}
        )

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_403_FORBIDDEN
        )

        self.assertEqual(1, DeliveryDonation.objects.count())
        self.assertFalse(DeliveryDonationCancelledLogEntry.objects.exists())
        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action")
    def test_post_donationDoesntExist_returns404(self, mock_fire_action: Mock):
        user = MemberFactory.create(is_superuser=True)
        self.client.force_login(user)

        response = self.client.post(
            reverse("deliveries:cancel_donation"), data={"donation_id": "abcd"}
        )

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_404_NOT_FOUND
        )
        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action")
    def test_post_normalMemberCancelsDonationOfOtherMember_returns403(
        self, mock_fire_action: Mock
    ):
        donation = DeliveryDonationFactory.create()
        user = MemberFactory.create(is_superuser=False)
        self.client.force_login(user)

        url = reverse("deliveries:cancel_donation")
        url = f"{url}?donation_id={donation.id}"
        response = self.client.post(url)

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_403_FORBIDDEN
        )

        self.assertEqual(1, DeliveryDonation.objects.count())
        self.assertFalse(DeliveryDonationCancelledLogEntry.objects.exists())
        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action")
    def test_post_normalMemberCancelsOwnDonation_cancelsDonationAndSendsMailAndCreatesLogEntry(
        self, mock_fire_action: Mock
    ):
        mock_timezone(test=self, now=datetime.datetime(year=1999, month=1, day=15))
        member = MemberFactory.create(is_superuser=False)
        donation_date = datetime.date(year=2000, month=4, day=13)
        donation = DeliveryDonationFactory.create(member=member, date=donation_date)
        self.client.force_login(member)

        url = reverse("deliveries:cancel_donation")
        url = f"{url}?donation_id={donation.id}"
        response = self.client.post(url)

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_200_OK
        )

        self.assertFalse(DeliveryDonation.objects.exists())
        self.assertEqual(1, DeliveryDonationCancelledLogEntry.objects.count())
        log_entry = DeliveryDonationCancelledLogEntry.objects.get()
        self.assertEqual(member.email, log_entry.user.email)
        self.assertEqual(member.email, log_entry.actor.email)
        self.assertEqual(donation.date, log_entry.date)

        mock_fire_action.assert_called_once_with(
            trigger_data=TransactionalTriggerData(
                key=DeliveriesConfig.MAIL_TRIGGER_DONATION_CANCELLED,
                recipient_id_in_base_queryset=member.id,
                token_data={"donation_date": donation_date},
            ),
        )

    @patch.object(TransactionalTrigger, "fire_action")
    def test_post_adminCancelsDonationOfOtherMember_cancelsDonationAndSendsMailAndCreatesLogEntry(
        self, mock_fire_action: Mock
    ):
        admin = MemberFactory.create(is_superuser=True)
        mock_timezone(test=self, now=datetime.datetime(year=1999, month=1, day=15))
        normal_member = MemberFactory.create(is_superuser=False)
        donation_date = datetime.date(year=2000, month=4, day=13)
        donation = DeliveryDonationFactory.create(
            member=normal_member, date=donation_date
        )
        self.client.force_login(admin)

        url = reverse("deliveries:cancel_donation")
        url = f"{url}?donation_id={donation.id}"
        response = self.client.post(url)

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_200_OK
        )

        self.assertFalse(DeliveryDonation.objects.exists())
        self.assertEqual(1, DeliveryDonationCancelledLogEntry.objects.count())
        log_entry = DeliveryDonationCancelledLogEntry.objects.get()
        self.assertEqual(normal_member.email, log_entry.user.email)
        self.assertEqual(admin.email, log_entry.actor.email)
        self.assertEqual(donation.date, log_entry.date)

        mock_fire_action.assert_called_once_with(
            trigger_data=TransactionalTriggerData(
                key=DeliveriesConfig.MAIL_TRIGGER_DONATION_CANCELLED,
                recipient_id_in_base_queryset=normal_member.id,
                token_data={"donation_date": donation_date},
            ),
        )

    @patch.object(TransactionalTrigger, "fire_action")
    def test_post_donationCannotBeCancelled_returns403(self, mock_fire_action: Mock):
        mock_timezone(test=self, now=datetime.datetime(year=1999, month=1, day=15))
        member = MemberFactory.create(is_superuser=False)
        donation_date = datetime.date(year=1998, month=4, day=13)
        donation = DeliveryDonationFactory.create(member=member, date=donation_date)
        self.client.force_login(member)

        url = reverse("deliveries:cancel_donation")
        url = f"{url}?donation_id={donation.id}"
        response = self.client.post(url)

        self.assertStatusCode(
            response=response, expected_status_code=status.HTTP_403_FORBIDDEN
        )

        self.assertEqual(1, DeliveryDonation.objects.count())
        self.assertFalse(DeliveryDonationCancelledLogEntry.objects.exists())
        mock_fire_action.assert_not_called()
