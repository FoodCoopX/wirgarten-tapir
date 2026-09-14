from django.urls import reverse

from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberDetailViewMemberNumber(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_memberHasMemberNumber_showsFormattedMemberNumberAsFirstDetail(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, False)
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_PREFIX, "BT")
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ZERO_PAD_LENGTH, 4)
        self._login_as_admin()
        member = MemberFactory.create(member_no=17)

        response = self.client.get(reverse("wirgarten:member_detail", args=[member.pk]))

        self.assertStatusCode(response, 200)
        content = response.content.decode()
        self.assertIn('id="tapir_user_member_number">BT0017</div>', content)
        self.assertLess(
            content.index("tapir_user_member_number"),
            content.index("tapir_user_display_name"),
            "Mitgliedsnummer should be shown before Name in the personal data card",
        )

    def test_get_memberHasNoMemberNumber_showsPlaceholder(self):
        self._login_as_admin()
        member = MemberFactory.create()
        member.member_no = None
        member.save()

        response = self.client.get(reverse("wirgarten:member_detail", args=[member.pk]))

        self.assertStatusCode(response, 200)
        self.assertIn(
            'id="tapir_user_member_number">-</div>', response.content.decode()
        )
