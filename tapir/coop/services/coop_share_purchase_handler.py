import datetime
from functools import partial

from dateutil.relativedelta import relativedelta
from django.db import transaction

from tapir.accounts.models import TapirUser
from tapir.configuration.parameter import get_parameter_value
from tapir.coop.models import CoopSharesPurchasedLogEntry
from tapir.payments.config import PAYMENT_TYPE_COOP_SHARES
from tapir.payments.services.mandate_reference_provider import MandateReferenceProvider
from tapir.wirgarten.models import (
    Member,
    Payment,
    CoopShareTransaction,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.email import send_email
from tapir.wirgarten.utils import get_now, format_date


class CoopSharePurchaseHandler:
    @classmethod
    def buy_cooperative_shares(
        cls,
        quantity: int,
        member: Member,
        shares_valid_at: datetime.date,
        cache: dict,
        actor: TapirUser | None,
        pay_in_instalments: bool,
    ):
        mandate_ref = MandateReferenceProvider.get_or_create_mandate_reference(
            member=member, cache=cache
        )

        coop_share_transaction = CoopShareTransaction.objects.create(
            member=member,
            quantity=quantity,
            share_price=get_parameter_value(
                key=ParameterKeys.COOP_SHARE_PRICE, cache=cache
            ),
            valid_at=shares_valid_at,
            mandate_ref=mandate_ref,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
        )

        if pay_in_instalments:
            cls.create_instalment_payments(
                coop_share_transaction=coop_share_transaction, cache=cache
            )
        else:
            cls.create_payment(
                coop_share_transaction=coop_share_transaction, cache=cache
            )

        now = get_now(cache=cache)
        if member.sepa_consent != now:
            member.sepa_consent = get_now(cache=cache)
            member.save()

        cls.send_warning_mail_if_necessary(
            quantity=quantity,
            shares_valid_at=shares_valid_at,
            member=member,
            cache=cache,
        )

        CoopSharesPurchasedLogEntry.populate_transaction(
            coop_share_transaction=coop_share_transaction, actor=actor, user=member
        ).save()

        return coop_share_transaction

    @classmethod
    def create_payment(
        cls, coop_share_transaction: CoopShareTransaction, cache: dict
    ) -> Payment:
        return Payment.objects.create(
            due_date=cls.get_payment_due_date(
                shares_valid_at=coop_share_transaction.valid_at, cache=cache
            ),
            amount=coop_share_transaction.total_price,
            mandate_ref=coop_share_transaction.mandate_ref,
            status=Payment.PaymentStatus.DUE,
            type=PAYMENT_TYPE_COOP_SHARES,
            coop_share_transaction=coop_share_transaction,
        )

    @classmethod
    def create_instalment_payments(
        cls, coop_share_transaction: CoopShareTransaction, cache: dict
    ) -> list[Payment]:
        instalment_amount = get_parameter_value(
            key=ParameterKeys.COOP_SHARES_INSTALMENT_AMOUNT, cache=cache
        )
        first_due_date = cls.get_payment_due_date(
            shares_valid_at=coop_share_transaction.valid_at, cache=cache
        )
        number_of_instalments = int(
            coop_share_transaction.total_price / instalment_amount
        )

        return Payment.objects.bulk_create(
            [
                Payment(
                    due_date=first_due_date + relativedelta(months=index),
                    amount=instalment_amount,
                    mandate_ref=coop_share_transaction.mandate_ref,
                    status=Payment.PaymentStatus.DUE,
                    type=PAYMENT_TYPE_COOP_SHARES,
                    coop_share_transaction=coop_share_transaction,
                    instalment_number=index + 1,
                )
                for index in range(number_of_instalments)
            ]
        )

    @classmethod
    def get_payment_due_date(cls, shares_valid_at: datetime.date, cache: dict):
        due_date = shares_valid_at.replace(day=1) + relativedelta(
            day=get_parameter_value(ParameterKeys.PAYMENT_DUE_DAY, cache=cache)
        )
        if due_date < shares_valid_at:
            due_date = due_date + relativedelta(months=1)
        return due_date

    @classmethod
    def send_warning_mail_if_necessary(
        cls, quantity: int, member: Member, shares_valid_at: datetime.date, cache: dict
    ):
        threshold = get_parameter_value(
            key=ParameterKeys.COOP_THRESHOLD_WARNING_ON_MANY_COOP_SHARES_BOUGHT,
            cache=cache,
        )
        if quantity < threshold:
            return

        _partial = partial(
            send_email,
            to_email=[
                get_parameter_value(key=ParameterKeys.SITE_ADMIN_EMAIL, cache=cache)
            ],
            subject=f"Warnung: es wurden mehr als {threshold} Genossenschaftsanteile gezeichnet- bitte prüfen",
            content=f"Bestehendes Mitglied oder Neuanmeldung: {member.get_display_name()} mit Mail-Adresse {member.email} hat gerade {quantity} Genossenschaftsanteile gezeichnet. Die Anteile sind ab dem {format_date(shares_valid_at)} gültig. Bitte an Vorstand zur Prüfung weiterleiten.",
            attachments=[],
            cache=cache,
        )
        transaction.on_commit(_partial)
