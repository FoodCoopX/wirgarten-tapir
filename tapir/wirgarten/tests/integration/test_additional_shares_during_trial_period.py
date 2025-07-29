import datetime

from django.urls import reverse

from tapir.configuration.models import TapirParameter
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberWithCoopSharesFactory,
    ProductTypeFactory,
)
from tapir.wirgarten.tests.test_utils import (
    TapirIntegrationTest,
    mock_timezone,
)


class TestAdditionalSharesDuringTrialPeriod(TapirIntegrationTest):
    NOW = datetime.datetime(year=2023, month=6, day=12)

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.COOP_SHARES_INDEPENDENT_FROM_HARVEST_SHARES
        ).update(value="True")
        product_type = ProductTypeFactory.create()
        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=product_type.id
        )

    def setUp(self):
        mock_timezone(self, self.NOW)

    def test_getAddCoopSharesForm_memberIsNotInTrialPeriod_canBuyMoreShares(
        self,
    ):
        member = MemberWithCoopSharesFactory.create(add_coop_shares__quantity=3)
        self.client.force_login(member)
        self.assertFalse(member.is_in_coop_trial())
        self.assertEqual(3, member.coop_shares_quantity)

        url = reverse("wirgarten:member_add_coop_shares", args=[member.id])
        data = {
            "cooperative_shares": 100,
            "statute_consent": True,
        }

        response = self.client.post(
            url,
            data=data,
        )

        self.assertStatusCode(response, 200)
        self.assertEqual(5, member.coop_shares_quantity)

    def test_getAddCoopSharesForm_memberIsInTrialPeriod_cannotBuyMoreShares(
        self,
    ):
        member = MemberWithCoopSharesFactory.create(
            add_coop_shares__quantity=3,
            add_coop_shares__valid_at=self.NOW + datetime.timedelta(days=1),
        )
        self.client.force_login(member)
        self.assertTrue(member.is_in_coop_trial())
        self.assertEqual(0, member.coop_shares_quantity)

        url = reverse("wirgarten:member_add_coop_shares", args=[member.id])
        data = {
            "cooperative_shares": 100,
            "statute_consent": True,
        }

        response = self.client.post(url, data=data, follow=True)

        self.assertStatusCode(response, 403)
        self.assertEqual(0, member.coop_shares_quantity)
