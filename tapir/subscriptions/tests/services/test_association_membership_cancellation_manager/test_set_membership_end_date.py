import datetime
from unittest.mock import patch, Mock

from tapir.associations.models import (
    AssociationMembership,
    AssociationMembershipUpdatedLogEntry,
)
from tapir.associations.services.association_membership_cancellation_manager import (
    AssociationMembershipCancellationManager,
)
from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest, mock_timezone


class TestSetMembershipEndDate(TapirUnitTest):
    @patch.object(AssociationMembershipUpdatedLogEntry, "populate", autospec=True)
    @patch.object(AssociationMembership, "save", autospec=True)
    def test_setMembershipEndDate_default_setsEndDateAndCreatesLogEntry(
        self, mock_membership_save: Mock, mock_populate: Mock
    ):
        now = mock_timezone(
            test=self, now=datetime.datetime(year=2019, month=6, day=12)
        )
        membership = AssociationMembershipFactory.build(
            end_date=None, cancellation_ts=None
        )
        actor = Mock()
        cache = Mock()
        end_date = datetime.date(year=2019, month=12, day=31)

        AssociationMembershipCancellationManager._set_membership_end_date(
            membership=membership,
            end_date=end_date,
            actor=actor,
            cache=cache,
        )

        membership.end_date = end_date
        membership.cancellation_ts = now
        mock_membership_save.assert_called_once()

        mock_populate.assert_called_once()
        mock_populate.return_value.save.assert_called_once_with()
