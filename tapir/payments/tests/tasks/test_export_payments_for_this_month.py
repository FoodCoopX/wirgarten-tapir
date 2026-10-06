import datetime

from django.core import mail

from tapir.payments.tasks import export_payments_for_this_month
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    SubscriptionFactory,
    GrowingPeriodFactory,
    ProductPriceFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestExportPaymentsForThisMonth(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls._set_parameter(
            key=ParameterKeys.PAYMENT_ORGANISATION_IBAN, value="NL88ABNA2011060885"
        )
        cls._set_parameter(
            key=ParameterKeys.PAYMENT_CREDITOR_IDENTIFIER, value="test_id"
        )
        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2019, month=1, day=1)
        )
        cls._set_parameter(
            key=ParameterKeys.PAYMENT_START_DATE, value=growing_period.start_date
        )
        cls.valid_subscription = SubscriptionFactory.create(
            period=growing_period,
            member__first_name="Alice",
            member__last_name="Valid",
            member__member_no=902,
        )
        cls.invalid_subscription = SubscriptionFactory.create(
            period=growing_period,
            member__iban="INVALID_IBAN",
            member__first_name="John",
            member__last_name="Invalid",
            member__member_no=13,
            product=cls.valid_subscription.product,
        )
        Subscription.objects.update(
            created_at=datetime.datetime(
                year=2019, month=1, day=1, tzinfo=datetime.timezone.utc
            )
        )
        ProductPriceFactory.create(
            product=cls.valid_subscription.product,
            price=10,
            valid_from=growing_period.start_date,
        )

    def test_exportPaymentsForThisMonth_somePaymentsFail_sendMailWithErrorDetails(self):
        mock_timezone(test=self, now=datetime.datetime(year=2019, month=6, day=15))
        export_payments_for_this_month()

        self.assertEqual(1, len(mail.outbox))
        sent_mail = mail.outbox[0]

        self.assertEqual(
            "Verträge-Einzahlungen Juni 2019.xml ist bereit (1 Fehler)",
            sent_mail.subject,
        )
        self.assertEqual(
            "<p>Hallo Admin,</p><p>im Anhang findest du die aktuelle Verträge-Einzahlungen Juni 2019_20190615_000000.xml.</p><p>Es gab 1 Fehler: <ul><li>Mitglied John Invalid #13: IN is not a valid country code for IBAN.</li></ul></p><p>(Automatisch von Tapir versendet)</p>",
            sent_mail.body,
        )

    def test_exportPaymentsForThisMonth_noErrors_sendsCorrectMail(self):
        mock_timezone(test=self, now=datetime.datetime(year=2019, month=6, day=15))

        self.invalid_subscription.member.iban = "NL88ABNA2011060885"
        self.invalid_subscription.member.save()

        export_payments_for_this_month()

        self.assertEqual(1, len(mail.outbox))
        sent_mail = mail.outbox[0]

        self.assertEqual(
            "Verträge-Einzahlungen Juni 2019.xml ist bereit",
            sent_mail.subject,
        )
        self.assertEqual(
            "<p>Hallo Admin,</p><p>im Anhang findest du die aktuelle Verträge-Einzahlungen Juni 2019_20190615_000000.xml.</p><p>(Automatisch von Tapir versendet)</p>",
            sent_mail.body,
        )

    def test_exportPaymentsForThisMonth_invalidConfig_sendsMailWithErrorDetails(self):
        mock_timezone(test=self, now=datetime.datetime(year=2019, month=6, day=15))

        self.invalid_subscription.member.iban = "NL88ABNA2011060885"
        self.invalid_subscription.member.save()

        self._set_parameter(
            key=ParameterKeys.PAYMENT_ORGANISATION_IBAN, value="INVALID"
        )

        export_payments_for_this_month()

        self.assertEqual(1, len(mail.outbox))
        sent_mail = mail.outbox[0]

        self.assertEqual(
            "Fehler bei der Erzeugung der Verträge-Einzahlungen Juni 2019-Datei",
            sent_mail.subject,
        )
        self.assertIn(
            "<p>Hallo Admin,</p><p>Die Datei Verträge-Einzahlungen Juni 2019 konnte nicht erzeugt werden. Grund dafür ist:",
            sent_mail.body,
        )
        self.assertIn(
            "The value 'INVALID' is not accepted by the pattern", sent_mail.body
        )
