from tapir.configuration.models import TapirParameter
from tapir.configuration.parameter import get_parameter_meta
from tapir.wirgarten.constants import ParameterCategory
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestParameterDefinitions(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_parametersImported_flagsHaveExpectedDefaults(self):
        self.assertFalse(
            TapirParameter.objects.get(
                key=ParameterKeys.BIDDING_ROUND_ENABLED
            ).get_value()
        )
        self.assertTrue(
            TapirParameter.objects.get(
                key=ParameterKeys.BIDDING_ROUND_URL_ENABLED
            ).get_value()
        )

    def test_parametersImported_allBiddingRoundParametersExist(self):
        for name in dir(ParameterKeys):
            if name.startswith("BIDDING_ROUND_"):
                key = getattr(ParameterKeys, name)
                self.assertTrue(
                    TapirParameter.objects.filter(key=key).exists(),
                    msg=f"Missing parameter definition: {key}",
                )

    def test_parametersImported_orderPrioritiesAreUnique(self):
        priorities = list(
            TapirParameter.objects.filter(
                category=ParameterCategory.BIDDING_ROUND
            ).values_list("order_priority", flat=True)
        )

        self.assertEqual(len(priorities), len(set(priorities)))

    def test_parametersImported_onlyTheMasterFlagIsAlwaysVisible(self):
        for name in dir(ParameterKeys):
            if not name.startswith("BIDDING_ROUND_"):
                continue
            key = getattr(ParameterKeys, name)
            meta = get_parameter_meta(key)
            if key == ParameterKeys.BIDDING_ROUND_ENABLED:
                self.assertIsNone(meta.show_only_when)
            else:
                self.assertIsNotNone(meta.show_only_when)
