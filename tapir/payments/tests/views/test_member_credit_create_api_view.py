import datetime
from decimal import Decimal

from django.urls import reverse

from tapir.payments.models import MemberCredit
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberCreditListApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_normalMemberTriesToAccess_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        response = self.client.post(reverse("payments:member_credit_create"))

        self.assertStatusCode(response, 403)

    def test_get_adminUserTriesToAccess_returns200(self):
        user = MemberFactory.create(is_superuser=True)
        target = MemberFactory.create()
        self.client.force_login(user)

        data = {
            "due_date": "2019-7-28",
            "member_id": target.id,
            "amount": 127.76,
            "purpose": "test purpose",
            "comment": "test comment",
        }
        response = self.client.post(reverse("payments:member_credit_create"), data=data)

        self.assertStatusCode(response, 200)

        self.assertEqual(1, MemberCredit.objects.count())
        member_credit = MemberCredit.objects.get()
        self.assertEqual(Decimal("127.76"), member_credit.amount)
        self.assertEqual(target.id, member_credit.member_id)
        self.assertEqual(
            datetime.date(year=2019, month=7, day=28), member_credit.due_date
        )
        self.assertEqual("test purpose", member_credit.purpose)
        self.assertEqual("test comment", member_credit.comment)
