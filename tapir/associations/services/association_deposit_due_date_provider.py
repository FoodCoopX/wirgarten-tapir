from django.core.exceptions import ValidationError
from django.db.models import Q

from tapir.associations.models import AssociationMembership, AssociationDepositAccount
from tapir.payments.services.mandate_reference_provider import MandateReferenceProvider
from tapir.payments.services.payment_due_date_calculator import PaymentDueDateCalculator
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import get_now, get_today


class AssociationDepositDueDateProvider:
    @staticmethod
    def get_first_due_date(
        member: Member, account: AssociationDepositAccount, cache: dict
    ):
        if not member.sepa_consent or member.sepa_consent > get_now(cache=cache):
            raise ValidationError(
                "Für den Einzug ist eine gültige SEPA-Zustimmung erforderlich."
            )
        cache.pop(MandateReferenceProvider.CACHE_KEY, None)
        mandate = MandateReferenceProvider.get_mandate_ref(member, cache)
        earliest = max(
            account.effective_from,
            get_today(cache),
            mandate.start_ts.date() if mandate else get_today(cache),
        )
        memberships = (
            AssociationMembership.objects.filter(member=member)
            .filter(Q(end_date=None) | Q(end_date__gte=earliest))
            .order_by("start_date")
        )
        for membership in memberships:
            candidate = PaymentDueDateCalculator.get_first_due_date_on_or_after(
                max(earliest, membership.start_date), cache
            )
            if membership.end_date is None or candidate <= membership.end_date:
                return candidate
        raise ValidationError(
            "Für den Einzug ist eine gültige Vereinsmitgliedschaft erforderlich."
        )
