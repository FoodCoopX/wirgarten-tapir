import datetime
import hashlib
import json
import uuid
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import DecimalValidator, MinValueValidator
from django.db import IntegrityError, transaction

from tapir.associations.services.association_deposit_membership_coverage import (
    AssociationDepositMembershipCoverage,
)
from tapir.accounts.models import TapirUser
from tapir.associations.models import (
    AssociationDepositAccount,
    AssociationDepositAgreementAuthorizedLogEntry,
)
from tapir.associations.services.association_deposit_payment_synchronizer import (
    AssociationDepositPaymentSynchronizer,
)
from tapir.associations.services.association_deposit_instalment_calculator import (
    AssociationDepositInstalmentCalculator,
)
from tapir.associations.services.association_deposit_policy import (
    AssociationDepositPolicy,
)
from tapir.log.util import freeze_for_log
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import Member, Payment
from tapir.wirgarten.utils import get_today


class AssociationDepositAgreementAuthorizer:
    @staticmethod
    @transaction.atomic
    def authorize_agreement(
        member: Member,
        amount: Decimal,
        effective_from: datetime.date,
        instalment_count: int,
        consented_on: datetime.date,
        consent_note: str,
        expected_revision: int,
        request_key: uuid.UUID,
        actor: TapirUser,
        cache: dict,
    ) -> AssociationDepositAccount:
        if actor is None or not actor.has_perm(Permission.Coop.MANAGE):
            raise PermissionDenied
        amount, consent_note = AssociationDepositAgreementAuthorizer._validate_inputs(
            amount, instalment_count, expected_revision, consent_note
        )
        request_hash = hashlib.sha256(
            json.dumps(
                [
                    member.pk,
                    str(amount.quantize(Decimal("0.01"))),
                    effective_from.isoformat(),
                    instalment_count,
                    consented_on.isoformat(),
                    consent_note,
                    expected_revision,
                ]
            ).encode()
        ).hexdigest()
        Member.objects.select_for_update(no_key=True).get(pk=member.pk)
        AssociationDepositMembershipCoverage.invalidate_member(member, cache)
        previous = AssociationDepositAgreementAuthorizedLogEntry.objects.filter(
            request_key=request_key
        ).first()
        if previous:
            if previous.user_id != member.pk or previous.request_hash != request_hash:
                raise ValidationError(
                    "Dieser Anfrageschlüssel wurde bereits mit anderen Daten verwendet."
                )
            return AssociationDepositAccount.objects.get(member=member)
        if not AssociationDepositPolicy.is_enabled(cache):
            raise ValidationError("Vereinseinlagen sind nicht aktiviert.")
        AssociationDepositAgreementAuthorizer._validate_new_terms(
            amount, effective_from, instalment_count, consented_on, cache
        )
        account, _ = AssociationDepositAccount.objects.get_or_create(member=member)
        if account.agreement_revision != expected_revision:
            raise ValidationError(
                "Die Vereinbarung wurde inzwischen geändert. Bitte den aktuellen Stand laden."
            )
        cutoff = AssociationDepositMembershipCoverage.get_collection_cutoff(
            account, cache
        )
        if (
            cutoff
            and AssociationDepositMembershipCoverage.requires_new_agreement(
                account, cache
            )
            and effective_from < cutoff
        ):
            raise ValidationError(
                "Die neue Vereinbarung muss nach der bisherigen Mitgliedschaftsphase beginnen."
            )
        old = freeze_for_log(account)
        old_payments = [
            freeze_for_log(payment)
            for payment in account.payments.filter(
                transaction=None, status=Payment.PaymentStatus.DUE
            ).order_by("due_date", "pk")
        ]
        account.refund_requires_agreement = False
        account.collection_stopped_from = None
        account.agreed_amount = amount
        account.effective_from = effective_from
        account.instalment_count = instalment_count
        account.is_individual_agreement = True
        account.agreement_revision += 1
        account.save(
            update_fields=[
                "refund_requires_agreement",
                "collection_stopped_from",
                "agreed_amount",
                "effective_from",
                "instalment_count",
                "is_individual_agreement",
                "agreement_revision",
                "updated_at",
            ]
        )
        AssociationDepositPaymentSynchronizer.replace_unexported_payment_plan(
            member, actor, cache
        )
        values = freeze_for_log(account)
        values.update(
            consented_on=consented_on.isoformat(),
            consent_note=consent_note,
            previous_agreement=json.dumps(old, sort_keys=True),
            previous_payments=json.dumps(old_payments, sort_keys=True),
            payments=json.dumps(
                [
                    freeze_for_log(payment)
                    for payment in account.payments.filter(
                        transaction=None, status=Payment.PaymentStatus.DUE
                    ).order_by("due_date", "pk")
                ],
                sort_keys=True,
            ),
        )
        try:
            with transaction.atomic():
                AssociationDepositAgreementAuthorizedLogEntry(
                    request_key=request_key, request_hash=request_hash
                ).populate(frozen=values, actor=actor, user=member).save()
        except IntegrityError as error:
            if AssociationDepositAgreementAuthorizedLogEntry.objects.filter(
                request_key=request_key
            ).exists():
                raise ValidationError(
                    "Dieser Anfrageschlüssel wurde bereits verwendet."
                ) from error
            raise
        return account

    @staticmethod
    def _validate_inputs(amount, instalment_count, expected_revision, consent_note):
        DecimalValidator(max_digits=8, decimal_places=2)(amount)
        MinValueValidator(Decimal("0"))(amount)
        amount = amount.quantize(Decimal("0.01"))
        AssociationDepositInstalmentCalculator.validate_instalment_count(
            instalment_count
        )
        if type(expected_revision) is not int or expected_revision < 0:
            raise ValidationError("Bitte eine gültige Vereinbarungsrevision angeben.")
        consent_note = consent_note.strip()
        if not consent_note:
            raise ValidationError("Bitte die dokumentierte Zustimmung angeben.")
        return amount, consent_note

    @staticmethod
    def _validate_new_terms(
        amount, effective_from, instalment_count, consented_on, cache: dict
    ):
        today = get_today(cache)
        if effective_from < today or consented_on > today:
            raise ValidationError(
                "Neue Einzüge dürfen nicht rückdatiert werden; die Zustimmung darf nicht in der Zukunft liegen."
            )
        if amount == 0 and instalment_count != 1:
            raise ValidationError("Bei einem Verzicht ist kein Ratenplan erforderlich.")
