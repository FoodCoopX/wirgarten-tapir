from django.urls import reverse

from tapir.payments.config import IntendedUseTokens, PAYMENT_TYPE_COOP_SHARES
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PaymentFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPaymentIntendedUsePreviewCoopSharesApiView(TapirIntegrationTest):
    URL_NAME = "payments:intended_use_preview_coop_shares"

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls._set_parameter(key=ParameterKeys.COOP_SHARE_PRICE, value=75)

    def test_get_loggedInAsNormalMember_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        response = self.client.get(reverse(self.URL_NAME))

        self.assertStatusCode(response, 403)

    def test_get_loggedInAsAdmin_returns200(self):
        self._login_as_admin()

        response = self.client.get(reverse(self.URL_NAME))

        self.assertStatusCode(response, 200)

    def test_get_returnsTokenListWithCommonAndCoopShareTokens(self):
        self._login_as_admin()

        response = self.client.get(reverse(self.URL_NAME))

        self.assertStatusCode(response, 200)
        expected_tokens = sorted(IntendedUseTokens.COMMON_TOKENS) + sorted(
            IntendedUseTokens.COOP_SHARE_TOKENS
        )
        self.assertEqual(expected_tokens, response.json()["tokens"])

    def test_get_dbIsEmpty_responseContainsTwoFakeMembers(self):
        self._login_as_admin()

        response = self.client.get(
            reverse(self.URL_NAME)
            + "?pattern_old={anzahl_geno_anteile}&pattern_new={preis_einzelne_geno_anteil}"
        )

        self.assertStatusCode(response, 200)
        data = response.json()
        self.assertEqual("Maximilian", data["members"][0]["first_name"])
        self.assertEqual("John", data["members"][1]["first_name"])
        self.assertEqual("123", data["previews_old"][0])
        self.assertEqual("1", data["previews_old"][1])
        self.assertEqual("75,00", data["previews_new"][0])
        self.assertEqual("75,00", data["previews_new"][1])

    def test_get_invalidPattern_returnsErrorFieldNotEmpty(self):
        self._login_as_admin()
        too_long = "X" * 50

        response = self.client.get(
            reverse(self.URL_NAME) + f"?pattern_old={too_long}&pattern_new={too_long}"
        )

        self.assertStatusCode(response, 200)
        self.assertEqual(
            "Diese Zeile: 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX' ist zu lang wenn die Tokens expandiert sind.",
            response.json()["error"],
        )

    def test_get_realPaymentsExist_realPaymentIncludedInResponse(self):
        self._login_as_admin()
        payment = PaymentFactory.create(
            amount=225,
            type=PAYMENT_TYPE_COOP_SHARES,
        )

        response = self.client.get(
            reverse(self.URL_NAME)
            + "?pattern_old={vorname}&pattern_new={nachname} {anzahl_geno_anteile}"
        )

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertEqual(
            payment.mandate_ref.member.id, response_content["members"][2]["id"]
        )
        self.assertEqual(
            ["Maximilian", "John", payment.mandate_ref.member.first_name],
            response_content["previews_old"],
        )
        self.assertEqual(
            ["Mustermann 123", "Doe 1", f"{payment.mandate_ref.member.last_name} 3"],
            response_content["previews_new"],
        )
        self.assertEqual("", response_content["error"])
