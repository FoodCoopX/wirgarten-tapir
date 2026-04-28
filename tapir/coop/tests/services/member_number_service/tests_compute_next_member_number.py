from unittest.mock import patch

from django.test import SimpleTestCase

from tapir.coop.services.member_number_service import MemberNumberService
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys


class TestComputeNextMemberNumber(SimpleTestCase):
    @patch.object(Member.objects, "aggregate", autospec=True)
    def test_computeNextMemberNumber_noExistingMembers_returnsStartValue(
        self, mock_aggregate
    ):
        cache = {}
        mock_parameter_value(
            cache=cache, key=ParameterKeys.MEMBER_NUMBER_START_VALUE, value=1000
        )
        mock_aggregate.return_value = {"member_no__max": None}

        self.assertEqual(
            1000, MemberNumberService.compute_next_member_number(cache=cache)
        )

    @patch.object(Member.objects, "aggregate", autospec=True)
    def test_computeNextMemberNumber_existingMemberBelowStartValue_returnsStartValue(
        self, mock_aggregate
    ):
        cache = {}
        mock_parameter_value(
            cache=cache, key=ParameterKeys.MEMBER_NUMBER_START_VALUE, value=1000
        )
        mock_aggregate.return_value = {"member_no__max": 500}

        self.assertEqual(
            1000, MemberNumberService.compute_next_member_number(cache=cache)
        )

    @patch.object(Member.objects, "aggregate", autospec=True)
    def test_computeNextMemberNumber_existingMemberAboveStartValue_returnsMaxPlusOne(
        self, mock_aggregate
    ):
        cache = {}
        mock_parameter_value(
            cache=cache, key=ParameterKeys.MEMBER_NUMBER_START_VALUE, value=1
        )
        mock_aggregate.return_value = {"member_no__max": 42}

        self.assertEqual(
            43, MemberNumberService.compute_next_member_number(cache=cache)
        )
