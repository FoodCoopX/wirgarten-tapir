from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.subscriptions.views.confirmations import MemberDataToConfirmApiView
from tapir.wirgarten.tests.factories import ProductTypeFactory, SubscriptionFactory


class TestClassifyChanges(TapirUnitTest):
    def test_classifyChanges_productTypeHasOnlyCreations_allChangesAddedToCreations(
        self,
    ):
        subscription = SubscriptionFactory.build()
        changes_by_product_type = {
            ProductTypeFactory.build(): {
                "creations": [subscription],
                "cancellations": [],
            }
        }

        result = MemberDataToConfirmApiView.classify_changes(changes_by_product_type)

        self.assertEqual([], result["cancellations"])
        self.assertEqual([], result["changes"])
        self.assertEqual([subscription], result["creations"])

    def test_classifyChanges_productTypeSameOnlyCancellations_allChangesAddedToCancellations(
        self,
    ):
        subscription = SubscriptionFactory.build()
        changes_by_product_type = {
            ProductTypeFactory.build(): {
                "creations": [],
                "cancellations": [subscription],
            }
        }

        result = MemberDataToConfirmApiView.classify_changes(changes_by_product_type)

        self.assertEqual([subscription], result["cancellations"])
        self.assertEqual([], result["changes"])
        self.assertEqual([], result["creations"])

    def test_classifyChanges_productTypeHasBothCreationsAndCancellations_allChangesAddedToChanges(
        self,
    ):
        subscription_1 = SubscriptionFactory.build()
        subscription_2 = SubscriptionFactory.build()
        product_type = ProductTypeFactory.build()
        changes_by_product_type = {
            product_type: {
                "creations": [subscription_1],
                "cancellations": [subscription_2],
            }
        }

        result = MemberDataToConfirmApiView.classify_changes(changes_by_product_type)

        self.assertEqual([], result["cancellations"])
        self.assertEqual(
            [
                {
                    "product_type": product_type,
                    "subscription_cancellations": [subscription_2],
                    "subscription_creations": [subscription_1],
                }
            ],
            result["changes"],
        )
        self.assertEqual([], result["creations"])
