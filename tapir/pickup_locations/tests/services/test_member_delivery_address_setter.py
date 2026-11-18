from tapir.pickup_locations.models import MemberDeliveryAddressChangedLogEntry
from tapir.pickup_locations.services.member_delivery_address_getter import (
    DeliveryAddressInput,
)
from tapir.pickup_locations.services.member_delivery_address_setter import (
    MemberDeliveryAddressSetter,
)
from tapir.wirgarten.models import Member
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberDeliveryAddressSetter(TapirIntegrationTest):
    def setUp(self):
        super().setUp()
        self.member = MemberFactory.create()
        self.actor = MemberFactory.create(is_superuser=True)

    @staticmethod
    def _set_separate_address(member: Member, street: str):
        member.delivery_same_as_billing_address = False
        member.delivery_street = street
        member.delivery_street_2 = ""
        member.delivery_postcode = "22222"
        member.delivery_city = "Lieferdorf"
        member.delivery_country = "DE"

    def test_saveDeliveryAddress_separateAddress_savesFieldsAndLogsChange(self):
        self._set_separate_address(member=self.member, street="Lieferweg 2")

        MemberDeliveryAddressSetter.save_delivery_address(
            member=self.member, actor=self.actor
        )

        self.member.refresh_from_db()
        self.assertFalse(self.member.delivery_same_as_billing_address)
        self.assertEqual("Lieferweg 2", self.member.delivery_street)
        log_entry = MemberDeliveryAddressChangedLogEntry.objects.get()
        self.assertEqual("Wie Rechnungsadresse", log_entry.old_address)
        self.assertEqual("Lieferweg 2, 22222 Lieferdorf, DE", log_entry.new_address)
        self.assertEqual(self.actor.id, log_entry.actor_id)
        self.assertEqual(self.member.id, log_entry.user_id)

    def test_saveDeliveryAddress_sameAsBillingAddress_clearsAddressFields(self):
        self._set_separate_address(member=self.member, street="Lieferweg 2")
        self.member.save()
        self.member.delivery_same_as_billing_address = True

        MemberDeliveryAddressSetter.save_delivery_address(
            member=self.member, actor=self.actor
        )

        self.member.refresh_from_db()
        self.assertTrue(self.member.delivery_same_as_billing_address)
        self.assertEqual("", self.member.delivery_street)
        self.assertEqual("", self.member.delivery_postcode)
        self.assertEqual("", self.member.delivery_city)
        log_entry = MemberDeliveryAddressChangedLogEntry.objects.get()
        self.assertEqual("Lieferweg 2, 22222 Lieferdorf, DE", log_entry.old_address)
        self.assertEqual("Wie Rechnungsadresse", log_entry.new_address)

    def test_saveDeliveryAddress_unchangedAddress_createsNoLogEntry(self):
        MemberDeliveryAddressSetter.save_delivery_address(
            member=self.member, actor=self.actor
        )

        self.assertFalse(MemberDeliveryAddressChangedLogEntry.objects.exists())

    def test_saveDeliveryAddress_otherUnsavedChanges_savesOnlyDeliveryFields(self):
        self.member.first_name = "Nicht gespeichert"
        self._set_separate_address(member=self.member, street="Lieferweg 2")

        MemberDeliveryAddressSetter.save_delivery_address(
            member=self.member, actor=self.actor
        )

        self.assertNotEqual(
            "Nicht gespeichert", Member.objects.get(id=self.member.id).first_name
        )

    def test_applyDeliveryAddressInput_default_setsFieldsWithoutSaving(self):
        member = MemberFactory.build()

        MemberDeliveryAddressSetter.apply_delivery_address_input(
            target=member,
            delivery_address_input=DeliveryAddressInput(
                same_as_billing_address=False,
                street="Lieferweg 2",
                street_2="Hof",
                postcode="22222",
                city="Lieferdorf",
                country="AT",
            ),
        )

        self.assertFalse(member.delivery_same_as_billing_address)
        self.assertEqual("Lieferweg 2", member.delivery_street)
        self.assertEqual("Hof", member.delivery_street_2)
        self.assertEqual("22222", member.delivery_postcode)
        self.assertEqual("Lieferdorf", member.delivery_city)
        self.assertEqual("AT", member.delivery_country)
        self.assertFalse(Member.objects.filter(id=member.id).exists())
