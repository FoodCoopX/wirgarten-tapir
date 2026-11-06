from django.core.exceptions import ValidationError

from tapir.associations.models import AssociationDepositAccount
from tapir.utils.shortcuts import get_from_cache_or_compute


class AssociationDepositImportDeletionValidator:
    @staticmethod
    def validate_member_reset_is_safe(cache: dict):
        if get_from_cache_or_compute(
            cache=cache,
            key="association_deposit_accounts_exist",
            compute_function=lambda: AssociationDepositAccount.objects.exists(),
        ):
            raise ValidationError(
                "Mitglieder mit Einlagenkonten dürfen nicht gesammelt gelöscht werden. "
                "Einlagen- und Zahlungshistorie müssen erhalten bleiben. "
                "Bitte den Import ohne --reset-all und ohne --delete-all für Mitglieder ausführen."
            )
