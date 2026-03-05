import datetime
from decimal import Decimal

from django.urls import reverse
from rest_framework import status

from tapir.solidarity_contribution.models import (
    SolidarityContribution,
    SolidarityContributionChangedLogEntry,
)
from tapir.solidarity_contribution.tests.factories import SolidarityContributionFactory
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, GrowingPeriodFactory, NOW
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestUpdateMemberSolidarityContributionApiView(TapirIntegrationTest):
    CONTRACT_START_DATE = datetime.date(year=2023, month=3, day=20)

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls.growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2023, month=1, day=1)
        )

    def setUp(self) -> None:
        mock_timezone(self, NOW)

    def test_post_normalMemberUpdatesContributionFromOtherMember_returns403(self):
        user = MemberFactory.create(is_superuser=False)
        self.client.force_login(user)
        target = MemberFactory.create()

        response = self.client.post(
            reverse("solidarity_contribution:update_member_contribution"),
            data={"amount": 10, "member_id": target.id},
        )

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        self.assertFalse(SolidarityContribution.objects.exists())

    def test_post_normalMemberSendsNegativeValueWithoutPreviousContribution_returns400(
        self,
    ):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        response = self.client.post(
            reverse("solidarity_contribution:update_member_contribution"),
            data={"amount": -10, "member_id": member.id},
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(SolidarityContribution.objects.exists())

    def test_post_normalMemberSendsPositiveValueWithoutPreviousContribution_createsContribution(
        self,
    ):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        response = self.client.post(
            reverse("solidarity_contribution:update_member_contribution"),
            data={"amount": 10.65, "member_id": member.id},
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(1, SolidarityContribution.objects.count())
        contribution = SolidarityContribution.objects.get()
        self.assert_contribution_is_correct(
            contribution=contribution,
            member_id=member.id,
            amount=Decimal("10.65"),
            start_date=self.CONTRACT_START_DATE,
            end_date=self.growing_period.end_date,
        )

    def test_post_normalMemberSendsValueLowerThanCurrent_returns400(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)
        SolidarityContribution.objects.create(
            member=member,
            amount=10,
            start_date=self.growing_period.start_date,
            end_date=self.growing_period.end_date,
        )

        response = self.client.post(
            reverse("solidarity_contribution:update_member_contribution"),
            data={"amount": 9, "member_id": member.id},
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(1, SolidarityContribution.objects.count())
        self.assert_contribution_is_correct(
            contribution=SolidarityContribution.objects.get(),
            member_id=member.id,
            amount=Decimal("10"),
            start_date=self.growing_period.start_date,
            end_date=self.growing_period.end_date,
        )

    def test_post_normalMemberSendsValueHigherThanCurrent_createsContribution(
        self,
    ):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)
        SolidarityContribution.objects.create(
            member=member,
            amount=10,
            start_date=self.growing_period.start_date,
            end_date=self.growing_period.end_date,
        )

        response = self.client.post(
            reverse("solidarity_contribution:update_member_contribution"),
            data={"amount": 12, "member_id": member.id},
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(2, SolidarityContribution.objects.count())
        old_contribution, new_contribution = SolidarityContribution.objects.order_by(
            "start_date"
        )
        self.assert_contribution_is_correct(
            contribution=old_contribution,
            member_id=member.id,
            amount=Decimal("10"),
            start_date=self.growing_period.start_date,
            end_date=self.CONTRACT_START_DATE - datetime.timedelta(days=1),
        )

        self.assert_contribution_is_correct(
            contribution=new_contribution,
            member_id=member.id,
            amount=Decimal("12"),
            start_date=self.CONTRACT_START_DATE,
            end_date=self.growing_period.end_date,
        )

    def test_post_adminUpdatesValueToLower_createsContribution(self):
        target = MemberFactory.create(is_superuser=False)
        user = MemberFactory.create(is_superuser=True)
        self.client.force_login(user)

        SolidarityContribution.objects.create(
            member=target,
            amount=10,
            start_date=self.growing_period.start_date,
            end_date=self.growing_period.end_date,
        )

        response = self.client.post(
            reverse("solidarity_contribution:update_member_contribution"),
            data={"amount": -1, "member_id": target.id},
        )

        self.assertStatusCode(response, status.HTTP_200_OK)

        self.assertEqual(2, SolidarityContribution.objects.count())
        old_contribution, new_contribution = SolidarityContribution.objects.order_by(
            "start_date"
        )
        self.assert_contribution_is_correct(
            contribution=old_contribution,
            member_id=target.id,
            amount=Decimal("10"),
            start_date=self.growing_period.start_date,
            end_date=self.CONTRACT_START_DATE - datetime.timedelta(days=1),
        )

        self.assert_contribution_is_correct(
            contribution=new_contribution,
            member_id=target.id,
            amount=Decimal("-1"),
            start_date=self.CONTRACT_START_DATE,
            end_date=self.growing_period.end_date,
        )

    def test_post_newValueIsZero_dontCreateANewContribution(self):
        target = MemberFactory.create(is_superuser=False)
        user = MemberFactory.create(is_superuser=True)
        self.client.force_login(user)

        SolidarityContribution.objects.create(
            member=target,
            amount=-5,
            start_date=self.growing_period.start_date,
            end_date=self.growing_period.end_date,
        )

        response = self.client.post(
            reverse("solidarity_contribution:update_member_contribution"),
            data={"amount": 0, "member_id": target.id},
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(1, SolidarityContribution.objects.count())
        old_contribution = SolidarityContribution.objects.get()
        self.assert_contribution_is_correct(
            contribution=old_contribution,
            member_id=target.id,
            amount=Decimal("-5"),
            start_date=self.growing_period.start_date,
            end_date=self.CONTRACT_START_DATE - datetime.timedelta(days=1),
        )

    def test_post_futureContributionExists_futureContributionDeleted(self):
        target = MemberFactory.create(is_superuser=False)
        user = MemberFactory.create(is_superuser=True)
        self.client.force_login(user)

        SolidarityContribution.objects.create(
            member=target,
            amount=10,
            start_date=self.growing_period.start_date,
            end_date=self.growing_period.end_date,
        )
        SolidarityContribution.objects.create(
            member=target,
            amount=15,
            start_date=self.growing_period.start_date.replace(
                year=self.growing_period.start_date.year + 1
            ),
            end_date=self.growing_period.end_date.replace(
                year=self.growing_period.end_date.year + 1
            ),
        )

        response = self.client.post(
            reverse("solidarity_contribution:update_member_contribution"),
            data={"amount": -1, "member_id": target.id},
        )

        self.assertStatusCode(response, status.HTTP_200_OK)

        self.assertEqual(2, SolidarityContribution.objects.count())
        old_contribution, new_contribution = SolidarityContribution.objects.order_by(
            "start_date"
        )
        self.assert_contribution_is_correct(
            contribution=old_contribution,
            member_id=target.id,
            amount=Decimal("10"),
            start_date=self.growing_period.start_date,
            end_date=self.CONTRACT_START_DATE - datetime.timedelta(days=1),
        )

        self.assert_contribution_is_correct(
            contribution=new_contribution,
            member_id=target.id,
            amount=Decimal("-1"),
            start_date=self.CONTRACT_START_DATE,
            end_date=self.growing_period.end_date,
        )

    def assert_contribution_is_correct(
        self,
        contribution: SolidarityContribution,
        member_id: str,
        amount: Decimal,
        start_date: datetime.date,
        end_date: datetime.date,
    ):
        self.assertEqual(member_id, contribution.member_id)
        self.assertEqual(amount, contribution.amount)
        self.assertEqual(start_date, contribution.start_date)
        self.assertEqual(end_date, contribution.end_date)

    def test_post_onlyFutureContributionExistsAndStartContributionNow_futureContributionDeletedAndNewContributionStartsNow(
        self,
    ):
        target = MemberFactory.create(is_superuser=False)
        user = MemberFactory.create(is_superuser=True)
        self.client.force_login(user)

        SolidarityContribution.objects.create(
            member=target,
            amount=15,
            start_date=self.growing_period.start_date.replace(
                year=self.growing_period.start_date.year + 1
            ),
            end_date=self.growing_period.end_date.replace(
                year=self.growing_period.end_date.year + 1
            ),
        )

        response = self.client.post(
            reverse("solidarity_contribution:update_member_contribution"),
            data={"amount": -1, "member_id": target.id, "start_contribution_now": True},
        )

        self.assertStatusCode(response, status.HTTP_200_OK)

        self.assertEqual(1, SolidarityContribution.objects.count())
        new_contribution = SolidarityContribution.objects.get()

        self.assert_contribution_is_correct(
            contribution=new_contribution,
            member_id=target.id,
            amount=Decimal("-1"),
            start_date=self.CONTRACT_START_DATE,
            end_date=self.growing_period.end_date,
        )

    def test_post_onlyFutureContributionExistsAndDontStartContributionNow_futureContributionDeletedAndNewContributionStartsAtDateOfPreviousContribution(
        self,
    ):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        SolidarityContributionFactory.create(
            member=member,
            amount=15,
            start_date=datetime.date(year=2023, month=6, day=22),
        )

        response = self.client.post(
            reverse("solidarity_contribution:update_member_contribution"),
            data={
                "amount": 17,
                "member_id": member.id,
                "start_contribution_now": False,
            },
        )

        self.assertStatusCode(response, status.HTTP_200_OK)

        self.assertEqual(1, SolidarityContribution.objects.count())
        new_contribution = SolidarityContribution.objects.get()

        self.assert_contribution_is_correct(
            contribution=new_contribution,
            member_id=member.id,
            amount=Decimal("17"),
            start_date=datetime.date(year=2023, month=6, day=22),
            end_date=self.growing_period.end_date,
        )

        self.assertEqual(1, SolidarityContributionChangedLogEntry.objects.count())
        log_entry = SolidarityContributionChangedLogEntry.objects.get()
        self.assertEqual(member.email, log_entry.user.email)
        self.assertEqual(member.email, log_entry.actor.email)
        self.assertEqual(Decimal(15), log_entry.old_contribution_amount)
        self.assertEqual(Decimal(17), log_entry.new_contribution_amount)
