import datetime

from django.urls import reverse

from tapir.payments.tests.factories import PaymentExportExclusionPeriodFactory
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestPaymentExportExclusionPeriodOverviewApiViewGet(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls._set_parameter(
            key=ParameterKeys.PAYMENT_EXPORT_EXCLUSION_ENABLED, value=True
        )

    def setUp(self) -> None:
        super().setUp()
        mock_timezone(test=self, now=datetime.datetime(year=2026, month=6, day=15))

    def test_get_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))

        response = self._get()

        self.assertStatusCode(response, 403)

    def test_get_featureDisabled_returns403(self):
        self._login_as_admin()
        self._set_parameter(
            key=ParameterKeys.PAYMENT_EXPORT_EXCLUSION_ENABLED, value=False
        )

        response = self._get()

        self.assertStatusCode(response, 403)

    def test_get_default_returnsCurrentAndFuturePeriodsSortedByStartDate(self):
        self._login_as_admin()
        self._create_period(
            last_name="Expired",
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=5, day=31),
        )
        future_period = self._create_period(
            last_name="Future",
            start_date=datetime.date(year=2026, month=9, day=1),
            end_date=None,
        )
        current_period = self._create_period(
            last_name="Current",
            start_date=datetime.date(year=2026, month=6, day=1),
            end_date=datetime.date(year=2026, month=6, day=30),
        )

        response = self._get()

        self.assertStatusCode(response, 200)
        self.assertEqual(
            [
                (current_period.id, "Current", True),
                (future_period.id, "Future", False),
            ],
            [
                (row["id"], row["last_name"], row["is_active"])
                for row in response.json()["results"]
            ],
        )

    def test_get_includeExpired_alsoReturnsExpiredPeriods(self):
        self._login_as_admin()
        expired_period = self._create_period(
            last_name="Expired",
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=5, day=31),
        )
        current_period = self._create_period(
            last_name="Current",
            start_date=datetime.date(year=2026, month=6, day=1),
            end_date=None,
        )

        response = self._get(include_expired=True)

        self.assertStatusCode(response, 200)
        self.assertEqual(
            [(expired_period.id, False), (current_period.id, True)],
            [(row["id"], row["is_active"]) for row in response.json()["results"]],
        )

    def test_get_sameStartDate_sortedByMemberName(self):
        self._login_as_admin()
        start_date = datetime.date(year=2026, month=6, day=1)
        self._create_period(last_name="Zimmer", start_date=start_date, end_date=None)
        self._create_period(last_name="Adler", start_date=start_date, end_date=None)

        response = self._get()

        self.assertEqual(
            ["Adler", "Zimmer"],
            [row["last_name"] for row in response.json()["results"]],
        )

    def test_get_default_returnsMemberData(self):
        self._login_as_admin()
        member = MemberFactory.create(
            member_no=42, first_name="Ada", last_name="Lovelace"
        )
        PaymentExportExclusionPeriodFactory.create(
            member=member,
            start_date=datetime.date(year=2026, month=6, day=1),
            end_date=None,
            comment="Kredit",
        )

        response = self._get()

        row = response.json()["results"][0]
        self.assertEqual(42, row["member_no"])
        self.assertEqual("Ada", row["first_name"])
        self.assertEqual("Lovelace", row["last_name"])
        self.assertEqual(member.get_absolute_url(), row["member_url"])
        self.assertEqual("2026-06-01", row["start_date"])
        self.assertIsNone(row["end_date"])
        self.assertEqual("Kredit", row["comment"])

    def test_get_moreRowsThanLimit_returnsRequestedPageAndTotalCount(self):
        self._login_as_admin()
        periods = [
            self._create_period(
                last_name=f"Member{index}",
                start_date=datetime.date(year=2026, month=month, day=1),
                end_date=None,
            )
            for index, month in enumerate([7, 8, 9])
        ]

        response = self._get(limit=2, offset=2)

        self.assertStatusCode(response, 200)
        self.assertEqual(3, response.json()["count"])
        self.assertEqual(
            [periods[2].id], [row["id"] for row in response.json()["results"]]
        )

    @staticmethod
    def _create_period(
        last_name: str,
        start_date: datetime.date,
        end_date: datetime.date | None,
    ):
        return PaymentExportExclusionPeriodFactory.create(
            member=MemberFactory.create(last_name=last_name),
            start_date=start_date,
            end_date=end_date,
        )

    def _get(self, include_expired: bool = False, limit: int = 10, offset: int = 0):
        query_params = {"limit": limit, "offset": offset}
        if include_expired:
            query_params["include_expired"] = "true"
        return self.client.get(
            reverse("payments:payment_export_exclusion_periods_overview"),
            query_params=query_params,
        )
