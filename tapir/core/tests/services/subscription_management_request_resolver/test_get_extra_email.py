from django.http import Http404
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from tapir.core.services.subscription_management_request_resolver import (
    SubscriptionManagementRequestResolver,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberExtraEmailFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetExtraEmail(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        self._set_parameter(key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, value=True)

    def test_getExtraEmail_addressIsAConfirmedExtra_returnsIt(self):
        extra_email = MemberExtraEmailFactory.create(
            email="extra@example.com", confirmed_on=timezone.now()
        )

        result = SubscriptionManagementRequestResolver.get_extra_email(
            address="extra@example.com", cache={}
        )

        self.assertEqual(extra_email, result)

    def test_getExtraEmail_addressIsAnUnconfirmedExtra_raisesHttp404(self):
        MemberExtraEmailFactory.create(email="extra@example.com", confirmed_on=None)

        with self.assertRaises(Http404):
            SubscriptionManagementRequestResolver.get_extra_email(
                address="extra@example.com", cache={}
            )

    def test_getExtraEmail_featureDisabled_raisesValidationError(self):
        self._set_parameter(key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, value=False)
        MemberExtraEmailFactory.create(
            email="extra@example.com", confirmed_on=timezone.now()
        )

        with self.assertRaisesMessage(
            ValidationError, "Diese Funktion ist ausgeschaltet."
        ):
            SubscriptionManagementRequestResolver.get_extra_email(
                address="extra@example.com", cache={}
            )
