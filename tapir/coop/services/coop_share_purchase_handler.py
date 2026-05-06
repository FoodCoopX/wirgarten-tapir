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
    MandateReference,
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
    ):
        mandate_ref = MandateReferenceProvider.get_or_create_mandate_reference(
            member=member, cache=cache
        )

        payment = cls.create_or_update_payment(
            shares_valid_at=shares_valid_at,
            mandate_ref=mandate_ref,
            quantity=quantity,
            cache=cache,
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
            payment=payment,
        )

        now = get_now(cache=cache)
        if member.sepa_consent != now:
            member.sepa_consent = get_now(cache=cache)
            member.save(cache=cache)

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
    def create_or_update_payment(
        cls,
        shares_valid_at: datetime.date,
        mandate_ref: MandateReference,
        quantity: int,
        cache: dict,
    ) -> Payment:
        share_price = get_parameter_value(ParameterKeys.COOP_SHARE_PRICE, cache=cache)
        due_date = cls.get_payment_due_date(
            shares_valid_at=shares_valid_at, cache=cache
        )

        existing_payment = Payment.objects.filter(
            due_date=due_date,
            mandate_ref=mandate_ref,
            status=Payment.PaymentStatus.DUE,
            type=PAYMENT_TYPE_COOP_SHARES,
        ).first()
        if existing_payment is not None:
            existing_payment.amount = (
                float(existing_payment.amount) + share_price * quantity
            )
            existing_payment.save()
            return existing_payment

        return Payment.objects.create(
            due_date=due_date,
            amount=share_price * quantity,
            mandate_ref=mandate_ref,
            status=Payment.PaymentStatus.DUE,
            type=PAYMENT_TYPE_COOP_SHARES,
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
