import datetime

from django.urls import reverse

from tapir.deliveries.tests.factories import JokerFactory
from tapir.payments.config import IntendedUseTokens
from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    ProductPriceFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestCreditIntendedUsePreviewJokerApiView(TapirIntegrationTest):
    URL_NAME = "payments:intended_use_preview_joker"

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_loggedInAsNormalMember_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        response = self.client.get(reverse(self.URL_NAME))

        self.assertStatusCode(response, 403)

    def test_get_loggedInAsAdmin_returns200(self):
        self._login_as_admin()

        response = self.client.get(reverse(self.URL_NAME))

        self.assertStatusCode(response, 200)

    def test_get_dbIsEmpty_responseContainsTwoFakeMembers(self):
        self._login_as_admin()

        response = self.client.get(
            reverse(self.URL_NAME) + "?pattern_old={vorname}&pattern_new={vorname}"
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
            reverse(self.URL_NAME) + f"?pattern_old={too_long}&pattern_new={too_long}"
        )

        self.assertStatusCode(response, 200)
        data = response.json()
        self.assertEqual(
            "Diese Zeile: 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX' ist zu lang wenn die Tokens expandiert sind.",
            data["error"],
        )

    def test_get_default_returnsTokenListWithCommonAndJokerTokens(self):
        self._login_as_admin()

        response = self.client.get(reverse(self.URL_NAME))

        self.assertStatusCode(response, 200)
        expected_tokens = sorted(IntendedUseTokens.COMMON_TOKENS) + sorted(
            IntendedUseTokens.JOKER_TOKENS
        )
        self.assertEqual(expected_tokens, response.json()["tokens"])

    def test_get_realJokerExist_realPaymentIncludedInResponse(self):
        mock_timezone(test=self, now=datetime.datetime(2026, 6, 1))
        self._login_as_admin()

        period = GrowingPeriodFactory.create(
            start_date=datetime.date(2026, 6, 1),
            end_date=datetime.date(2027, 5, 31),
        )
        member = MemberFactory.create(first_name="Julius", last_name="Caesar")
        subscription = SubscriptionFactory.create(
            member=member, period=period, product__type__delivery_cycle=WEEKLY[0]
        )
        ProductPriceFactory.create(
            product=subscription.product,
            valid_from=datetime.date(2026, 1, 1),
            price=100,
        )
        JokerFactory.create(member=member, date=datetime.date(2026, 6, 1))
        JokerFactory.create(member=member, date=datetime.date(2026, 7, 1))
        JokerFactory.create(member=member, date=datetime.date(2026, 8, 1))

        response = self.client.get(
            reverse(self.URL_NAME)
            + "?pattern_old={vorname}&pattern_new={anzahl_an_joker};{wert_der_joker};{daten_der_joker}"
        )

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertEqual(
            ["Maximilian", "John", "Julius"], response_content["previews_old"]
        )
        self.assertEqual(
            [
                "3;50,42€ * 2;01.06.2026 - 1",
                "3;50,42€ * 2;01.06.2026 - 1",
                "3;67,92€ * 3;01.06.2026 - 0",
            ],
            response_content["previews_new"],
        )
        self.assertEqual("", response_content["error"])
        self.assertEqual(member.id, response_content["members"][2]["id"])
