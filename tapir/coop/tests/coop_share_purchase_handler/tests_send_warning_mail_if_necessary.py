import datetime
from unittest.mock import Mock, patch

from tapir.configuration.models import TapirParameter
from tapir.coop.services.coop_share_purchase_handler import CoopSharePurchaseHandler
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestSendWarningMailIfNecessary(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()
        TapirParameter.objects.filter(
            key=ParameterKeys.COOP_THRESHOLD_WARNING_ON_MANY_COOP_SHARES_BOUGHT
        ).update(value=8)
        TapirParameter.objects.filter(key=ParameterKeys.SITE_ADMIN_EMAIL).update(
            value="admin@example.com"
        )

    @patch("tapir.coop.services.coop_share_purchase_handler.send_email")
    def test_sendWarningMailIfNecessary_quantityIsBelowThreshold_noMailSent(
        self, mock_send_email: Mock
    ):
        CoopSharePurchaseHandler.send_warning_mail_if_necessary(
            quantity=7, member=Mock(), shares_valid_at=Mock(), cache={}
        )

        mock_send_email.assert_not_called()

    @patch("tapir.coop.services.coop_share_purchase_handler.send_email")
    def test_sendWarningMailIfNecessary_quantityIsAboveThreshold_mailSent(
        self, mock_send_email: Mock
    ):
        member = MemberFactory.create(
            first_name="John", last_name="Smith", email="john@example.com"
        )

        with self.captureOnCommitCallbacks(execute=True):
            CoopSharePurchaseHandler.send_warning_mail_if_necessary(
                quantity=9,
                member=member,
                shares_valid_at=datetime.date(year=2022, month=2, day=27),
                cache={},
            )

        mock_send_email.assert_called_once_with(
            to_email=["admin@example.com"],
            subject="Warnung: eine große Anzahl an Anteile ist bestellt worden",
            content="Mitglied: John Smith mit Mail-Adresse john@example.com hat gerade 9 Genossenschaftsanteile gezeichnet. Die Anteile sind ab dem 27.02.2022 gültig.",
        )

    @patch("tapir.coop.services.coop_share_purchase_handler.send_email")
    def test_sendWarningMailIfNecessary_quantityIsExactlyThreshold_mailSent(
        self, mock_send_email: Mock
    ):
        member = MemberFactory.create(
            first_name="John", last_name="Smith", email="john@example.com"
        )

        with self.captureOnCommitCallbacks(execute=True):
            CoopSharePurchaseHandler.send_warning_mail_if_necessary(
                quantity=8,
                member=member,
                shares_valid_at=datetime.date(year=2022, month=2, day=27),
                cache={},
            )

        mock_send_email.assert_called_once_with(
            to_email=["admin@example.com"],
            subject="Warnung: eine große Anzahl an Anteile ist bestellt worden",
            content="Mitglied: John Smith mit Mail-Adresse john@example.com hat gerade 8 Genossenschaftsanteile gezeichnet. Die Anteile sind ab dem 27.02.2022 gültig.",
        )
