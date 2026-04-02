import datetime
from unittest.mock import patch, Mock

from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.configuration.models import TapirParameter
from tapir.pickup_locations.models import PickupLocationChangedLogEntry
from tapir.pickup_locations.services.member_pickup_location_setter import (
    MemberPickupLocationSetter,
)
from tapir.wirgarten.constants import ODD_WEEKS
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import (
    MemberPickupLocation,
    PickupLocationOpeningTime,
    GrowingPeriod,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    MemberPickupLocationFactory,
    PickupLocationFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import mock_timezone, TapirIntegrationTest


class TestLinkMemberToPickupLocation(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(key=ParameterKeys.DELIVERY_DAY).update(value=2)

    def setUp(self):
        super().setUp()
        self.now = mock_timezone(
            test=self, now=datetime.datetime(year=2020, month=1, day=1)
        )

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_linkMemberToPickupLocation_memberHadNoLocationBefore_assignLocationValidFromTodayAndDontSendConfirmationMail(
        self, mock_fire_action: Mock
    ):
        member = MemberFactory.create()
        actor = MemberFactory.create()

        future_member_pickup_location = MemberPickupLocationFactory.create(
            member=member, valid_from=datetime.date(year=2020, month=6, day=1)
        )

        new_pickup_location = PickupLocationFactory.create()
        PickupLocationOpeningTime.objects.create(
            pickup_location=new_pickup_location,
            day_of_week=4,
            open_time=datetime.time(hour=10),
            close_time=datetime.time(hour=18),
        )

        MemberPickupLocationSetter.link_member_to_pickup_location(
            pickup_location_id=new_pickup_location.id,
            member=member,
            actor=actor,
            valid_from=datetime.date(year=2020, month=2, day=1),
            cache={},
        )

        self.assertEqual(1, MemberPickupLocation.objects.count())
        new_member_pickup_location = MemberPickupLocation.objects.get()
        self.assertNotEqual(
            future_member_pickup_location.id,
            new_member_pickup_location.id,
            "future_member_pickup_location should have been deleted",
        )
        self.assertEqual(
            new_member_pickup_location.valid_from,
            self.now.date(),
            "Since the member didn't have a location at the valid_from parameter, the actual valid_from should be today",
        )
        self.assertEqual(
            new_pickup_location, new_member_pickup_location.pickup_location
        )

        self.assertEqual(1, PickupLocationChangedLogEntry.objects.count())
        log_entry = PickupLocationChangedLogEntry.objects.get()
        self.assertEqual(member.email, log_entry.user.email)
        self.assertEqual(actor.email, log_entry.actor.email)
        self.assertEqual(new_pickup_location.name, log_entry.new_pickup_location_name)
        self.assertEqual("Keine", log_entry.old_pickup_location_name)
        self.assertEqual(self.now.date(), log_entry.valid_from)

        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_linkMemberToPickupLocation_hadALocationBefore_assignLocationValidFromGivenDateAndSendConfirmationMail(
        self, mock_fire_action: Mock
    ):
        member = MemberFactory.create()
        actor = MemberFactory.create()

        future_member_pickup_location = MemberPickupLocationFactory.create(
            member=member, valid_from=datetime.date(year=2020, month=6, day=1)
        )
        past_member_pickup_location = MemberPickupLocationFactory.create(
            member=member, valid_from=datetime.date(year=2019, month=6, day=1)
        )

        new_pickup_location = PickupLocationFactory.create()
        PickupLocationOpeningTime.objects.create(
            pickup_location=new_pickup_location,
            day_of_week=4,
            open_time=datetime.time(hour=10),
            close_time=datetime.time(hour=18),
        )

        MemberPickupLocationSetter.link_member_to_pickup_location(
            pickup_location_id=new_pickup_location.id,
            member=member,
            actor=actor,
            valid_from=datetime.date(year=2020, month=2, day=1),
            cache={},
        )

        self.assertEqual(2, MemberPickupLocation.objects.count())
        self.assertFalse(
            MemberPickupLocation.objects.filter(
                id=future_member_pickup_location.id
            ).exists()
        )
        new_member_pickup_location = MemberPickupLocation.objects.get(
            valid_from__gte=self.now.date()
        )

        self.assertEqual(
            new_member_pickup_location.valid_from,
            datetime.date(year=2020, month=2, day=1),
        )
        self.assertEqual(
            new_pickup_location, new_member_pickup_location.pickup_location
        )

        self.assertEqual(1, PickupLocationChangedLogEntry.objects.count())
        log_entry = PickupLocationChangedLogEntry.objects.get()
        self.assertEqual(member.email, log_entry.user.email)
        self.assertEqual(actor.email, log_entry.actor.email)
        self.assertEqual(new_pickup_location.name, log_entry.new_pickup_location_name)
        self.assertEqual(
            past_member_pickup_location.pickup_location.name,
            log_entry.old_pickup_location_name,
        )
        self.assertEqual(datetime.date(year=2020, month=2, day=1), log_entry.valid_from)

        mock_fire_action.assert_called_once()
        trigger_data: TransactionalTriggerData = mock_fire_action.call_args_list[
            0
        ].args[0]
        self.assertEqual(Events.MEMBERAREA_CHANGE_PICKUP_LOCATION, trigger_data.key)
        self.assertEqual(member.id, trigger_data.recipient_id_in_base_queryset)
        self.assertEqual(
            {
                "pickup_location": new_pickup_location.name,
                "pickup_location_start_date": "07.02.2020",  # With a change valid from the 01.02.2020 (a Saturday), the next delivery day (set by PickupLocationOpeningTime) should be a friday
            },
            trigger_data.token_data,
        )

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_linkMemberToPickupLocation_someDeliveryFreeWeeksAreSet_sendCorrectFirstDeliveryDateInConfirmationMail(
        self, mock_fire_action: Mock
    ):
        member = MemberFactory.create()
        actor = MemberFactory.create()

        SubscriptionFactory.create(
            member=member,
            period__start_date=datetime.date(year=2020, month=1, day=1),
            product__type__delivery_cycle=ODD_WEEKS[0],
        )
        growing_period = GrowingPeriod.objects.get()
        # The change is expected to be valid from week 6 of 2020. This should skip the two deliveries of February 2020
        # Therefore the first odd week that is delivered after the location change should be week 11
        growing_period.weeks_without_delivery = [7, 9]
        growing_period.save()

        MemberPickupLocationFactory.create(
            member=member, valid_from=datetime.date(year=2019, month=6, day=1)
        )

        new_pickup_location = PickupLocationFactory.create()
        PickupLocationOpeningTime.objects.create(
            pickup_location=new_pickup_location,
            day_of_week=4,
            open_time=datetime.time(hour=10),
            close_time=datetime.time(hour=18),
        )

        MemberPickupLocationSetter.link_member_to_pickup_location(
            pickup_location_id=new_pickup_location.id,
            member=member,
            actor=actor,
            valid_from=datetime.date(year=2020, month=2, day=1),
            cache={},
        )

        self.assertEqual(2, MemberPickupLocation.objects.count())
        new_member_pickup_location = MemberPickupLocation.objects.get(
            valid_from__gte=self.now.date()
        )

        self.assertEqual(
            new_member_pickup_location.valid_from,
            datetime.date(year=2020, month=2, day=1),
        )
        self.assertEqual(
            new_pickup_location, new_member_pickup_location.pickup_location
        )

        mock_fire_action.assert_called_once()
        trigger_data: TransactionalTriggerData = mock_fire_action.call_args_list[
            0
        ].args[0]
        self.assertEqual(Events.MEMBERAREA_CHANGE_PICKUP_LOCATION, trigger_data.key)
        self.assertEqual(member.id, trigger_data.recipient_id_in_base_queryset)
        self.assertEqual(
            {
                "pickup_location": new_pickup_location.name,
                "pickup_location_start_date": "13.03.2020",  # This is the first delivered Friday (week 11) after the location change
            },
            trigger_data.token_data,
        )
