from tapir.subscriptions.services.order_confirmation_mail_token_builder import (
    OrderConfirmationMailTokenBuilder,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetFirstPickupDateForRecipient(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_getFirstPickupDateForRecipient_memberWithoutSubscriptions_returnsKeineLieferung(
        self,
    ):
        member = MemberFactory.create()

        result = OrderConfirmationMailTokenBuilder.get_first_pickup_date_for_recipient(
            recipient=member, cache={}
        )

        self.assertEqual("Keine Lieferung", result)
