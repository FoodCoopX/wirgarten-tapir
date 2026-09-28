from unittest.mock import Mock, patch

from tapir.subscriptions.services.subscription_update_view_validator import (
    SubscriptionUpdateViewValidator,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch(
    "tapir.subscriptions.services.subscription_update_view_validator.get_parameter_value"
)
class TestSubscriptionUpdateViewValidatorMayMemberReduceSize(TapirUnitTest):
    @staticmethod
    def set_parameters(
        mock_get_parameter_value: Mock, bakery_enabled: bool, members_can_reduce: bool
    ):
        values = {
            ParameterKeys.BAKERY_ENABLED: bakery_enabled,
            ParameterKeys.BAKERY_MEMBERS_CAN_REDUCE_BREAD_SHARES: members_can_reduce,
        }
        mock_get_parameter_value.side_effect = lambda key, cache: values[key]

    @staticmethod
    def may_reduce(logged_in_user_is_admin: bool = False) -> bool:
        return SubscriptionUpdateViewValidator.may_member_reduce_size(
            logged_in_user_is_admin=logged_in_user_is_admin, cache={}
        )

    def test_mayMemberReduceSize_bothParametersOn_returnsTrue(
        self, mock_get_parameter_value: Mock
    ):
        self.set_parameters(mock_get_parameter_value, True, True)

        self.assertTrue(self.may_reduce())

    def test_mayMemberReduceSize_admin_returnsTrue(
        self, mock_get_parameter_value: Mock
    ):
        self.set_parameters(mock_get_parameter_value, False, False)

        self.assertTrue(self.may_reduce(logged_in_user_is_admin=True))

    def test_mayMemberReduceSize_bakeryDisabled_returnsFalse(
        self, mock_get_parameter_value: Mock
    ):
        self.set_parameters(mock_get_parameter_value, False, True)

        self.assertFalse(self.may_reduce())

    def test_mayMemberReduceSize_membersCannotReduceBreadShares_returnsFalse(
        self, mock_get_parameter_value: Mock
    ):
        self.set_parameters(mock_get_parameter_value, True, False)

        self.assertFalse(self.may_reduce())
