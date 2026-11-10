import datetime
from unittest.mock import patch, Mock

from django.urls import reverse
from rest_framework import status
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.configuration.models import TapirParameter
from tapir.pickup_locations.models import (
    MemberDeliveryAddressChangedLogEntry,
    PickupLocationChangedLogEntry,
)
from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import Member, MemberPickupLocation, PickupLocation
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
    PickupLocationOpeningTimesFactory,
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
        new_pickup_location = PickupLocationFactory.create(
            street="test_street",
            postcode="test_postcode",
            city="test_city",
            contact_name="test_contact",
            info="test_info",
            messenger_group_link="test_link",
            photo_link="test_photo",
            access_code="test_access",
        )
        PickupLocationOpeningTimesFactory.create(
            pickup_location=new_pickup_location,
            day_of_week=0,
            open_time=datetime.time(hour=8, minute=0),
            close_time=datetime.time(hour=9, minute=0),
        )
        PickupLocationOpeningTimesFactory.create(
            pickup_location=new_pickup_location,
            day_of_week=1,
            open_time=datetime.time(hour=8, minute=45),
            close_time=datetime.time(hour=10, minute=30),
        )

        SubscriptionFactory.create(
            member=member,
            start_date=datetime.datetime(year=1998, month=1, day=1),
            product__type__delivery_cycle=WEEKLY[0],
        )

        self.client.force_login(member)
        response = self._post(
            member_id=member.id, pickup_location_id=new_pickup_location.id
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
                "pickup_location_start_date": "22.06.1998",  # here we want the date of the first delivery at that location, no the date where the change is valid
                "address": "test_street, test_postcode test_city",
                "contact_name": "test_contact",
                "infos": "test_info",
                "messenger_group_link": "test_link",
                "opening_times": "Montag: 08:00-09:00, Dienstag: 08:45-10:30",
                "photo_link": "test_photo",
                "access_code": "test_access",
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
        response = self._post(
            member_id=member.id,
            pickup_location_id=old_member_pickup_location.pickup_location.id,
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
        response = self._post(
            member_id=member.id,
            pickup_location_id=old_member_pickup_location.pickup_location.id,
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
        response = self._post(
            member_id=member.id, pickup_location_id=new_pickup_location.id
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_response_content_is_correct(
            response,
            error_message="Dieser Abholort kann nicht ausgewählt werden (das ist der Sonder-Abholort für Spenden).",
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
        response = self._post(
            member_id=member.id, pickup_location_id=new_pickup_location.id
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
        response = self._post(
            member_id=member.id, pickup_location_id=new_pickup_location.id
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_response_content_is_correct(
            response,
            error_message="Dieser Abholort hat nicht genug Kapazitäten für deine Verträge.",
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
        response = self._post(
            member_id=member.id, pickup_location_id=new_pickup_location.id
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
        response = self._post(
            member_id=target_member.id, pickup_location_id=new_pickup_location.id
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
            new_pickup_location.name, trigger_data.token_data["pickup_location"]
        )
        self.assertEqual(
            "24.06.1998", trigger_data.token_data["pickup_location_start_date"]
        )  # here we want the date of the first delivery at that location, no the date where the change is valid

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_memberChangesOwnLocationWhenFeatureDisabled_returns403(
        self, mock_fire_action: Mock
    ):
        old_member_pickup_location = MemberPickupLocationFactory.create(
            valid_from=datetime.datetime(year=1998, month=1, day=1)
        )
        new_pickup_location = PickupLocationFactory.create()
        member = old_member_pickup_location.member

        self._set_parameter(
            key=ParameterKeys.MEMBERS_CAN_CHANGE_PICKUP_LOCATION, value=False
        )

        self.client.force_login(member)
        response = self._post(
            member_id=member.id, pickup_location_id=new_pickup_location.id
        )

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

        self.assertEqual(1, MemberPickupLocation.objects.count())
        self.assertFalse(PickupLocationChangedLogEntry.objects.exists())

        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_adminChangesLocationOfMemberWhenFeatureDisabled_appliesChanges(
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

        self._set_parameter(
            key=ParameterKeys.MEMBERS_CAN_CHANGE_PICKUP_LOCATION, value=False
        )

        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)
        response = self._post(
            member_id=target_member.id, pickup_location_id=new_pickup_location.id
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

        mock_fire_action.assert_called_once()

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_homeDeliveryWithoutAddress_doesntApplyChangesAndReturnsFalse(
        self, mock_fire_action: Mock
    ):
        old_member_pickup_location = MemberPickupLocationFactory.create(
            valid_from=datetime.datetime(year=1998, month=1, day=1),
            member__street="",
            member__postcode="",
            member__city="",
        )
        member = old_member_pickup_location.member
        new_pickup_location = PickupLocationFactory.create(is_home_delivery=True)
        SubscriptionFactory.create(
            member=member,
            start_date=datetime.datetime(year=1998, month=1, day=1),
            product__type__delivery_cycle=WEEKLY[0],
        )

        self.client.force_login(member)
        response = self._post(
            member_id=member.id, pickup_location_id=new_pickup_location.id
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_response_content_is_correct(
            response,
            error_message="Für die Hauslieferung wird eine vollständige Lieferadresse (Straße, PLZ und Ort) benötigt.",
        )

        self.assertEqual(1, MemberPickupLocation.objects.count())
        self.assertFalse(PickupLocationChangedLogEntry.objects.exists())

        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_homeDeliveryWithAddressInRequest_savesAddressAndAppliesChanges(
        self, _: Mock
    ):
        member, new_pickup_location = (
            self._create_member_with_subscription_and_home_delivery_location()
        )

        self.client.force_login(member)
        response = self._post(
            member_id=member.id,
            pickup_location_id=new_pickup_location.id,
            data={"delivery_address": self._build_separate_address()},
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_response_content_is_correct(response, error_message=None)

        member.refresh_from_db()
        self.assertFalse(member.delivery_same_as_billing_address)
        self.assertEqual("Lieferweg 2", member.delivery_street)
        self.assertEqual("22222", member.delivery_postcode)
        self.assertEqual("Lieferdorf", member.delivery_city)
        self.assertEqual(1, MemberDeliveryAddressChangedLogEntry.objects.count())
        self.assertEqual(
            new_pickup_location.id,
            MemberPickupLocation.objects.order_by("valid_from")
            .last()
            .pickup_location_id,
        )

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_homeDeliveryWithIncompleteAddressInRequest_doesntApplyChangesAndReturnsFalse(
        self, mock_fire_action: Mock
    ):
        member, new_pickup_location = (
            self._create_member_with_subscription_and_home_delivery_location()
        )

        self.client.force_login(member)
        response = self._post(
            member_id=member.id,
            pickup_location_id=new_pickup_location.id,
            data={"delivery_address": self._build_separate_address(city="")},
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_response_content_is_correct(
            response,
            error_message="Für die Hauslieferung wird eine vollständige Lieferadresse (Straße, PLZ und Ort) benötigt.",
        )

        member.refresh_from_db()
        self.assertTrue(member.delivery_same_as_billing_address)
        self.assertEqual("", member.delivery_street)
        self.assertFalse(MemberDeliveryAddressChangedLogEntry.objects.exists())
        self.assertEqual(1, MemberPickupLocation.objects.count())
        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_addressInRequestButNewLocationIsNotHomeDelivery_ignoresAddress(
        self, _: Mock
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
        response = self._post(
            member_id=member.id,
            pickup_location_id=new_pickup_location.id,
            data={"delivery_address": self._build_separate_address()},
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_response_content_is_correct(response, error_message=None)

        member.refresh_from_db()
        self.assertTrue(member.delivery_same_as_billing_address)
        self.assertEqual("", member.delivery_street)
        self.assertFalse(MemberDeliveryAddressChangedLogEntry.objects.exists())

    @staticmethod
    def _create_member_with_subscription_and_home_delivery_location() -> (
        tuple[Member, PickupLocation]
    ):
        member = MemberPickupLocationFactory.create(
            valid_from=datetime.datetime(year=1998, month=1, day=1),
            member__street="",
            member__postcode="",
            member__city="",
        ).member
        SubscriptionFactory.create(
            member=member,
            start_date=datetime.datetime(year=1998, month=1, day=1),
            product__type__delivery_cycle=WEEKLY[0],
        )
        return member, PickupLocationFactory.create(is_home_delivery=True)

    @staticmethod
    def _build_separate_address(**overrides: str) -> dict[str, str | bool]:
        address = {
            "same_as_billing_address": False,
            "street": "Lieferweg 2",
            "street_2": "",
            "postcode": "22222",
            "city": "Lieferdorf",
            "country": "DE",
        }
        address.update(overrides)
        return address

    def _post(self, member_id: str, pickup_location_id: str, data: dict | None = None):
        return self.client.post(
            reverse("pickup_locations:change_member_pickup_location"),
            data={
                "member_id": member_id,
                "pickup_location_id": pickup_location_id,
                **(data or {}),
            },
            content_type="application/json",
        )

    def assert_response_content_is_correct(self, response, error_message: str | None):
        self.assertEqual(
            {"order_confirmed": error_message is None, "error": error_message},
            response.json(),
        )

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_newLocationNotYetAvailable_doesntApplyChangesAndReturnsFalse(
        self, mock_fire_action: Mock
    ):
        old_member_pickup_location = MemberPickupLocationFactory.create(
            valid_from=datetime.datetime(year=1998, month=1, day=1)
        )
        new_pickup_location = PickupLocationFactory.create(
            start_date=datetime.date(year=1998, month=7, day=6)
        )
        member = old_member_pickup_location.member

        self.client.force_login(member)
        response = self._post(
            member_id=member.id, pickup_location_id=new_pickup_location.id
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_response_content_is_correct(
            response,
            error_message="Dieser Abholort ist für den gewählten Zeitpunkt nicht verfügbar.",
        )

        self.assertEqual(1, MemberPickupLocation.objects.count())
        self.assertFalse(PickupLocationChangedLogEntry.objects.exists())

        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_newLocationAlreadyDecommissioned_doesntApplyChangesAndReturnsFalse(
        self, mock_fire_action: Mock
    ):
        old_member_pickup_location = MemberPickupLocationFactory.create(
            valid_from=datetime.datetime(year=1998, month=1, day=1)
        )
        new_pickup_location = PickupLocationFactory.create(
            end_date=datetime.date(year=1998, month=5, day=31)
        )
        member = old_member_pickup_location.member

        self.client.force_login(member)
        response = self._post(
            member_id=member.id, pickup_location_id=new_pickup_location.id
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_response_content_is_correct(
            response,
            error_message="Dieser Abholort ist für den gewählten Zeitpunkt nicht verfügbar.",
        )

        self.assertEqual(1, MemberPickupLocation.objects.count())
        self.assertFalse(PickupLocationChangedLogEntry.objects.exists())

        mock_fire_action.assert_not_called()
