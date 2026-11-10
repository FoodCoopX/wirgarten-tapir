import datetime

from tapir.wirgarten.models import Member
from tapir.wirgarten.tests.factories import (
    MemberPickupLocationFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.views.member.details.member_details import MemberDetailView


class TestMemberDetailViewDeliveryAddress(TapirIntegrationTest):
    TODAY = datetime.date(year=2027, month=6, day=15)

    @classmethod
    def _build_context(cls, member_id: str) -> dict:
        view = MemberDetailView()
        view.object = Member.objects.get(id=member_id)
        context = {}
        view.add_delivery_address_context(context=context, today=cls.TODAY, cache={})
        return context

    def test_addDeliveryAddressContext_noHomeDelivery_onlySetsFlag(self):
        member = MemberPickupLocationFactory.create(
            pickup_location__is_home_delivery=False,
            valid_from=datetime.date(year=2027, month=1, day=1),
        ).member

        self.assertEqual(
            {"has_home_delivery": False}, self._build_context(member_id=member.id)
        )

    def test_addDeliveryAddressContext_homeDelivery_setsResolvedAddress(self):
        member = MemberPickupLocationFactory.create(
            pickup_location__is_home_delivery=True,
            valid_from=datetime.date(year=2027, month=1, day=1),
            member__street="Rechnungsstraße 1",
            member__street_2="",
            member__postcode="11111",
            member__city="Rechnungsstadt",
        ).member

        self.assertEqual(
            {
                "has_home_delivery": True,
                "delivery_address_complete": True,
                "delivery_address": "Rechnungsstraße 1, 11111 Rechnungsstadt",
            },
            self._build_context(member_id=member.id),
        )

    def test_addDeliveryAddressContext_homeDeliveryAndIncompleteAddress_marksIncomplete(
        self,
    ):
        member = MemberPickupLocationFactory.create(
            pickup_location__is_home_delivery=True,
            valid_from=datetime.date(year=2027, month=1, day=1),
            member__street="",
            member__street_2="",
            member__postcode="",
            member__city="",
        ).member

        self.assertFalse(
            self._build_context(member_id=member.id)["delivery_address_complete"]
        )
