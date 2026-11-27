from unittest.mock import MagicMock, Mock, patch

from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager
from tapir.coop.services.member_number_service import MemberNumberService
from tapir.core.services.member_extra_email_address_releaser import (
    MemberExtraEmailAddressReleaser,
)
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest
from tapir.wirgarten.views.member.list.modals import save_member_and_assign_number


@patch.object(KeycloakUserManager, "create_keycloak_user_if_necessary", autospec=True)
@patch.object(MemberExtraEmailAddressReleaser, "release_address", autospec=True)
@patch.object(MemberNumberService, "assign_member_number_if_eligible", autospec=True)
class TestSaveMemberAndAssignNumber(TapirUnitTest):
    def test_saveMemberAndAssignNumber_default_savesMemberReleasesAddressAndAssignsNumber(
        self,
        mock_assign_if_eligible: MagicMock,
        mock_release_address: MagicMock,
        mock_create_keycloak_user: MagicMock,
    ):
        member = MemberFactory.build()
        logged_in_user = MemberFactory.build()
        form = Mock(instance=member)
        form.request.user = logged_in_user

        save_member_and_assign_number(form)

        form.save.assert_called_once_with()
        mock_release_address.assert_called_once_with(
            address=member.email, actor=logged_in_user
        )
        mock_assign_if_eligible.assert_called_once_with(
            member, cache={}, actor=logged_in_user
        )
        mock_create_keycloak_user.assert_called_once_with(
            user=member, initial_password=None
        )

    def test_saveMemberAndAssignNumber_mixedCaseAddress_savesTheNormalisedAddress(
        self, _: MagicMock, mock_release_address: MagicMock, __: MagicMock
    ):
        logged_in_user = MemberFactory.build()
        form = Mock(instance=MemberFactory.build(email=" Member@Example.com"))
        form.request.user = logged_in_user

        save_member_and_assign_number(form)

        self.assertEqual("member@example.com", form.instance.email)
        self.assertEqual("member@example.com", form.instance.username)
        mock_release_address.assert_called_once_with(
            address="member@example.com", actor=logged_in_user
        )
