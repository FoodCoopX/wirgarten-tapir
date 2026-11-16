import datetime

from django.urls import reverse

from tapir.payments.tests.factories import PaymentExportExclusionPeriodFactory
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPaymentExportExclusionPeriodApiViewGet(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_loggedInAsNormalMember_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        response = self.client.get(
            reverse("payments:payment_export_exclusion_periods"),
            query_params={"member_id": member.id},
        )

        self.assertStatusCode(response, 403)

    def test_get_default_returnsPeriodsOfMemberSortedByStartDate(self):
        self._login_as_admin()
        member = MemberFactory.create()
        later_period = PaymentExportExclusionPeriodFactory.create(
            member=member,
            start_date=datetime.date(year=2026, month=6, day=1),
            end_date=None,
            comment="later",
        )
        earlier_period = PaymentExportExclusionPeriodFactory.create(
            member=member,
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=3, day=31),
            comment="earlier",
        )
        PaymentExportExclusionPeriodFactory.create()

        response = self.client.get(
            reverse("payments:payment_export_exclusion_periods"),
            query_params={"member_id": member.id},
        )

        self.assertStatusCode(response, 200)
        self.assertEqual(
            [
                {
                    "id": earlier_period.id,
                    "start_date": "2026-01-01",
                    "end_date": "2026-03-31",
                    "comment": "earlier",
                },
                {
                    "id": later_period.id,
                    "start_date": "2026-06-01",
                    "end_date": None,
                    "comment": "later",
                },
            ],
            response.json(),
        )
