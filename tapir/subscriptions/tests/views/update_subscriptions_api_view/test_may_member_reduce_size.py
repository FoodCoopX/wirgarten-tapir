from tapir.configuration.models import TapirParameter
from tapir.subscriptions.services.subscription_update_view_validator import (
    SubscriptionUpdateViewValidator,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import ProductTypeFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestUpdateSubscriptionsApiViewMayMemberReduceSize(TapirIntegrationTest):
    """
    BAKERY_MEMBERS_CAN_REDUCES_BREAD_SHARES lets a member shrink a running
    contract. It is about bread, so it must not also unlock the harvest share.
    """

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        for key in [
            ParameterKeys.BAKERY_A_ENABLED,
            ParameterKeys.BAKERY_MEMBERS_CAN_REDUCES_BREAD_SHARES,
        ]:
            TapirParameter.objects.filter(key=key).update(value="True")

    @staticmethod
    def _may_reduce(is_bread: bool, logged_in_user_is_admin: bool = False) -> bool:
        return SubscriptionUpdateViewValidator.may_member_reduce_size(
            logged_in_user_is_admin=logged_in_user_is_admin,
            product_type=ProductTypeFactory.create(is_bread=is_bread),
            cache={},
        )

    def test_mayMemberReduceSize_breadProductType_isTrue(self):
        self.assertTrue(self._may_reduce(is_bread=True))

    def test_mayMemberReduceSize_nonBreadProductType_isFalse(self):
        # The harvest share stays locked even with the bakery parameter on.
        self.assertFalse(self._may_reduce(is_bread=False))

    def test_mayMemberReduceSize_adminOnANonBreadProductType_isTrue(self):
        self.assertTrue(self._may_reduce(is_bread=False, logged_in_user_is_admin=True))

    def test_mayMemberReduceSize_bakeryDisabled_breadShareStaysLocked(self):
        TapirParameter.objects.filter(key=ParameterKeys.BAKERY_A_ENABLED).update(
            value="False"
        )

        self.assertFalse(self._may_reduce(is_bread=True))

    def test_mayMemberReduceSize_parameterOff_breadShareStaysLocked(self):
        TapirParameter.objects.filter(
            key=ParameterKeys.BAKERY_MEMBERS_CAN_REDUCES_BREAD_SHARES
        ).update(value="False")

        self.assertFalse(self._may_reduce(is_bread=True))
