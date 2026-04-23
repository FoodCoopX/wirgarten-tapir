import datetime
from decimal import Decimal

from django.urls import reverse

from tapir.payments.models import MemberCredit, MemberCreditAccountedLogEntry
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberCreditLogEntries(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self) -> None:
        super().setUp()
        MemberCredit.objects.bulk_create(
            [
                MemberCredit(
                    due_date=datetime.date(year=2025, month=1, day=1),
                    member=MemberFactory.create(),
                    amount=10,
                    purpose="p1",
                    comment="c1",
                ),
                MemberCredit(
                    due_date=datetime.date(year=2025, month=2, day=1),
                    member=MemberFactory.create(),
                    amount=20,
                    purpose="p2",
                    comment="c2",
                ),
                MemberCredit(
                    due_date=datetime.date(year=2026, month=1, day=1),
                    member=MemberFactory.create(),
                    amount=30,
                    purpose="p3",
                    comment="c3",
                ),
            ]
        )

    def test_get_normalMemberTriesToAccess_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        response = self.client.get(reverse("payments:credit_list_filtered"))

        self.assertStatusCode(response, 403)

    def test_get_adminUserTriesToAccess_returns200(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        response = self.client.get(reverse("payments:credit_list_filtered"))

        self.assertStatusCode(response, 200)

    def test_get_notFiltered_returnsAllCredits(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        response = self.client.get(reverse("payments:credit_list_filtered"))

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertEqual(3, len(response_content))

        self.assertEqual("c3", response_content[0]["credit"]["comment"])
        self.assertEqual("c2", response_content[1]["credit"]["comment"])
        self.assertEqual("c1", response_content[2]["credit"]["comment"])

    def test_get_filteredByMonth_returnsCorrectCredits(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        url = reverse("payments:credit_list_filtered")
        url = f"{url}?month_filter=1"
        response = self.client.get(url)

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertEqual(2, len(response_content))

        self.assertEqual("c3", response_content[0]["credit"]["comment"])
        self.assertEqual("c1", response_content[1]["credit"]["comment"])

    def test_get_filteredByYear_returnsCorrectCredits(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        url = reverse("payments:credit_list_filtered")
        url = f"{url}?year_filter=2025"
        response = self.client.get(url)

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertEqual(2, len(response_content))

        self.assertEqual("c2", response_content[0]["credit"]["comment"])
        self.assertEqual("c1", response_content[1]["credit"]["comment"])

    def test_get_showAllFalse_returnsOnlyUnaccountedCredits(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        credit = MemberCredit.objects.first()
        credit.accounted_on = datetime.datetime.now(datetime.timezone.utc)
        credit.save()

        url = reverse("payments:credit_list_filtered")
        url = f"{url}?show_all=false"
        response = self.client.get(url)

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertEqual(2, len(response_content))
        for item in response_content:
            self.assertIsNone(item["credit"].get("accountedOn"))

    def test_get_showAllTrue_returnsAllCredits(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        credit = MemberCredit.objects.first()
        credit.accounted_on = datetime.datetime.now(datetime.timezone.utc)
        credit.save()

        url = reverse("payments:credit_list_filtered")
        url = f"{url}?show_all=true"
        response = self.client.get(url)

        self.assertStatusCode(response, 200)
        response_content = response.json()
        self.assertEqual(3, len(response_content))


class TestMemberCreditAccountApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_normalMemberTriesToAccount_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        response = self.client.post(
            reverse("payments:member_credit_account"),
            data={"credit_ids": []},
            content_type="application/json",
        )

        self.assertStatusCode(response, 403)

    def test_post_accountCredits_booksTheCreditAndAddsLogEntry(self):
        admin_member = MemberFactory.create(is_superuser=True)
        member = MemberFactory.create()
        self.client.force_login(admin_member)

        credit = MemberCredit.objects.create(
            due_date=datetime.date(year=2025, month=1, day=1),
            member=member,
            amount=Decimal("50.00"),
            purpose="Test purpose",
            comment="Test comment",
        )

        self.assertIsNone(credit.accounted_on)

        url = reverse("payments:member_credit_account")
        response = self.client.post(
            url,
            data={"credit_ids": [credit.id]},
            content_type="application/json",
        )

        self.assertStatusCode(response, 200)
        self.assertIn("1 gebucht", response.json())

        credit.refresh_from_db()
        self.assertIsNotNone(credit.accounted_on)

        log_entries = MemberCreditAccountedLogEntry.objects.all()
        self.assertEqual(1, log_entries.count())
        db_log_entry = log_entries.first()
        self.assertEqual(member.email, db_log_entry.user.email)
        self.assertEqual(admin_member.email, db_log_entry.actor.email)
