from tapir.wirgarten.tests.factories import GrowingPeriodFactory, MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.views.contracts import SubscriptionListFilter


class TestSubscriptionListFilterMemberDropdown(TapirIntegrationTest):
    @staticmethod
    def _get_member_dropdown_ids() -> list[str]:
        growing_period = GrowingPeriodFactory.create()
        filterset = SubscriptionListFilter(data={"period": growing_period.id})
        return list(
            filterset.form.fields["member"].queryset.values_list("id", flat=True)
        )

    def test_memberDropdown_compoundLowercaseLastName_sortedCaseInsensitivelyByLastName(
        self,
    ):
        vogel = MemberFactory.create(last_name="Vogel")
        von_adler = MemberFactory.create(last_name="von Adler")
        voss = MemberFactory.create(last_name="Voss")
        relevant_ids = {vogel.id, von_adler.id, voss.id}

        ordered_ids = self._get_member_dropdown_ids()

        ordered_last_names = [
            {vogel.id: "Vogel", von_adler.id: "von Adler", voss.id: "Voss"}[member_id]
            for member_id in ordered_ids
            if member_id in relevant_ids
        ]
        self.assertEqual(["Vogel", "von Adler", "Voss"], ordered_last_names)

    def test_memberDropdown_membersWithIdenticalName_tieBrokenByMemberNumber(self):
        older_member = MemberFactory.create(
            first_name="Anna", last_name="Schmidt", member_no=100
        )
        younger_member = MemberFactory.create(
            first_name="Anna", last_name="Schmidt", member_no=200
        )

        ordered_ids = self._get_member_dropdown_ids()

        self.assertLess(
            ordered_ids.index(older_member.id),
            ordered_ids.index(younger_member.id),
        )
