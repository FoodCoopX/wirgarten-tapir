import uuid

from django.urls import reverse

from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestExternalRecipientManagerUrl(TapirIntegrationTest):
    def test_get_anySecret_redirectsToTheLinkRequestPage(self):
        response = self.client.get(
            reverse("external_recipient_manager", args=[uuid.uuid4()])
        )

        self.assertRedirects(
            response,
            reverse("core:subscription_management_link_request"),
            fetch_redirect_response=False,
        )
