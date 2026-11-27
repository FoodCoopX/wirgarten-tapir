from unittest.mock import MagicMock, patch

from django.utils import timezone

from tapir.core.services.active_member_provider import ActiveMemberProvider
from tapir.core.services.former_member_address_provider import (
    FormerMemberAddressProvider,
)
from tapir.mail.models import ExternalRecipient
from tapir.wirgarten.models import Member
from tapir.wirgarten.tests.factories import MemberExtraEmailFactory, MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@patch.object(ActiveMemberProvider, "get_active_members", autospec=True)
class TestGetFormerMemberByAddress(TapirIntegrationTest):
    def setUp(self):
        self.former_member = MemberFactory.create(email="former@example.com")
        self.active_member = MemberFactory.create(email="active@example.com")

    def test_getFormerMemberByAddress_default_returnsTheMainAndConfirmedExtraAddressesOfFormerMembers(
        self, mock_get_active_members: MagicMock
    ):
        self._mark_active_member_as_active(mock_get_active_members)
        MemberExtraEmailFactory.create(
            member=self.former_member,
            email="confirmed@example.com",
            confirmed_on=timezone.now(),
        )
        MemberExtraEmailFactory.create(
            member=self.former_member,
            email="unconfirmed@example.com",
            confirmed_on=None,
        )
        MemberExtraEmailFactory.create(
            member=self.active_member,
            email="active.extra@example.com",
            confirmed_on=timezone.now(),
        )

        result = FormerMemberAddressProvider.get_former_member_by_address(
            reference_datetime=timezone.now(), cache={}
        )

        self.assertEqual(
            {
                "former@example.com": self.former_member,
                "confirmed@example.com": self.former_member,
            },
            result,
        )

    def test_getFormerMemberByAddress_addressStillInUse_excludesIt(
        self, mock_get_active_members: MagicMock
    ):
        self._mark_active_member_as_active(mock_get_active_members)
        MemberExtraEmailFactory.create(
            member=self.former_member,
            email="active@example.com",
            confirmed_on=timezone.now(),
        )
        MemberExtraEmailFactory.create(
            member=self.former_member,
            email="external@example.com",
            confirmed_on=timezone.now(),
        )
        ExternalRecipient.objects.create(email="external@example.com", first_name="E")

        result = FormerMemberAddressProvider.get_former_member_by_address(
            reference_datetime=timezone.now(), cache={}
        )

        self.assertEqual({"former@example.com": self.former_member}, result)

    def _mark_active_member_as_active(self, mock_get_active_members: MagicMock):
        mock_get_active_members.return_value = Member.objects.filter(
            id=self.active_member.id
        )
