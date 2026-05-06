import datetime
from unittest.mock import Mock

from django.core import mail

from tapir.configuration.models import TapirParameter
from tapir.coop.services.coop_share_purchase_handler import CoopSharePurchaseHandler
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestSendWarningMailIfNecessary(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.COOP_THRESHOLD_WARNING_ON_MANY_COOP_SHARES_BOUGHT
        ).update(value=8)
        TapirParameter.objects.filter(key=ParameterKeys.SITE_ADMIN_EMAIL).update(
            value="admin@example.com"
        )

    def test_sendWarningMailIfNecessary_quantityIsBelowThreshold_noMailSent(self):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            CoopSharePurchaseHandler.send_warning_mail_if_necessary(
                quantity=7, member=Mock(), shares_valid_at=Mock(), cache={}
            )

        self.assertEqual(len(callbacks), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_sendWarningMailIfNecessary_quantityIsAboveThreshold_mailSent(self):
        member = MemberFactory.create(
            first_name="John", last_name="Smith", email="john@example.com"
        )
        cache = {}

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            CoopSharePurchaseHandler.send_warning_mail_if_necessary(
                quantity=9,
                member=member,
                shares_valid_at=datetime.date(year=2022, month=2, day=27),
                cache=cache,
            )

        self.assertEqual(len(callbacks), 1)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            ["admin@example.com"],
            mail.outbox[0].to,
        )
        self.assertEqual(
            "Warnung: es wurden mehr als 8 Genossenschaftsanteile gezeichnet- bitte prüfen",
            mail.outbox[0].subject,
        )
        self.assertEqual(
            "Bestehendes Mitglied oder Neuanmeldung: John Smith mit Mail-Adresse john@example.com hat gerade 9 Genossenschaftsanteile gezeichnet. Die Anteile sind ab dem 27.02.2022 gültig. Bitte an Vorstand zur Prüfung weiterleiten.",
            mail.outbox[0].body,
        )

    def test_sendWarningMailIfNecessary_quantityIsExactlyThreshold_mailSent(self):
        member = MemberFactory.create(
            first_name="John", last_name="Smith", email="john@example.com"
        )
        cache = {}

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            CoopSharePurchaseHandler.send_warning_mail_if_necessary(
                quantity=8,
                member=member,
                shares_valid_at=datetime.date(year=2022, month=2, day=27),
                cache=cache,
            )

        self.assertEqual(len(callbacks), 1)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            ["admin@example.com"],
            mail.outbox[0].to,
        )
        self.assertEqual(
            "Warnung: es wurden mehr als 8 Genossenschaftsanteile gezeichnet- bitte prüfen",
            mail.outbox[0].subject,
        )
        self.assertEqual(
            "Bestehendes Mitglied oder Neuanmeldung: John Smith mit Mail-Adresse john@example.com hat gerade 8 Genossenschaftsanteile gezeichnet. Die Anteile sind ab dem 27.02.2022 gültig. Bitte an Vorstand zur Prüfung weiterleiten.",
            mail.outbox[0].body,
        )
