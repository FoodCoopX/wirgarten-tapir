import datetime

from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.core.services.active_member_provider import ActiveMemberProvider
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetFormerMembers(TapirIntegrationTest):
    def test_getFormerMembers_default_returnsAllMembersThatAreNotActive(self):
        former_member = MemberFactory.create()
        AssociationMembershipFactory.create(
            member=former_member,
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=3, day=15),
        )
        active_member = MemberFactory.create()
        AssociationMembershipFactory.create(
            member=active_member, start_date=datetime.date(year=2026, month=1, day=1)
        )

        result = ActiveMemberProvider.get_former_members(
            reference_datetime=datetime.datetime(
                year=2026, month=4, day=1, tzinfo=datetime.timezone.utc
            ),
            cache={},
        )

        self.assertQuerySetEqual(result, [former_member])
