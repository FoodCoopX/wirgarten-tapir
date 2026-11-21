from tapir_mail.triggers.transactional_trigger import TransactionalTrigger

from tapir.core.config import (
    LEGAL_STATUS_ASSOCIATION,
    LEGAL_STATUS_COMPANY,
    LEGAL_STATUS_COOPERATIVE,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tapirmail import configure_mail_module
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestTransactionalTriggerRegistrations(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        configure_mail_module()

    def test_isTriggerRequired_allRegisteredTriggers_resolvesWithCache(self):
        self.assertNotEqual(0, len(TransactionalTrigger.required_triggers))

        for legal_status in [
            LEGAL_STATUS_ASSOCIATION,
            LEGAL_STATUS_COMPANY,
            LEGAL_STATUS_COOPERATIVE,
        ]:
            self._set_parameter(
                key=ParameterKeys.ORGANISATION_LEGAL_STATUS, value=legal_status
            )
            for key in TransactionalTrigger.required_triggers.keys():
                with self.subTest(legal_status=legal_status, key=key):
                    result = TransactionalTrigger.is_trigger_required(key=key, cache={})
                    self.assertIsInstance(result, bool)
