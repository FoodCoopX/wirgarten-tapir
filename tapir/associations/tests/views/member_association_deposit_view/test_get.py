from tapir.associations.tests.views.member_association_deposit_view.base import (
    MemberAssociationDepositViewTestCase,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.factories import MemberFactory


class TestMemberAssociationDepositViewGet(MemberAssociationDepositViewTestCase):
    def test_get_default_returnsAmountAndIncreaseOption(self):
        response = self.client.get(self.url)
        self.assertStatusCode(response, 200)
        self.assertEqual(200, response.json()["amount"])
        self.assertTrue(response.json()["can_increase"])

    def test_get_disabledFeature_returns403(self):
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED, False)
        self.assertStatusCode(self.client.get(self.url), 403)

    def test_get_otherMember_returns403(self):
        self.client.force_login(MemberFactory.create())
        self.assertStatusCode(self.client.get(self.url), 403)

    def test_get_memberIncreaseDisabled_hidesIncreaseOption(self):
        self._set_parameter(
            ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_MEMBER_INCREASE, False
        )
        self.assertFalse(self.client.get(self.url).json()["can_increase"])

    def test_get_adminAndMemberIncreaseDisabled_allowsIncrease(self):
        self._set_parameter(
            ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_MEMBER_INCREASE, False
        )
        self.client.force_login(MemberFactory.create(is_superuser=True))
        self.assertTrue(self.client.get(self.url).json()["can_increase"])
