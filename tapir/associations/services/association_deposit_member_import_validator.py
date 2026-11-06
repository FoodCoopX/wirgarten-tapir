from django.core.exceptions import ValidationError

from tapir.associations.models import AssociationDepositAccount, AssociationMembership
from tapir.utils.services.data_import_utils import DataImportUtils


class AssociationDepositMemberImportValidator:
    @staticmethod
    def preserve_membership(member, row: dict, cache: dict) -> bool:
        if not AssociationDepositAccount.objects.filter(member=member).exists():
            return False
        fields = {
            key: DataImportUtils.normalize_cell(row.get(key))
            for key in (
                "Vereinsmitgliedschafttyp",
                "Vereinsmitgliedschaft Start_Date",
                "Vereinsmitgliedschaft End_Date",
            )
        }
        supplied = {key: value for key, value in fields.items() if value}
        if not supplied:
            return True
        memberships = list(
            AssociationMembership.objects.filter(member=member).select_related("type")
        )
        if len(memberships) == 1:
            membership = memberships[0]
            expected = {
                "Vereinsmitgliedschafttyp": membership.type.name,
                "Vereinsmitgliedschaft Start_Date": membership.start_date,
                "Vereinsmitgliedschaft End_Date": membership.end_date,
            }
            if all(
                (
                    value
                    if key == "Vereinsmitgliedschafttyp"
                    else DataImportUtils.to_date(value)
                )
                == expected[key]
                and (
                    key == "Vereinsmitgliedschafttyp"
                    or DataImportUtils.to_date(value) is not None
                )
                for key, value in supplied.items()
            ):
                return True
        raise ValidationError(
            "Geschützte Vereinsmitgliedschaft mit Einlagenkonto: historische oder geänderte Mitgliedschaften bitte über die Verwaltung bearbeiten; Import wurde vor Profil-/Keycloak-Änderungen abgebrochen."
        )
