import datetime
from decimal import Decimal
from unittest.mock import patch

from django.core import mail
from django.db import transaction
from django.test import override_settings
from django.urls import reverse
from tapir_mail.models import EmailConfigurationDispatch, ReleaseStatus
from tapir_mail.service.email import build_email
from tapir_mail.service.token import replace_tokens, token_registry
from tapir_mail.tests.factories import EmailConfigurationVersionFactory
from tapir_mail.triggers.transactional_trigger import TransactionalTrigger

from tapir.associations.apps import AssociationsConfig
from tapir.associations.mail_tokens import ASSOCIATION_DEPOSIT_MAIL_TOKENS
from tapir.associations.models import AssociationDepositRefund
from tapir.associations.services.association_deposit_overview_provider import (
    AssociationDepositOverviewProvider,
)
from tapir.associations.services.association_deposit_mail_token_provider import (
    AssociationDepositMailTokenProvider,
)
from tapir.associations.tasks import trigger_association_membership_ends_today_mails
from tapir.associations.tests.factories import (
    AssociationDepositAccountFactory,
    AssociationDepositReceiptFactory,
    AssociationMembershipFactory,
)
from tapir.coop.tasks import send_membership_entry_mails
from tapir.core.config import (
    LEGAL_STATUS_ASSOCIATION,
    LEGAL_STATUS_COOPERATIVE,
    LEGAL_STATUS_COMPANY,
)
from tapir.subscriptions.services.order_confirmation_mail_sender import (
    OrderConfirmationMailSender,
)
from tapir.wirgarten.constants import NO_DELIVERY
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import Payment
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.service.member import (
    send_investing_membership_confirmation,
    send_product_order_confirmation,
)
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PaymentFactory,
    SubscriptionFactory,
    ProductPriceFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestAssociationDepositMailTokens(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.today = datetime.date(2026, 11, 6)
        self.now = mock_timezone(self, datetime.datetime(2026, 11, 6, 12))
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION
        )
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED, True)
        self._set_parameter(
            ParameterKeys.ASSOCIATION_DEPOSIT_NAME, "Investitionsbetrag"
        )
        self.member = MemberFactory(has_received_membership_started_mail=False)
        self.membership = AssociationMembershipFactory(
            member=self.member, start_date=self.today
        )
        self.account = AssociationDepositAccountFactory(
            member=self.member,
            agreed_amount=200,
            effective_from=self.today,
            instalment_count=4,
        )
        self.dates = [
            datetime.date(2026, 12, 5),
            datetime.date(2027, 1, 5),
            datetime.date(2027, 2, 5),
            datetime.date(2027, 3, 5),
        ]
        for index, date in enumerate(self.dates, 1):
            PaymentFactory(
                association_deposit_account=self.account,
                mandate_ref__member=self.member,
                due_date=date,
                amount=50,
                instalment_number=index,
                status=Payment.PaymentStatus.DUE,
                transaction=None,
            )

    def configure_event(self, event):
        prefix = TransactionalTrigger.transactional_trigger_registry[event]
        content = (
            "<p>"
            + " | ".join(
                "{{" + prefix + "." + label + "}}"
                for label in ASSOCIATION_DEPOSIT_MAIL_TOKENS
            )
            + "</p>"
        )
        return EmailConfigurationVersionFactory(
            status=ReleaseStatus.RELEASED,
            content=content,
            triggers=[
                {
                    "trigger_id": TransactionalTrigger.get_id(),
                    "trigger_field_values": {"key": event},
                }
            ],
        )

    def test_registry_exposes_tokens_only_on_relevant_transactional_actions(self):
        relevant = {
            Events.REGISTER_MEMBERSHIP_AND_SUBSCRIPTION,
            Events.REGISTER_MEMBERSHIP_ONLY,
            Events.WAITING_LIST_ORDER_CONFIRMATION,
            Events.ORDER_CONFIRMED_BY_ADMIN,
            Events.MEMBERSHIP_ENTRY,
            AssociationsConfig.MAIL_TRIGGER_ASSOCIATION_MEMBERSHIP_END_DATE_SET,
            AssociationsConfig.MAIL_TRIGGER_ASSOCIATION_MEMBERSHIP_ENDS_TODAY,
        }
        for event, tokens in TransactionalTrigger.trigger_tokens.items():
            with self.subTest(event=event):
                keys = set(tokens.values()) & set(
                    ASSOCIATION_DEPOSIT_MAIL_TOKENS.values()
                )
                self.assertEqual(
                    (
                        set(ASSOCIATION_DEPOSIT_MAIL_TOKENS.values())
                        if event in relevant
                        else set()
                    ),
                    keys,
                )
        self.client.force_login(MemberFactory(is_superuser=True))
        response = self.client.get("/tapirmail/api/trigger_tokens/get_tokens/")
        self.assertEqual(200, response.status_code)
        for event in relevant:
            group = response.json()[event][
                TransactionalTrigger.transactional_trigger_registry[event]
            ]
            self.assertTrue(set(ASSOCIATION_DEPOSIT_MAIL_TOKENS) <= set(group))
        for tokens in token_registry.values():
            self.assertFalse(set(tokens) & set(ASSOCIATION_DEPOSIT_MAIL_TOKENS))
            self.assertFalse(
                {value for value in tokens.values() if isinstance(value, str)}
                & set(ASSOCIATION_DEPOSIT_MAIL_TOKENS.values())
            )

    def test_standard_plan_uses_backend_dates_and_amounts_without_financial_writes(
        self,
    ):
        before = list(self.account.payments.order_by("pk").values())
        with patch.object(
            AssociationDepositOverviewProvider,
            "get_rows",
            side_effect=AssertionError(
                "Bulkübersicht darf für einzelne Mails nicht geladen werden"
            ),
        ):
            tokens = AssociationDepositMailTokenProvider.build_tokens(self.member, {})
        self.assertEqual("Investitionsbetrag", tokens["association_deposit_name"])
        self.assertEqual("200,00", tokens["association_deposit_amount"])
        self.assertEqual("Reguläre Vereinbarung", tokens["association_deposit_status"])
        self.assertEqual(
            "05.12.2026: 50,00 € (offen); 05.01.2027: 50,00 € (offen); 05.02.2027: 50,00 € (offen); 05.03.2027: 50,00 € (offen)",
            tokens["association_deposit_payment_plan"],
        )
        self.assertEqual(before, list(self.account.payments.order_by("pk").values()))

    def test_unknown_waived_reduced_and_feature_off_history_are_distinct(self):
        self.account.payments.all().delete()
        for amount, status, text in [
            (None, "Individuelle Vereinbarung offen", "Nicht vereinbart"),
            (Decimal("0"), "Vollständiger Verzicht vereinbart", "0,00"),
            (Decimal("100"), "Individuelle Vereinbarung", "100,00"),
        ]:
            with self.subTest(amount=amount):
                self.account.agreed_amount = amount
                self.account.effective_from = self.today if amount is not None else None
                self.account.hardship_requested_at = self.now
                self.account.is_individual_agreement = True
                self.account.save()
                tokens = AssociationDepositMailTokenProvider.build_tokens(
                    self.member, {}
                )
                self.assertEqual(text, tokens["association_deposit_amount"])
                self.assertEqual(status, tokens["association_deposit_status"])
                self.assertEqual(
                    "Kein Einzug vereinbart", tokens["association_deposit_payment_plan"]
                )
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED, False)
        self.assertEqual(
            "100,00",
            AssociationDepositMailTokenProvider.build_tokens(self.member, {})[
                "association_deposit_amount"
            ],
        )
        self.assertFalse(self.account.payments.exists())
        AssociationDepositReceiptFactory(
            account=self.account, amount=25, received_on=self.today
        )
        for index, date in enumerate(self.dates, 1):
            PaymentFactory(
                association_deposit_account=self.account,
                mandate_ref__member=self.member,
                due_date=date,
                amount=Decimal("18.75"),
                instalment_number=index,
                status=Payment.PaymentStatus.DUE,
                transaction=None,
            )
        tokens = AssociationDepositMailTokenProvider.build_tokens(self.member, {})
        self.assertEqual("100,00", tokens["association_deposit_amount"])
        self.assertEqual("25,00", tokens["association_deposit_retained_amount"])
        self.assertEqual(4, tokens["association_deposit_payment_plan"].count("18,75"))

    def test_no_account_and_other_legal_statuses_have_blank_compatible_tokens(self):
        empty = dict.fromkeys(ASSOCIATION_DEPOSIT_MAIL_TOKENS.values(), "")
        self.assertEqual(
            empty, AssociationDepositMailTokenProvider.build_tokens(MemberFactory(), {})
        )
        for legal_status in [LEGAL_STATUS_COOPERATIVE, LEGAL_STATUS_COMPANY]:
            self._set_parameter(ParameterKeys.ORGANISATION_LEGAL_STATUS, legal_status)
            self.assertEqual(
                empty, AssociationDepositMailTokenProvider.build_tokens(self.member, {})
            )

    def test_refunded_book_values_and_stopped_history_do_not_promise_a_payout(self):
        self.account.payments.all().delete()
        paid = PaymentFactory(
            association_deposit_account=self.account,
            mandate_ref__member=self.member,
            amount=200,
        )
        PaymentFactory(
            association_deposit_account=self.account,
            mandate_ref__member=self.member,
            status=Payment.PaymentStatus.DUE,
            transaction=None,
            amount=50,
            due_date=self.dates[0],
        )
        AssociationDepositRefund.objects.create(
            account=self.account,
            amount=50,
            refunded_on=self.today,
            reference="mail-refund",
            note="Bankseitig geprüft",
        )
        self.account.refund_requires_agreement = True
        self.account.save()
        tokens = AssociationDepositMailTokenProvider.build_tokens(self.member, {})
        self.assertEqual("200,00", tokens["association_deposit_amount"])
        self.assertEqual("150,00", tokens["association_deposit_retained_amount"])
        self.assertEqual("50,00", tokens["association_deposit_refunded_amount"])
        self.assertIn("verbucht/exportiert", tokens["association_deposit_payment_plan"])
        self.assertIn("Einzug gesperrt", tokens["association_deposit_payment_plan"])
        self.assertEqual(
            "Einzug bis zu neuer Vereinbarung gesperrt",
            tokens["association_deposit_status"],
        )
        paid.refresh_from_db()
        self.assertEqual(200, paid.amount)
        self.assertIsNotNone(paid.transaction_id)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        EMAIL_AUTO_BCC=None,
        EMAIL_BOUNCE_ADDRESS="bounce@example.test",
        EMAIL_HOST_SENDER="mail@example.test",
        EMAIL_HOST_SENDER_NAME="Test",
    )
    def test_membership_confirmation_creates_real_dispatch_and_renders_captured_tokens(
        self,
    ):
        version = self.configure_event(Events.REGISTER_MEMBERSHIP_ONLY)
        send_investing_membership_confirmation(
            self.member.pk, None, self.membership, None, {}
        )
        dispatch = EmailConfigurationDispatch.objects.get(
            email_configuration_version=version
        )
        self.assertFalse(dispatch.is_sent)
        self.assertEqual(
            [{"recipient_id_in_base_queryset": self.member.pk}],
            dispatch.override_recipients,
        )
        rendered = replace_tokens(
            version.content, transactional_tokens=dispatch.additional_tokens
        )
        self.assertIn("Investitionsbetrag", rendered)
        self.assertIn("200,00", rendered)
        self.assertIn("05.12.2026: 50,00", rendered)
        self.assertNotIn("{{", rendered)
        self.assertNotIn("None", rendered)
        build_email(
            html=rendered, subject="Test", recipients=["synthetic@example.test"]
        ).send()
        self.assertEqual(1, len(mail.outbox))
        self.assertEqual(["synthetic@example.test"], mail.outbox[0].to)
        self.assertIn("200,00", mail.outbox[0].body)

    def test_failed_transaction_rolls_back_actual_configured_dispatch(self):
        version = self.configure_event(Events.REGISTER_MEMBERSHIP_ONLY)
        with self.assertRaises(ValueError):
            with transaction.atomic():
                send_investing_membership_confirmation(
                    self.member.pk, None, self.membership, None, {}
                )
                self.assertEqual(
                    1,
                    EmailConfigurationDispatch.objects.filter(
                        email_configuration_version=version
                    ).count(),
                )
                raise ValueError("Abbruch")
        self.assertFalse(
            EmailConfigurationDispatch.objects.filter(
                email_configuration_version=version
            ).exists()
        )

    def test_actual_entry_waits_for_membership_start_and_reuses_existing_sent_flag(
        self,
    ):
        version = self.configure_event(Events.MEMBERSHIP_ENTRY)
        self.membership.start_date = self.today + datetime.timedelta(days=1)
        self.membership.save()
        send_membership_entry_mails()
        self.assertFalse(EmailConfigurationDispatch.objects.exists())
        self.membership.start_date = self.today
        self.membership.save()
        send_membership_entry_mails()
        send_membership_entry_mails()
        dispatch = EmailConfigurationDispatch.objects.get(
            email_configuration_version=version
        )
        self.assertIn("200,00", dispatch.additional_tokens.values())
        self.member.refresh_from_db()
        self.assertTrue(self.member.has_received_membership_started_mail)

    def test_end_date_and_actual_end_use_existing_triggers_with_tokens(self):
        admin = MemberFactory(is_superuser=True)
        self.client.force_login(admin)
        end_version = self.configure_event(
            AssociationsConfig.MAIL_TRIGGER_ASSOCIATION_MEMBERSHIP_END_DATE_SET
        )
        response = self.client.post(
            reverse("associations:set_membership_end_date"),
            {"membership_id": self.membership.pk, "end_date": self.today.isoformat()},
            content_type="application/json",
        )
        self.assertEqual(200, response.status_code)
        dispatch = EmailConfigurationDispatch.objects.get(
            email_configuration_version=end_version
        )
        self.assertIn("200,00", dispatch.additional_tokens.values())
        today_version = self.configure_event(
            AssociationsConfig.MAIL_TRIGGER_ASSOCIATION_MEMBERSHIP_ENDS_TODAY
        )
        trigger_association_membership_ends_today_mails()
        trigger_association_membership_ends_today_mails()
        self.assertEqual(
            1,
            EmailConfigurationDispatch.objects.filter(
                email_configuration_version=today_version
            ).count(),
        )

    def test_actual_end_without_known_cancellation_timestamp_keeps_unknown_date(self):
        version = self.configure_event(
            AssociationsConfig.MAIL_TRIGGER_ASSOCIATION_MEMBERSHIP_ENDS_TODAY
        )
        self.membership.end_date = self.today
        self.membership.cancellation_ts = None
        self.membership.save()
        trigger_association_membership_ends_today_mails()
        dispatch = EmailConfigurationDispatch.objects.get(
            email_configuration_version=version
        )
        self.assertIn("200,00", dispatch.additional_tokens.values())

    def test_admin_order_confirmation_uses_same_targeted_member_tokens(self):
        version = self.configure_event(Events.ORDER_CONFIRMED_BY_ADMIN)
        subscription = SubscriptionFactory(member=self.member, auto_confirmed=None)
        OrderConfirmationMailSender.send_confirmation_mail_if_necessary(
            [subscription.pk], []
        )
        dispatch = EmailConfigurationDispatch.objects.get(
            email_configuration_version=version
        )
        self.assertIn("200,00", dispatch.additional_tokens.values())

    def test_product_and_waiting_list_confirmations_populate_the_existing_actions(self):
        subscription = SubscriptionFactory(
            member=self.member, product__type__delivery_cycle=NO_DELIVERY[0]
        )
        ProductPriceFactory(product=subscription.product, price=30, size=1)
        for event, waiting in [
            (Events.REGISTER_MEMBERSHIP_AND_SUBSCRIPTION, False),
            (Events.WAITING_LIST_ORDER_CONFIRMATION, True),
        ]:
            with self.subTest(event=event):
                version = self.configure_event(event)
                send_product_order_confirmation(
                    self.member, [subscription], {}, waiting, None, None, None
                )
                dispatch = EmailConfigurationDispatch.objects.get(
                    email_configuration_version=version
                )
                self.assertIn("200,00", dispatch.additional_tokens.values())
                self.assertTrue(
                    any(
                        "05.12.2026: 50,00" in str(value)
                        for value in dispatch.additional_tokens.values()
                    )
                )
