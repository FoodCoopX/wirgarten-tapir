import datetime
from unittest.mock import Mock, patch

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.deliveries.config import (
    DELIVERY_DONATION_MODE_DISABLED,
    DELIVERY_DONATION_MODE_ALWAYS_POSSIBLE,
)
from tapir.deliveries.services.delivery_donation_manager import DeliveryDonationManager
from tapir.deliveries.tests.factories import DeliveryDonationFactory
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.factories import MemberFactory


class TestDoesMemberHaveADonationInWeek(TapirUnitTest):
    def test_doesMemberHaveADonationInWeek_donationsAreDisabled_returnsFalse(self):
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.DELIVERY_DONATION_MODE,
            value=DELIVERY_DONATION_MODE_DISABLED,
        )

        result = DeliveryDonationManager.does_member_have_a_donation_in_week(
            member=Mock(), reference_date=Mock(), cache=cache
        )

        self.assertFalse(result)

    @patch.object(TapirCache, "get_all_delivery_donations_for_member", autospec=True)
    def test_doesMemberHaveADonationInWeek_noDonationOnGivenDate_returnsFalse(
        self, mock_get_all_delivery_donations_for_member: Mock
    ):
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.DELIVERY_DONATION_MODE,
            value=DELIVERY_DONATION_MODE_ALWAYS_POSSIBLE,
        )

        member = MemberFactory.build()
        donations = [
            DeliveryDonationFactory.build(
                member=member, date=datetime.date(year=2026, month=1, day=1)
            ),
            DeliveryDonationFactory.build(
                member=member, date=datetime.date(year=2026, month=2, day=1)
            ),
        ]
        mock_get_all_delivery_donations_for_member.return_value = donations

        result = DeliveryDonationManager.does_member_have_a_donation_in_week(
            member=member,
            reference_date=datetime.date(year=2026, month=1, day=15),
            cache=cache,
        )

        self.assertFalse(result)
        mock_get_all_delivery_donations_for_member.assert_called_once_with(
            member_id=member.id, cache=cache
        )

    @patch.object(TapirCache, "get_all_delivery_donations_for_member", autospec=True)
    def test_doesMemberHaveADonationInWeek_donationOnGivenDateExists_returnsTrue(
        self, mock_get_all_delivery_donations_for_member: Mock
    ):
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.DELIVERY_DONATION_MODE,
            value=DELIVERY_DONATION_MODE_ALWAYS_POSSIBLE,
        )

        member = MemberFactory.build()
        donations = [
            DeliveryDonationFactory.build(
                member=member, date=datetime.date(year=2026, month=1, day=17)
            ),
            DeliveryDonationFactory.build(
                member=member, date=datetime.date(year=2026, month=2, day=1)
            ),
        ]
        mock_get_all_delivery_donations_for_member.return_value = donations

        result = DeliveryDonationManager.does_member_have_a_donation_in_week(
            member=member,
            reference_date=datetime.date(year=2026, month=1, day=13),
            cache=cache,
        )

        self.assertTrue(result)
        mock_get_all_delivery_donations_for_member.assert_called_once_with(
            member_id=member.id, cache=cache
        )
