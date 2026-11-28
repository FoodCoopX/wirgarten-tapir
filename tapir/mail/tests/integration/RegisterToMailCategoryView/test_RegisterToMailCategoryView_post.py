from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.http import HttpResponse
from django.urls import reverse

from tapir.mail.config import TransactionalTriggerKeys
from tapir.mail.models import ExternalRecipient, MailCategory, StaticSegmentRecipient
from tapir.mail.tests.factories import MailCategoryFactory
from tapir.mail.triggers.transactional_trigger import TransactionalTrigger
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@patch.object(TransactionalTrigger, "fire_action", autospec=True)
class TestRegisterToMailCategoryViewPost(TapirIntegrationTest):
    EMAIL = "external@example.com"

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_post_newAddress_sendsConfirmationMail(self, mock_fire_action: MagicMock):
        category = MailCategoryFactory.create(available_for_external_recipients=True)

        response = self._register(category=category, email=self.EMAIL)

        self._assert_redirects_to_confirmation_mail_sent(
            response=response, category=category
        )
        mock_fire_action.assert_called_once()
        trigger_data = mock_fire_action.call_args.args[0]
        self.assertEqual(
            TransactionalTriggerKeys.MAIL_CATEGORY_REGISTRATION_CONFIRMATION_LINK,
            trigger_data.key,
        )
        self.assertEqual(
            self.EMAIL, trigger_data.recipient_outside_of_base_queryset.email
        )

    def test_post_mixedCaseAddress_storesTheNormalisedAddress(self, _: MagicMock):
        category = MailCategoryFactory.create(available_for_external_recipients=True)

        self._register(category=category, email=" External@Example.com")

        self.assertEqual(
            [self.EMAIL],
            list(ExternalRecipient.objects.values_list("email", flat=True)),
        )

    def test_post_sameAddressWithinCooldown_sendsNoSecondMail(
        self, mock_fire_action: MagicMock
    ):
        category = MailCategoryFactory.create(available_for_external_recipients=True)
        self._register(category=category, email=self.EMAIL)

        response = self._register(category=category, email=" EXTERNAL@example.com")

        self._assert_redirects_to_confirmation_mail_sent(
            response=response, category=category
        )
        mock_fire_action.assert_called_once()

    def test_post_sameAddressAfterCooldown_sendsMailAgain(
        self, mock_fire_action: MagicMock
    ):
        category = MailCategoryFactory.create(available_for_external_recipients=True)
        self._register(category=category, email=self.EMAIL)
        # The cooldown lives in the cache: clearing it is what its expiry does.
        cache.clear()

        self._register(category=category, email=self.EMAIL)

        self.assertEqual(2, mock_fire_action.call_count)

    def test_post_sameAddressForAnotherCategory_sendsMail(
        self, mock_fire_action: MagicMock
    ):
        self._register(
            category=MailCategoryFactory.create(available_for_external_recipients=True),
            email=self.EMAIL,
        )

        self._register(
            category=MailCategoryFactory.create(available_for_external_recipients=True),
            email=self.EMAIL,
        )

        self.assertEqual(2, mock_fire_action.call_count)

    def test_post_alreadyRegisteredAddress_showsSamePageWithoutMail(
        self, mock_fire_action: MagicMock
    ):
        category = MailCategoryFactory.create(available_for_external_recipients=True)
        StaticSegmentRecipient.objects.create(
            segment_id=category.static_segment_id, email=self.EMAIL
        )

        response = self._register(category=category, email=self.EMAIL)

        self._assert_redirects_to_confirmation_mail_sent(
            response=response, category=category
        )
        mock_fire_action.assert_not_called()

    def _register(self, category: MailCategory, email: str):
        return self.client.post(
            reverse("category_registration_external_form", args=[category.id]),
            data={"email": email, "first_name": "External"},
        )

    def _assert_redirects_to_confirmation_mail_sent(
        self, response: HttpResponse, category: MailCategory
    ):
        self.assertRedirects(
            response,
            reverse("confirmation_mail_sent", args=[category.id]),
            fetch_redirect_response=False,
        )
