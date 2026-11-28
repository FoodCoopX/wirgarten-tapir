from tapir.core.services.subscription_management_request_resolver import (
    SubscriptionManagementRequestResolver,
)
from tapir.mail.tests.factories import MailCategoryFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetExternalCategories(TapirIntegrationTest):
    def test_getExternalCategories_default_returnsThePublicCategoriesSortedByName(
        self,
    ):
        category_b = MailCategoryFactory.create(name="B")
        category_a = MailCategoryFactory.create(name="A")
        MailCategoryFactory.create(name="C", available_for_external_recipients=False)

        result = SubscriptionManagementRequestResolver.get_external_categories()

        self.assertEqual([category_a, category_b], result)
