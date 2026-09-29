from django.urls import reverse

from tapir.core.config import LEGAL_STATUS_ASSOCIATION, LEGAL_STATUS_COOPERATIVE
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestProductCfgViewGetContextData(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_getContextData_organisationIsCooperative_showCooperativeContentIsTrue(
        self,
    ):
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_COOPERATIVE
        )
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        response = self.client.get(reverse("wirgarten:product"))

        self.assertStatusCode(response, 200)
        self.assertTrue(response.context["show_cooperative_content"])

    def test_getContextData_organisationIsNotCooperative_showCooperativeContentIsFalse(
        self,
    ):
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION
        )
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        response = self.client.get(reverse("wirgarten:product"))

        self.assertStatusCode(response, 200)
        self.assertFalse(response.context["show_cooperative_content"])
