from django.template.response import TemplateResponse
from django.urls import reverse

from tapir.configuration.models import TapirParameter
from tapir.wirgarten.models import (
    Member,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import (
    ParameterDefinitions,
)
from tapir.wirgarten.tapirmail import configure_mail_module
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    ProductTypeFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestStudentStatus(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.COOP_SHARES_INDEPENDENT_FROM_HARVEST_SHARES
        ).update(value="True")
        product_type = ProductTypeFactory.create()
        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=product_type.id
        )

    def setUp(self) -> None:
        configure_mail_module()

    def test_personalDataFormForm_loggedInAsNormalMember_studentStatusCheckboxDisabled(
        self,
    ):
        member = MemberFactory.create()
        self.client.force_login(member)

        url = reverse("wirgarten:member_edit", args=[member.id])
        response: TemplateResponse = self.client.get(url)

        form_fields = response.context_data["form"].fields
        self.assertIn("is_student", form_fields.keys())
        self.assertTrue(form_fields["is_student"].disabled)

    def test_personalDataFormForm_loggedInAsAdmin_studentStatusCheckboxEnabled(
        self,
    ):
        member_to_edit = MemberFactory.create()
        member_logged_in: Member = MemberFactory.create(is_superuser=True)

        self.client.force_login(member_logged_in)

        url = reverse("wirgarten:member_edit", args=[member_to_edit.id])
        response: TemplateResponse = self.client.get(url)

        form_fields = response.context_data["form"].fields
        self.assertIn("is_student", form_fields.keys())
        self.assertFalse(form_fields["is_student"].disabled)
