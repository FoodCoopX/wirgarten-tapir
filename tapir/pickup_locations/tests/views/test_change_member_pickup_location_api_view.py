import datetime
from unittest.mock import patch, Mock

from django.urls import reverse
from rest_framework import status
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.configuration.models import TapirParameter
from tapir.pickup_locations.models import PickupLocationChangedLogEntry
from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import MemberPickupLocation
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tapirmail import configure_mail_module
from tapir.wirgarten.tests.factories import (
    MemberPickupLocationFactory,
    PickupLocationFactory,
    SubscriptionFactory,
    PickupLocationCapabilityFactory,
    ProductPriceFactory,
    MemberFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestChangeMemberPickupLocationApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self) -> None:
        super().setUp()
        self.now = mock_timezone(
            self, now=datetime.datetime(year=1998, month=6, day=15)
        )

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_default_memberPickupLocationChangedAtCorrectDateAndLogEntryCreatedAndMailTriggerFired(
        self, mock_fire_action: Mock
    ):
        old_member_pickup_location = MemberPickupLocationFactory.create(
            valid_from=datetime.datetime(year=1998, month=1, day=1)
        )
        member = old_member_pickup_location.member
        new_pickup_location = PickupLocationFactory.create()

        SubscriptionFactory.create(
            member=member,
            start_date=datetime.datetime(year=1998, month=1, day=1),
            product__type__delivery_cycle=WEEKLY[0],
        )

        self.client.force_login(member)
        url = reverse("pickup_locations:change_member_pickup_location")
        response = self.client.post(
            f"{url}?member_id={member.id}&pickup_location_id={new_pickup_location.id}"
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_response_content_is_correct(response, error_message=None)

        self.assertEqual(2, MemberPickupLocation.objects.count())
        member_pickup_location = MemberPickupLocation.objects.order_by(
            "valid_from"
        ).last()
        self.assertEqual(
            new_pickup_location.id, member_pickup_location.pickup_location_id
        )
        self.assertEqual(member.id, member_pickup_location.member_id)
        self.assertEqual(
            datetime.date(year=1998, month=6, day=18), member_pickup_location.valid_from
        )

        self.assertEqual(1, PickupLocationChangedLogEntry.objects.count())
        log_entry = PickupLocationChangedLogEntry.objects.get()
        self.assertEqual(self.now, log_entry.created_date)
        self.assertEqual(member.email, log_entry.actor.email)
        self.assertEqual(member.email, log_entry.user.email)
        self.assertEqual(member_pickup_location.valid_from, log_entry.valid_from)
        self.assertEqual(new_pickup_location.name, log_entry.new_pickup_location_name)
        self.assertEqual(
            old_member_pickup_location.pickup_location.name,
            log_entry.old_pickup_location_name,
        )

        mock_fire_action.assert_called_once()
        trigger_data: TransactionalTriggerData = mock_fire_action.call_args_list[
            0
        ].args[0]
        self.assertEqual(Events.MEMBERAREA_CHANGE_PICKUP_LOCATION, trigger_data.key)
        self.assertEqual(member.id, trigger_data.recipient_id_in_base_queryset)
        self.assertIsNone(trigger_data.recipient_outside_of_base_queryset)
        self.assertEqual(
            {
                "pickup_location": new_pickup_location.name,
                "pickup_location_start_date": "24.06.1998",  # here we want the date of the first delivery at that location, no the date where the change is valid
            },
            trigger_data.token_data,
        )

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_newLocationIsSameAsOldLocation_doesntApplyChangesAndReturnsFalse(
        self, mock_fire_action: Mock
    ):
        old_member_pickup_location = MemberPickupLocationFactory.create(
            valid_from=datetime.datetime(year=1998, month=1, day=1)
        )
        member = old_member_pickup_location.member

        SubscriptionFactory.create(
            member=member,
            start_date=datetime.datetime(year=1998, month=1, day=1),
            product__type__delivery_cycle=WEEKLY[0],
        )

        self.client.force_login(member)
        url = reverse("pickup_locations:change_member_pickup_location")
        response = self.client.post(
            f"{url}?member_id={member.id}&pickup_location_id={old_member_pickup_location.pickup_location.id}"
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_response_content_is_correct(
            response,
            error_message="Du bist schon für diese Verteilstation eingetragen.",
        )

        self.assertEqual(1, MemberPickupLocation.objects.count())
        self.assertFalse(PickupLocationChangedLogEntry.objects.exists())

        mock_fire_action.assert_not_called()

    def test_post_goingBackToPreviousLocation_applyChanges(self):
        # regression test for # 906
        # here we make sure that if there is a future change happening before the next delivery,
        # we use that future location to check new_location != old_location
        # and therefore don't raise the new_location == old_location error
        # so that if a user changes their location, then on the same day changes back to their original location,
        # the change is applied

        old_member_pickup_location = MemberPickupLocationFactory.create(
            valid_from=datetime.datetime(year=1998, month=1, day=1)
        )
        member = old_member_pickup_location.member
        MemberPickupLocationFactory.create(
            member=member, valid_from=datetime.date(year=1998, month=6, day=18)
        )
        configure_mail_module()

        SubscriptionFactory.create(
            member=member,
            start_date=datetime.datetime(year=1998, month=1, day=1),
            product__type__delivery_cycle=WEEKLY[0],
        )

        self.client.force_login(member)
        url = reverse("pickup_locations:change_member_pickup_location")
        response = self.client.post(
            f"{url}?member_id={member.id}&pickup_location_id={old_member_pickup_location.pickup_location.id}"
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_response_content_is_correct(response, error_message=None)

        self.assertEqual(2, MemberPickupLocation.objects.count())
        member_pickup_location = MemberPickupLocation.objects.order_by(
            "valid_from"
        ).last()
        self.assertEqual(
            old_member_pickup_location.pickup_location.id,
            member_pickup_location.pickup_location_id,
        )
        self.assertEqual(member.id, member_pickup_location.member_id)
        self.assertEqual(
            datetime.date(year=1998, month=6, day=18), member_pickup_location.valid_from
        )

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_newLocationIsTheDonationLocation_doesntApplyChangesAndReturnsFalse(
        self, mock_fire_action: Mock
    ):
        old_member_pickup_location = MemberPickupLocationFactory.create(
            valid_from=datetime.datetime(year=1998, month=1, day=1)
        )
        new_pickup_location = PickupLocationFactory.create()
        member = old_member_pickup_location.member
        TapirParameter.objects.filter(
            key=ParameterKeys.DELIVERY_DONATION_FORWARD_TO_PICKUP_LOCATION
        ).update(value=new_pickup_location.id)

        SubscriptionFactory.create(
            member=member,
            start_date=datetime.datetime(year=1998, month=1, day=1),
            product__type__delivery_cycle=WEEKLY[0],
        )

        self.client.force_login(member)
        url = reverse("pickup_locations:change_member_pickup_location")
        response = self.client.post(
            f"{url}?member_id={member.id}&pickup_location_id={new_pickup_location.id}"
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_response_content_is_correct(
            response,
            error_message="Dieser Abholort kann nicht ausgewählt werden (Das ist die Spende-Sonder-Ort).",
        )

        self.assertEqual(1, MemberPickupLocation.objects.count())
        self.assertFalse(PickupLocationChangedLogEntry.objects.exists())

        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_memberHasNoContractThatNeedsALocation_doesntApplyChangesAndReturnsFalse(
        self, mock_fire_action: Mock
    ):
        old_member_pickup_location = MemberPickupLocationFactory.create(
            valid_from=datetime.datetime(year=1998, month=1, day=1)
        )
        new_pickup_location = PickupLocationFactory.create()
        member = old_member_pickup_location.member

        self.client.force_login(member)
        url = reverse("pickup_locations:change_member_pickup_location")
        response = self.client.post(
            f"{url}?member_id={member.id}&pickup_location_id={new_pickup_location.id}"
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_response_content_is_correct(
            response,
            error_message="Deine Verträge brauchen keine Verteilstation.",
        )

        self.assertEqual(1, MemberPickupLocation.objects.count())
        self.assertFalse(PickupLocationChangedLogEntry.objects.exists())

        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_newLocationDoesntHaveEnoughCapacity_doesntApplyChangesAndReturnsFalse(
        self, mock_fire_action: Mock
    ):
        old_member_pickup_location = MemberPickupLocationFactory.create(
            valid_from=datetime.datetime(year=1998, month=1, day=1)
        )
        new_pickup_location = PickupLocationFactory.create()
        member = old_member_pickup_location.member

        subscription = SubscriptionFactory.create(
            member=member,
            start_date=datetime.datetime(year=1998, month=1, day=1),
            product__type__delivery_cycle=WEEKLY[0],
            quantity=1,
        )

        PickupLocationCapabilityFactory.create(
            pickup_location=new_pickup_location,
            product_type=subscription.product.type,
            max_capacity=1,
        )
        ProductPriceFactory.create(product=subscription.product, size=2)

        self.client.force_login(member)
        url = reverse("pickup_locations:change_member_pickup_location")
        response = self.client.post(
            f"{url}?member_id={member.id}&pickup_location_id={new_pickup_location.id}"
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_response_content_is_correct(
            response,
            error_message="Diese Abholort hat nicht genug Kapazitäten für deine Verträge.",
        )

        self.assertEqual(1, MemberPickupLocation.objects.count())
        self.assertFalse(PickupLocationChangedLogEntry.objects.exists())

        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_normalMemberChangesLocationOfOtherMember_returns403(
        self, mock_fire_action: Mock
    ):
        old_member_pickup_location = MemberPickupLocationFactory.create(
            valid_from=datetime.datetime(year=1998, month=1, day=1)
        )
        new_pickup_location = PickupLocationFactory.create()
        member = old_member_pickup_location.member

        SubscriptionFactory.create(
            member=member,
            start_date=datetime.datetime(year=1998, month=1, day=1),
            product__type__delivery_cycle=WEEKLY[0],
            quantity=1,
        )

        self.client.force_login(MemberFactory.create(is_superuser=False))
        url = reverse("pickup_locations:change_member_pickup_location")
        response = self.client.post(
            f"{url}?member_id={member.id}&pickup_location_id={new_pickup_location.id}"
        )

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

        self.assertEqual(1, MemberPickupLocation.objects.count())
        self.assertFalse(PickupLocationChangedLogEntry.objects.exists())

        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_adminChangesLocationOfOtherMember_appliesChanges(
        self, mock_fire_action: Mock
    ):
        old_member_pickup_location = MemberPickupLocationFactory.create(
            valid_from=datetime.datetime(year=1998, month=1, day=1)
        )
        target_member = old_member_pickup_location.member
        new_pickup_location = PickupLocationFactory.create()

        SubscriptionFactory.create(
            member=target_member,
            start_date=datetime.datetime(year=1998, month=1, day=1),
            product__type__delivery_cycle=WEEKLY[0],
        )

        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)
        url = reverse("pickup_locations:change_member_pickup_location")
        response = self.client.post(
            f"{url}?member_id={target_member.id}&pickup_location_id={new_pickup_location.id}"
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_response_content_is_correct(response, error_message=None)

        self.assertEqual(2, MemberPickupLocation.objects.count())
        member_pickup_location = MemberPickupLocation.objects.order_by(
            "valid_from"
        ).last()
        self.assertEqual(
            new_pickup_location.id, member_pickup_location.pickup_location_id
        )
        self.assertEqual(target_member.id, member_pickup_location.member_id)
        self.assertEqual(
            datetime.date(year=1998, month=6, day=18), member_pickup_location.valid_from
        )

        self.assertEqual(1, PickupLocationChangedLogEntry.objects.count())
        log_entry = PickupLocationChangedLogEntry.objects.get()
        self.assertEqual(self.now, log_entry.created_date)
        self.assertEqual(admin.email, log_entry.actor.email)
        self.assertEqual(target_member.email, log_entry.user.email)
        self.assertEqual(member_pickup_location.valid_from, log_entry.valid_from)
        self.assertEqual(new_pickup_location.name, log_entry.new_pickup_location_name)
        self.assertEqual(
            old_member_pickup_location.pickup_location.name,
            log_entry.old_pickup_location_name,
        )

        mock_fire_action.assert_called_once()
        trigger_data: TransactionalTriggerData = mock_fire_action.call_args_list[
            0
        ].args[0]
        self.assertEqual(Events.MEMBERAREA_CHANGE_PICKUP_LOCATION, trigger_data.key)
        self.assertEqual(target_member.id, trigger_data.recipient_id_in_base_queryset)
        self.assertIsNone(trigger_data.recipient_outside_of_base_queryset)
        self.assertEqual(
            {
                "pickup_location": new_pickup_location.name,
                "pickup_location_start_date": "24.06.1998",  # here we want the date of the first delivery at that location, no the date where the change is valid
            },
            trigger_data.token_data,
        )

    def assert_response_content_is_correct(self, response, error_message: str | None):
        self.assertEqual(
            {"order_confirmed": error_message is None, "error": error_message},
            response.json(),
        )
