from unittest.mock import patch

from django.test import RequestFactory, override_settings

from tapir.payments.models import MemberCredit
from tapir.payments.tests.factories import MemberCreditFactory
from tapir.utils.config import Organization
from tapir.utils.services.test_data_generation.data_generator import DataGenerator
from tapir.utils.views import ResetTestData
from tapir.wirgarten.models import PickupLocation
from tapir.wirgarten.tests.factories import MemberFactory, PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestResetTestData(TapirIntegrationTest):
    @override_settings(DEBUG=True)
    @patch.object(DataGenerator, "generate_all", autospec=True)
    def test_post_creditReferencesPickupLocation_deletesBoth(self, generate_all):
        location = PickupLocationFactory.create()
        credit = MemberCreditFactory.create(pickup_location=location)
        request = RequestFactory().post(
            "/utils/reset_test_data",
            {"generate_test_data_for": Organization.BIOTOP.name, "confirmation": "on"},
        )
        request.user = MemberFactory.create(is_superuser=True)

        response = ResetTestData.as_view()(request)

        self.assertStatusCode(response, 302)
        self.assertFalse(MemberCredit.objects.filter(pk=credit.pk).exists())
        self.assertFalse(PickupLocation.objects.filter(pk=location.pk).exists())
        generate_all.assert_called_once_with(Organization.BIOTOP)
