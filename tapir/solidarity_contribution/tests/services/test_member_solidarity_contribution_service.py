import datetime
from decimal import Decimal
from unittest.mock import Mock, patch

from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.solidarity_contribution.services.member_solidarity_contribution_service import (
    MemberSolidarityContributionService,
)
from tapir.solidarity_contribution.tests.factories import SolidarityContributionFactory
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, GrowingPeriodFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberSolidarityContributionService(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_getMemberContribution_memberHasAContribution_returnsCorrectContribution(
        self,
    ):
        member = MemberFactory.create()
        SolidarityContributionFactory.create(
            member=member,
            start_date=datetime.date(year=2023, month=1, day=1),
            end_date=datetime.date(year=2023, month=1, day=31),
            amount=10,
        )
        SolidarityContributionFactory.create(
            member=member,
            start_date=datetime.date(year=2023, month=2, day=1),
            end_date=datetime.date(year=2023, month=2, day=28),
            amount=20,
        )
        SolidarityContributionFactory.create(
            member=member,
            start_date=datetime.date(year=2023, month=3, day=1),
            end_date=datetime.date(year=2023, month=3, day=31),
            amount=30,
        )

        contribution = MemberSolidarityContributionService.get_member_contribution(
            member_id=member.id,
            reference_date=datetime.date(year=2023, month=2, day=15),
            cache={},
        )

        self.assertEqual(Decimal(20), contribution)

    def test_getMemberContribution_memberHasNoCurrentContribution_returnsZero(
        self,
    ):
        member = MemberFactory.create()
        SolidarityContributionFactory.create(
            member=member,
            start_date=datetime.date(year=2023, month=1, day=1),
            end_date=datetime.date(year=2023, month=1, day=31),
            amount=10,
        )
        SolidarityContributionFactory.create(
            member=member,
            start_date=datetime.date(year=2023, month=3, day=1),
            end_date=datetime.date(year=2023, month=3, day=31),
            amount=30,
        )

        contribution = MemberSolidarityContributionService.get_member_contribution(
            member_id=member.id,
            reference_date=datetime.date(year=2023, month=2, day=15),
            cache={},
        )

        self.assertEqual(Decimal(0), contribution)

    def test_getMemberContribution_memberHasNoContributionAtAll_returnsZero(
        self,
    ):
        member = MemberFactory.create()

        contribution = MemberSolidarityContributionService.get_member_contribution(
            member_id=member.id,
            reference_date=datetime.date(year=2023, month=2, day=15),
            cache={},
        )

        self.assertEqual(Decimal(0), contribution)

    def test_assignContributionToMember_amountIsZero_doesntCreateContribution(self):
        member = MemberFactory.create()

        MemberSolidarityContributionService.assign_contribution_to_member(
            member_id=member.id,
            change_date=datetime.date(year=2024, month=1, day=1),
            amount=0,
            cache={},
        )

        self.assertFalse(SolidarityContribution.objects.exists())

    def test_assignContributionToMember_default_createsCorrectContributionAndCancelsPreviousContributions(
        self,
    ):
        GrowingPeriodFactory.create(start_date=datetime.date(year=2024, month=1, day=1))
        member = MemberFactory.create()
        past_contribution = SolidarityContributionFactory.create(
            member=member,
            amount=10,
            start_date=datetime.date(year=2023, month=1, day=1),
            end_date=datetime.date(year=2023, month=12, day=31),
        )
        current_contribution = SolidarityContributionFactory.create(
            member=member,
            amount=15,
            start_date=datetime.date(year=2024, month=1, day=1),
            end_date=datetime.date(year=2024, month=12, day=31),
        )
        future_contribution = SolidarityContributionFactory.create(
            member=member,
            amount=20,
            start_date=datetime.date(year=2025, month=1, day=1),
            end_date=datetime.date(year=2025, month=12, day=31),
        )

        MemberSolidarityContributionService.assign_contribution_to_member(
            member_id=member.id,
            change_date=datetime.date(year=2024, month=6, day=1),
            amount=17,
            cache={},
        )

        self.assertEqual(3, SolidarityContribution.objects.count())

        # past contribution didn't change
        past_contribution.refresh_from_db()
        self.assertEqual(Decimal(10), past_contribution.amount)
        self.assertEqual(
            datetime.date(year=2023, month=1, day=1), past_contribution.start_date
        )
        self.assertEqual(
            datetime.date(year=2023, month=12, day=31), past_contribution.end_date
        )

        # current contribution got cut
        current_contribution.refresh_from_db()
        self.assertEqual(Decimal(15), current_contribution.amount)
        self.assertEqual(
            datetime.date(year=2024, month=1, day=1), current_contribution.start_date
        )
        self.assertEqual(
            datetime.date(year=2024, month=5, day=31), current_contribution.end_date
        )

        # future contribution is deleted
        self.assertFalse(
            SolidarityContribution.objects.filter(id=future_contribution.id).exists()
        )

        # new contribution is correct
        new_contribution = SolidarityContribution.objects.exclude(
            id__in=[past_contribution.id, current_contribution.id]
        ).get()
        self.assertEqual(Decimal(17), new_contribution.amount)
        self.assertEqual(
            datetime.date(year=2024, month=6, day=1), new_contribution.start_date
        )
        self.assertEqual(
            datetime.date(year=2024, month=12, day=31), new_contribution.end_date
        )

    def test_assignContributionToMember_noCurrentGrowingPeriod_useFutureGrowingPeriodAsEndDate(
        self,
    ):
        GrowingPeriodFactory.create(start_date=datetime.date(year=2025, month=2, day=1))
        member = MemberFactory.create()

        MemberSolidarityContributionService.assign_contribution_to_member(
            member_id=member.id,
            change_date=datetime.date(year=2024, month=6, day=1),
            amount=17,
            cache={},
        )

        self.assertEqual(1, SolidarityContribution.objects.count())
        new_contribution = SolidarityContribution.objects.get()
        self.assertEqual(Decimal(17), new_contribution.amount)
        self.assertEqual(
            datetime.date(year=2024, month=6, day=1), new_contribution.start_date
        )
        self.assertEqual(
            datetime.date(year=2025, month=1, day=31), new_contribution.end_date
        )

    @patch.object(MemberSolidarityContributionService, "get_member_contribution")
    def test_isUserAllowedToChangeContribution_userIsAdmin_returnsTrue(
        self, mock_get_member_contribution: Mock
    ):
        member = MemberFactory.create(is_superuser=True)

        result = (
            MemberSolidarityContributionService.is_user_allowed_to_change_contribution(
                logged_in_user=member,
                target_member_id=Mock(),
                new_amount=Decimal(-1000),
                change_date=Mock(),
                cache=Mock(),
            )
        )

        self.assertTrue(result)
        mock_get_member_contribution.assert_not_called()

    def test_isUserAllowedToChangeContribution_userIsNotAdminAndNewContributionIsHigherThanCurrent_returnsTrue(
        self,
    ):
        member = MemberFactory.create(is_superuser=False)
        SolidarityContributionFactory.create(
            member=member,
            amount=10,
            start_date=datetime.date(year=2020, month=1, day=1),
        )

        result = (
            MemberSolidarityContributionService.is_user_allowed_to_change_contribution(
                logged_in_user=member,
                target_member_id=member.id,
                new_amount=Decimal(11),
                change_date=datetime.date(year=2020, month=1, day=3),
                cache={},
            )
        )

        self.assertTrue(result)

    def test_isUserAllowedToChangeContribution_userIsNotAdminButNewContributionIsLowerThanCurrent_returnsFalse(
        self,
    ):
        member = MemberFactory.create(is_superuser=False)
        SolidarityContributionFactory.create(
            member=member,
            amount=10,
            start_date=datetime.date(year=2020, month=1, day=1),
        )

        result = (
            MemberSolidarityContributionService.is_user_allowed_to_change_contribution(
                logged_in_user=member,
                target_member_id=member.id,
                new_amount=Decimal(9),
                change_date=datetime.date(year=2020, month=1, day=3),
                cache={},
            )
        )

        self.assertFalse(result)
