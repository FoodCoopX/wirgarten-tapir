from decimal import Decimal
from functools import partial

from tapir.associations.services.association_deposit_overview_provider import (
    AssociationDepositOverviewProvider,
)
from tapir.associations.services.association_deposit_policy import (
    AssociationDepositPolicy,
)
from tapir.generic_exports.services.export_segment_manager import ExportSegmentColumn
from tapir.wirgarten.utils import format_currency, legal_status_is_association


class AssociationDepositExportColumnProvider:
    @classmethod
    def get_columns(cls, cache: dict) -> list[ExportSegmentColumn]:
        try:
            if not legal_status_is_association(cache=cache):
                return []
        except KeyError:
            return []
        name = AssociationDepositPolicy.get_settings(cache)["name"]
        return [
            ExportSegmentColumn(
                id=f"association_deposit_{key}",
                display_name=f"{name}: {label} (aktueller Stand)",
                description="Aktueller Stand bei Erstellung, unabhängig vom Referenzdatum. Verbucht/exportiert bestätigt keinen Bankeingang.",
                get_value=partial(cls.get_value, key=key),
            )
            for key, label in AssociationDepositOverviewProvider.COLUMNS.items()
        ]

    @staticmethod
    def get_value(member, reference_datetime, cache: dict, *, key):
        return AssociationDepositOverviewProvider.get_row(member, cache)[key]

    @classmethod
    def get_csv_row(cls, member, cache: dict) -> dict:
        values = AssociationDepositOverviewProvider.get_row(member, cache)
        return {
            column.display_name: (
                format_currency(value) if isinstance(value, Decimal) else value or ""
            )
            for column, value in zip(
                cls.get_columns(cache),
                (values[key] for key in AssociationDepositOverviewProvider.COLUMNS),
            )
        }
