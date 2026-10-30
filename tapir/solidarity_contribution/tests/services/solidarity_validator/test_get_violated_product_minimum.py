import datetime
from decimal import Decimal
from unittest.mock import Mock, patch

from tapir.accounts.models import TapirUser
from tapir.solidarity_contribution.services.solidarity_validator import (
    SolidarityValidator,
)
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(
    SolidarityValidator, "get_product_solidarity_minimum_for_member", autospec=True
)
class TestGetViolatedProductMinimum(TapirUnitTest):
    def call(self, user: TapirUser, new_amount: Decimal, cache: dict | None = None):
        return SolidarityValidator.get_violated_product_minimum(
            logged_in_user=user,
            target_member_id="test_member_id",
            new_amount=new_amount,
            change_date=datetime.date(year=2025, month=6, day=1),
            cache=cache if cache is not None else {},
        )

    def test_getViolatedProductMinimum_userIsAdmin_returnsNone(
        self, mock_get_minimum: Mock
    ):
        mock_get_minimum.return_value = -10

        result = self.call(
            user=MemberFactory.build(is_superuser=True), new_amount=Decimal(-15)
        )

        self.assertIsNone(result)
        mock_get_minimum.assert_not_called()

    def test_getViolatedProductMinimum_amountBelowMinimum_returnsMinimum(
        self, mock_get_minimum: Mock
    ):
        mock_get_minimum.return_value = -10
        cache = {}

        result = self.call(
            user=MemberFactory.build(is_superuser=False),
            new_amount=Decimal(-15),
            cache=cache,
        )

        self.assertEqual(-10, result)
        mock_get_minimum.assert_called_once_with(
            member_id="test_member_id",
            reference_date=datetime.date(year=2025, month=6, day=1),
            cache=cache,
        )

    def test_getViolatedProductMinimum_amountEqualsMinimum_returnsNone(
        self, mock_get_minimum: Mock
    ):
        mock_get_minimum.return_value = -10.5

        result = self.call(
            user=MemberFactory.build(is_superuser=False), new_amount=Decimal("-10.5")
        )

        self.assertIsNone(result)

    def test_getViolatedProductMinimum_noProductMinimum_returnsNone(
        self, mock_get_minimum: Mock
    ):
        mock_get_minimum.return_value = None

        result = self.call(
            user=MemberFactory.build(is_superuser=False), new_amount=Decimal(-100)
        )

        self.assertIsNone(result)
