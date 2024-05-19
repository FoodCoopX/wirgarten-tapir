from tapir_mail.service.token import token_registry

from tapir.configuration.models import TapirParameterDefinitionImporter
from tapir.wirgarten.tapirmail import _register_tokens
from tapir.wirgarten.tests.factories import (
    MemberWithSubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TokenTest(TapirIntegrationTest):
    def setUp(self):
        for cls in TapirParameterDefinitionImporter.__subclasses__():
            cls.import_definitions(cls)

        _register_tokens()

    def test_tokens_userTokens_canBeResolved(self):
        for i in range(10):
            member = MemberWithSubscriptionFactory.create()
            for k, v in token_registry["Empfänger"].items():
                try:
                    result = getattr(member, v)
                    if callable(result):
                        result = result()
                except Exception as e:
                    self.fail(
                        f"Failed to resolve token '{k}' for member '{member.id}': {e}"
                    )

    def test_tokens_generalTokens_canBeResolved(self):
        for k, v in token_registry["Allgemein"].items():
            try:
                result = v() if callable(v) else v
            except Exception as e:
                self.fail(f"Failed to resolve general token '{k}': {e}")
