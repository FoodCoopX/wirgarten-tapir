from tapir.configuration.models import TapirParameter
from tapir.waiting_list.services.waiting_list_categories_service import (
    WaitingListCategoriesService,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestWaitingListCategoriesService(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_getCategories_default_returnsCorrectCategories(self):
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_WAITING_LIST_CATEGORIES
        ).update(value="cat_1, cat 2,  cat -.;+*3   ")

        result = WaitingListCategoriesService.get_categories(cache={})

        self.assertEqual(["cat_1", "cat 2", "cat -.;+*3"], result)

    def test_getCategories_noCategories_returnsEmptyList(self):
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_WAITING_LIST_CATEGORIES
        ).update(value="")

        result = WaitingListCategoriesService.get_categories(cache={})

        self.assertEqual([], result)

    def test_getCategories_parameterContainsOnlyWhitespaces_returnsEmptyList(self):
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_WAITING_LIST_CATEGORIES
        ).update(value="    ")

        result = WaitingListCategoriesService.get_categories(cache={})

        self.assertEqual([], result)
