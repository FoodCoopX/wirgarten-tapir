import datetime

from django.urls import reverse
from icecream import ic

from tapir.payments.config import IntendedUseTokens
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    PaymentFactory,
    ProductFactory,
    ProductPriceFactory,
    ProductTypeFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone

URL_NAME = "payments:intended_use_preview_contracts"


class TestPaymentIntendedUsePreviewContractsApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        product_type = ProductTypeFactory.create(name="ProductType")
        ProductFactory.create(name="ProductA", type=product_type)
        ProductFactory.create(name="ProductB", type=product_type)

    def _login_as_admin(self):
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)
        return admin

    def test_get_loggedInAsNormalMember_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        response = self.client.get(reverse(URL_NAME))

        self.assertStatusCode(response, 403)

    def test_get_loggedInAsAdmin_returns200(self):
        self._login_as_admin()

        response = self.client.get(reverse(URL_NAME))

        self.assertStatusCode(response, 200)

    def test_get_dbIsEmpty_responseContainsTwoFakeMembers(self):
        self._login_as_admin()

        response = self.client.get(
            reverse(URL_NAME) + "?pattern_old={vorname}&pattern_new={vorname}"
        )

        self.assertStatusCode(response, 200)
        data = response.json()
        self.assertEqual("Maximilian", data["members"][0]["first_name"])
        self.assertEqual("John", data["members"][1]["first_name"])
        self.assertEqual(["Maximilian", "John"], data["previews_old"])
        self.assertEqual(["Maximilian", "John"], data["previews_new"])

    def test_get_patternIsTooLong_returnsError(self):
        self._login_as_admin()
        too_long = "X" * 50

        response = self.client.get(
            reverse(URL_NAME) + f"?pattern_old={too_long}&pattern_new={too_long}"
        )

        self.assertStatusCode(response, 200)
        data = response.json()
        ic(data)
        self.assertEqual(
            "Diese Zeile: 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX' ist zu lang wenn die Tokens expandiert sind.",
            data["error"],
        )

    def test_get_default_returnsTokenListWithCommonAndContractTokens(self):
        self._login_as_admin()

        response = self.client.get(reverse(URL_NAME))

        self.assertStatusCode(response, 200)
        expected_tokens = sorted(IntendedUseTokens.COMMON_TOKENS) + sorted(
            IntendedUseTokens.CONTRACT_TOKENS
        )
        self.assertEqual(expected_tokens, response.json()["tokens"])

    def test_get_realPaymentsExist_realPaymentIncludedInResponse(self):
        mock_timezone(test=self, now=datetime.datetime(2026, 6, 1))
        self._login_as_admin()

        period = GrowingPeriodFactory.create(
            start_date=datetime.date(2026, 6, 1),
            end_date=datetime.date(2027, 5, 31),
        )
        member = MemberFactory.create(first_name="Julius", last_name="Caesar")
        subscription = SubscriptionFactory.create(
            member=member,
            period=period,
        )
        ProductPriceFactory.create(
            product=subscription.product,
            valid_from=datetime.date(2026, 1, 1),
            price=10,
        )
        payment = PaymentFactory.create(
            mandate_ref__member=member,
            due_date=datetime.date(2026, 6, 15),
            subscription_payment_range_start=datetime.date(2026, 6, 1),
            subscription_payment_range_end=datetime.date(2026, 6, 30),
        )

        response = self.client.get(
            reverse(URL_NAME) + "?pattern_old={vorname}&pattern_new={nachname}"
        )

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertEqual(
            ["Maximilian", "John", "Julius"], response_content["previews_old"]
        )
        self.assertEqual(
            ["Mustermann", "Doe", "Caesar"], response_content["previews_new"]
        )
        self.assertEqual("", response_content["error"])
        self.assertEqual(member.id, response_content["members"][2]["id"])
