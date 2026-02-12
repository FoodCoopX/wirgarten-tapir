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
    DELIVERY_DONATION_MODE_ALWAYS_POSSIBLE,
    DELIVERY_DONATION_MODE_DISABLED,
)
from tapir.deliveries.models import DeliveryDonation, DeliveryDonationUsedLogEntry
from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone
from tapir.wirgarten.utils import format_date


class TestUseDeliveryDonationView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(key=ParameterKeys.DELIVERY_DONATION_MODE).update(
            value=DELIVERY_DONATION_MODE_ALWAYS_POSSIBLE
        )

    def setUp(self) -> None:
        mock_timezone(test=self, now=datetime.datetime(year=2000, month=2, day=22))

    @patch.object(TransactionalTrigger, "fire_action")
    def test_post_featureIsDisabled_returns403(self, mock_fire_action: Mock):
        TapirParameter.objects.filter(key=ParameterKeys.DELIVERY_DONATION_MODE).update(
            value=DELIVERY_DONATION_MODE_DISABLED
        )
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        url = reverse("deliveries:use_donation")
        url = f"{url}?member_id={member.id}&date=2000-06-15"
        response = self.client.post(url)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        self.assertFalse(DeliveryDonationUsedLogEntry.objects.exists())
        self.assertFalse(DeliveryDonation.objects.exists())
        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action")
    def test_post_memberCreatesDonationForAnotherMember_returns403(
        self, mock_fire_action: Mock
    ):
        logged_in_member = MemberFactory.create(is_superuser=False)
        self.client.force_login(logged_in_member)
        other_member = MemberFactory.create()
        SubscriptionFactory.create(
            member=other_member,
            start_date=datetime.date(year=2000, month=1, day=1),
            end_date=datetime.date(year=2000, month=12, day=31),
            product__type__delivery_cycle=WEEKLY[0],
        )

        url = reverse("deliveries:use_donation")
        url = f"{url}?member_id={other_member.id}&date=2000-06-15"
        response = self.client.post(url)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        self.assertFalse(DeliveryDonationUsedLogEntry.objects.exists())
        self.assertFalse(DeliveryDonation.objects.exists())
        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action")
    def test_post_memberCreatesOwnDonation_createsDonationAndSendsMailAndCreatesLogEntry(
        self, mock_fire_action: Mock
    ):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)
        SubscriptionFactory.create(
            member=member,
            start_date=datetime.date(year=2000, month=1, day=1),
            end_date=datetime.date(year=2000, month=12, day=31),
            product__type__delivery_cycle=WEEKLY[0],
        )

        url = reverse("deliveries:use_donation")
        url = f"{url}?member_id={member.id}&date=2000-06-15"
        response = self.client.post(url)

        self.assertStatusCode(response, status.HTTP_200_OK)

        self.assertEqual(1, DeliveryDonation.objects.count())
        donation = DeliveryDonation.objects.get()
        self.assertEqual(member, donation.member)
        self.assertEqual(datetime.date(year=2000, month=6, day=15), donation.date)

        mock_fire_action.assert_called_once_with(
            TransactionalTriggerData(
                key=DeliveriesConfig.MAIL_TRIGGER_DONATION_USED,
                recipient_id_in_base_queryset=member.id,
                token_data={"donation_date": format_date(donation.date)},
            ),
        )

        self.assertEqual(1, DeliveryDonationUsedLogEntry.objects.count())
        log_entry = DeliveryDonationUsedLogEntry.objects.get()
        self.assertEqual(member.email, log_entry.user.email)
        self.assertEqual(member.email, log_entry.actor.email)
        self.assertEqual(donation.date, log_entry.date)
        self.assertEqual(donation, log_entry.delivery_donation)

    @patch.object(TransactionalTrigger, "fire_action")
    def test_post_creationNotAllowed_createsDonationAndSendsMailAndCreatesLogEntry(
        self, mock_fire_action: Mock
    ):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)
        SubscriptionFactory.create(
            member=member,
            start_date=datetime.date(year=2000, month=1, day=1),
            end_date=datetime.date(year=2000, month=12, day=31),
            product__type__delivery_cycle=WEEKLY[0],
        )

        url = reverse("deliveries:use_donation")
        url = f"{url}?member_id={member.id}&date=2000-01-15"
        response = self.client.post(url)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        self.assertFalse(DeliveryDonationUsedLogEntry.objects.exists())
        self.assertFalse(DeliveryDonation.objects.exists())
        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action")
    def test_post_adminCreatesDonationForOtherMember_createsDonationAndSendsMailAndCreatesLogEntry(
        self, mock_fire_action: Mock
    ):
        admin = MemberFactory.create(is_superuser=True)
        normal_member = MemberFactory.create(is_superuser=False)
        self.client.force_login(admin)
        SubscriptionFactory.create(
            member=normal_member,
            start_date=datetime.date(year=2000, month=1, day=1),
            end_date=datetime.date(year=2000, month=12, day=31),
            product__type__delivery_cycle=WEEKLY[0],
        )

        url = reverse("deliveries:use_donation")
        url = f"{url}?member_id={normal_member.id}&date=2000-06-15"
        response = self.client.post(url)

        self.assertStatusCode(response, status.HTTP_200_OK)

        self.assertEqual(1, DeliveryDonation.objects.count())
        donation = DeliveryDonation.objects.get()
        self.assertEqual(normal_member, donation.member)
        self.assertEqual(datetime.date(year=2000, month=6, day=15), donation.date)

        mock_fire_action.assert_called_once_with(
            TransactionalTriggerData(
                key=DeliveriesConfig.MAIL_TRIGGER_DONATION_USED,
                recipient_id_in_base_queryset=normal_member.id,
                token_data={"donation_date": format_date(donation.date)},
            ),
        )

        self.assertEqual(1, DeliveryDonationUsedLogEntry.objects.count())
        log_entry = DeliveryDonationUsedLogEntry.objects.get()
        self.assertEqual(normal_member.email, log_entry.user.email)
        self.assertEqual(admin.email, log_entry.actor.email)
        self.assertEqual(donation.date, log_entry.date)
        self.assertEqual(donation, log_entry.delivery_donation)
