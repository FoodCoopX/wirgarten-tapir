import hashlib
import json
from decimal import Decimal

from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction

from tapir.associations.services.association_deposit_membership_coverage import (
    AssociationDepositMembershipCoverage,
)
from tapir.associations.models import AssociationMembership
from tapir.associations.services.association_deposit_details_provider import (
    AssociationDepositDetailsProvider,
)
from tapir.associations.services.association_deposit_due_date_provider import (
    AssociationDepositDueDateProvider,
)
from tapir.associations.services.association_deposit_instalment_calculator import (
    AssociationDepositInstalmentCalculator,
)
from tapir.associations.services.association_deposit_policy import (
    AssociationDepositPolicy,
)
from tapir.wirgarten.models import Member, Payment, MandateReference


class AssociationDepositIncreasePreview:
    SIGNING_SALT = "association_deposit_increase"

    @classmethod
    @transaction.atomic
    def build_preview(cls, member: Member, total_amount: Decimal, cache: dict) -> dict:
        member = Member.objects.select_for_update(no_key=True).get(pk=member.pk)
        AssociationDepositMembershipCoverage.invalidate_member(member, cache)
        account = AssociationDepositPolicy.get_increasable_account(member, cache)
        AssociationDepositPolicy.validate_increase_amount(account, total_amount, cache)
        details = AssociationDepositDetailsProvider.get_deposit_details(member, cache)
        remaining = max(
            Decimal("0"),
            total_amount - details["retained_amount"],
        )
        pending = list(
            account.payments.filter(
                transaction=None, status=Payment.PaymentStatus.DUE
            ).order_by("due_date", "instalment_number", "pk")
        )
        first_due = AssociationDepositDueDateProvider.get_first_due_date(
            member, account, cache
        )
        if pending:
            schedule = AssociationDepositInstalmentCalculator.adjust_open_payments(
                remaining, account.instalment_count, pending, allow_increase=True
            )
        else:
            schedule = (
                AssociationDepositInstalmentCalculator.build_payment_schedule(
                    remaining, account.instalment_count, first_due, cache
                )
                if remaining
                else []
            )
        snapshot = {
            "revision": account.agreement_revision,
            "amount": account.agreed_amount,
            "individual": account.is_individual_agreement,
            "count": account.instalment_count,
            "effective_from": account.effective_from,
            "settings": details["settings"],
            "payments": list(
                account.payments.order_by("pk").values(
                    "pk",
                    "amount",
                    "due_date",
                    "status",
                    "transaction_id",
                    "mandate_ref_id",
                    "instalment_number",
                )
            ),
            "receipts": list(
                account.receipts.order_by("pk").values("pk", "amount", "received_on")
            ),
            "memberships": list(
                AssociationMembership.objects.filter(member=member)
                .order_by("pk")
                .values("pk", "type_id", "start_date", "end_date", "cancellation_ts")
            ),
            "mandates": list(
                MandateReference.objects.filter(member=member)
                .order_by("pk")
                .values("pk", "ref", "start_ts")
            ),
            "sepa_consent": member.sepa_consent,
            "iban": member.iban,
            "account_owner": member.account_owner,
            "proposed": schedule,
        }
        fingerprint = hashlib.sha256(
            json.dumps(snapshot, default=str, sort_keys=True).encode()
        ).hexdigest()
        return {
            "total_amount": total_amount,
            "received_amount": details["received_amount"],
            "committed_amount": details["committed_amount"],
            "pending_amount": sum((rate["amount"] for rate in schedule), Decimal("0")),
            "payments": schedule,
            "confirmation": signing.dumps(
                {
                    "member": member.pk,
                    "total": str(total_amount.quantize(Decimal("0.01"))),
                    "fingerprint": fingerprint,
                },
                salt=cls.SIGNING_SALT,
            ),
        }

    @classmethod
    def validate_confirmation(
        cls, member: Member, total_amount: Decimal, confirmation: str, cache: dict
    ):
        try:
            confirmed = signing.loads(confirmation, salt=cls.SIGNING_SALT, max_age=900)
            current = signing.loads(
                cls.build_preview(member, total_amount, cache)["confirmation"],
                salt=cls.SIGNING_SALT,
            )
        except signing.BadSignature as error:
            raise ValidationError(
                "Die Vorschau ist nicht mehr gültig. Bitte neu laden und erneut bestätigen."
            ) from error
        if confirmed != current:
            raise ValidationError(
                "Vereinbarung oder Zahlungsstand wurden inzwischen geändert. Bitte die neue Vorschau prüfen und erneut bestätigen."
            )
