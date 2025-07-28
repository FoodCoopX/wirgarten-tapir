import datetime

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db import transaction

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import (
    Member,
    MandateReference,
    Payment,
    CoopShareTransaction,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.email import send_email
from tapir.wirgarten.service.member import get_or_create_mandate_ref
from tapir.wirgarten.utils import get_now, format_date


class CoopSharePurchaseHandler:
    @classmethod
    def buy_cooperative_shares(
        cls,
        quantity: int,
        member: Member,
        shares_valid_at: datetime.date,
        cache: dict,
    ):
        mandate_ref = get_or_create_mandate_ref(member=member, cache=cache)

        payment = cls.create_or_update_payment(
            shares_valid_at=shares_valid_at,
            mandate_ref=mandate_ref,
            quantity=quantity,
            cache=cache,
        )

        coop_share_tx = CoopShareTransaction.objects.create(
            member=member,
            quantity=quantity,
            share_price=settings.COOP_SHARE_PRICE,
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

        return coop_share_tx

    @classmethod
    def create_or_update_payment(
        cls,
        shares_valid_at: datetime.date,
        mandate_ref: MandateReference,
        quantity: int,
        cache: dict,
    ) -> Payment:
        share_price = settings.COOP_SHARE_PRICE
        due_date = cls.get_payment_due_date(
            shares_valid_at=shares_valid_at, cache=cache
        )

        payment_type = "Genossenschaftsanteile"
        existing_payment = Payment.objects.filter(
            due_date=due_date,
            mandate_ref=mandate_ref,
            status=Payment.PaymentStatus.DUE,
            type=payment_type,
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
            type=payment_type,
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

        transaction.on_commit(
            lambda: send_email(
                to_email=[
                    get_parameter_value(key=ParameterKeys.SITE_ADMIN_EMAIL, cache=cache)
                ],
                subject=f"Warnung: es wurden mehr als {threshold} Genossenschaftsanteile gezeichnet- bitte prüfen",
                content=f"Bestehendes Mitglied oder Neuanmeldung: {member.get_display_name()} mit Mail-Adresse {member.email} hat gerade {quantity} Genossenschaftsanteile gezeichnet. Die Anteile sind ab dem {format_date(shares_valid_at)} gültig. Bitte an Vorstand zur Prüfung weiterleiten.",
            )
        )
