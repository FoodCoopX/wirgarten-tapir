"""Column mapping, cell validation and combined (members -> shares -> subscriptions) dry
run / apply for the data import page.

A single uploaded file may cover several import types at once (one row = one member with,
optionally, a share movement and a subscription). The user maps every source column to a
"semantic field": a target understood by one or more importers. The member number is the only
field shared between all three importers (as "Nr", "Mitgliedsnummer" or "Mitgliedernummer");
every other target is specific to one import type.
"""

import re
import unicodedata
from dataclasses import dataclass, field

from django.db import transaction

from tapir.utils.exceptions import DryRunException
from tapir.utils.services.data_import_service import IMPORT_TYPES
from tapir.utils.services.data_import_utils import DataImportUtils

# Sentinel used in <select> options and posted mapping values for "do not import this column".
DO_NOT_IMPORT = ""

IMPORT_TYPE_ORDER = ("members", "shares", "subscriptions")

CELL_NEUTRAL = "neutral"
CELL_VALID = "valid"
CELL_INVALID = "invalid"
CELL_WARN = "warn"

# The member number is the only column shared between the three importers.
SHARED_FIELDS = {
    "member_no": {
        "label": "Mitgliedsnummer",
        "kind": "int",
        "columns": {
            "members": "Nr",
            "shares": "Mitgliedsnummer",
            "subscriptions": "Mitgliedernummer",
        },
    },
}

# Columns whose value must parse into a specific format. Anything not listed here is treated as
# free text, i.e. any non-empty value is format-valid.
FIELD_KINDS = {
    "Anzahl Anteile": "int",
    "Quantity": "int",
    "Solidarpreis in EUR": "decimal",
    "Personalisierter Betrag": "decimal",
    "Geburtstag/Gründungsdatum": "date",
    "AO_gueltig_ab": "date",
    "Solidarpreis Start_Date": "date",
    "Solidarpreis End_Date": "date",
    "Vereinsmitgliedschaft Start_Date": "date",
    "Vereinsmitgliedschaft End_Date": "date",
    "Datum": "date",
    "Vertragsbeginn": "date",
    "Vertragsende": "date",
    "Ende Probezeit (Sonntag)": "date",
    "consent_sepa": "datetime",
    "privacy_consent": "datetime",
    "consent_vertragsgrundsätze": "datetime",
    "consent_widerruf": "datetime",
    "cancellation.ts": "datetime",
    "Mailadresse": "email",
    "Email": "email",
}

GERMAN_CHAR_MAP = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}

# Known German/English synonyms, keyed by semantic field key ("member_no" or
# "<import_type>:<column>"). The column's own name(s) always auto-map (see build_candidates);
# these are only extra, less exact header texts.
SYNONYMS = {
    "member_no": [
        "mitgliedsnummer",
        "mitgliedernummer",
        "mitgliedsnr",
        "mitglied nr",
        "mitglieds-nr",
        "mitglieder-nr",
        "member no",
        "member number",
        "membernumber",
        "memberno",
        "nummer",
        "kundennummer",
    ],
    "members:Vorname": ["vorname", "first name", "firstname", "vname"],
    "members:Nachname": [
        "nachname",
        "last name",
        "lastname",
        "surname",
        "familienname",
        "nname",
    ],
    "members:Mailadresse": [
        "email",
        "e-mail",
        "emailadresse",
        "e-mail-adresse",
        "mail",
        "mailadresse",
    ],
    "members:consent_sepa": [
        "sepa zustimmung",
        "sepa-zustimmung",
        "sepa einverständnis",
        "sepa consent",
        "sepa mandat datum",
    ],
    "members:Anrede": ["anrede", "salutation", "titel"],
    "members:Straße": ["straße", "strasse", "street"],
    "members:Hausnr.": ["hausnr", "hausnummer", "house number", "housenumber"],
    "members:PLZ": ["plz", "postleitzahl", "zip", "zip code", "zipcode", "postal code"],
    "members:Ort": ["ort", "stadt", "city", "town"],
    "members:Telefon": ["telefon", "phone", "tel", "telefonnummer", "phone number"],
    "members:Telefon 2": ["telefon 2", "telefon2", "phone 2", "phone2", "tel 2"],
    "members:IBAN": ["iban"],
    "members:Kontoinhaber": [
        "kontoinhaber",
        "account holder",
        "accountholder",
        "kontoinhaberin",
    ],
    "members:privacy_consent": [
        "datenschutz",
        "datenschutzzustimmung",
        "privacy consent",
    ],
    "members:Pseudonym": ["pseudonym", "nickname", "spitzname"],
    "members:Abholort": ["abholort", "pickup location", "pickup", "abholstelle"],
    "members:AO_gueltig_ab": [
        "abholort gültig ab",
        "abholort gueltig ab",
        "pickup valid from",
    ],
    "members:Zahlungsintervall": [
        "zahlungsintervall",
        "payment interval",
        "payment rhythm",
        "zahlungsrhythmus",
    ],
    "members:Solidarpreis in EUR": [
        "solidarpreis",
        "solidarity price",
        "solidaritätsbeitrag",
    ],
    "members:Solidarpreis Start_Date": [
        "solidarpreis start",
        "solidarity price start",
    ],
    "members:Solidarpreis End_Date": ["solidarpreis ende", "solidarity price end"],
    "members:Vereinsmitgliedschafttyp": [
        "vereinsmitgliedschaft typ",
        "association membership type",
    ],
    "members:Vereinsmitgliedschaft Start_Date": [
        "vereinsmitgliedschaft start",
    ],
    "members:Vereinsmitgliedschaft End_Date": [
        "vereinsmitgliedschaft ende",
    ],
    "shares:Bewegungsart (Z,Ü,K)": [
        "bewegungsart",
        "movement type",
        "art der bewegung",
    ],
    "shares:Datum": ["datum", "date"],
    "shares:Anzahl Anteile": [
        "anzahl anteile",
        "number of shares",
        "anzahl der anteile",
        "shares",
    ],
    "shares:Übertragungspartner": [
        "übertragungspartner",
        "uebertragungspartner",
        "transfer partner",
    ],
    "shares:Wirkung Kündigung": ["wirkung kündigung", "wirkung kuendigung"],
    "subscriptions:product": ["product", "produkt"],
    "subscriptions:Quantity": ["quantity", "menge", "anzahl"],
    "subscriptions:Vertragsbeginn": [
        "vertragsbeginn",
        "contract start",
        "start date",
        "startdate",
    ],
    "subscriptions:Vertragsende": [
        "vertragsende",
        "contract end",
        "end date",
        "enddate",
    ],
    "subscriptions:Email": ["email", "e-mail", "mail"],
    "subscriptions:product_type": ["product_type", "produkttyp", "product type"],
    "subscriptions:Probezeit": ["probezeit", "trial period", "trial"],
    "subscriptions:Ende Probezeit (Sonntag)": ["ende probezeit", "trial end"],
    "subscriptions:Personalisierter Betrag": [
        "personalisierter betrag",
        "personalized amount",
        "individual amount",
    ],
    "subscriptions:consent_vertragsgrundsätze": [
        "consent_vertragsgrundsaetze",
        "vertragsgrundsätze zustimmung",
    ],
    "subscriptions:consent_widerruf": [
        "widerruf zustimmung",
        "withdrawal consent",
    ],
    "subscriptions:cancellation.ts": [
        "kündigung zeitstempel",
        "cancellation timestamp",
    ],
}


@dataclass
class RowOutcome:
    index: int
    line: int
    relevant: bool
    valid: bool
    cell_states: dict[str, str] = field(default_factory=dict)
    messages: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SemanticField:
    key: str
    label: str
    kind: str
    import_columns: dict[str, str]  # import_type key -> importer column name
    required_for: tuple[str, ...]  # import_type keys this field is required for

    @property
    def required(self) -> bool:
        return bool(self.required_for)


class DataImportMappingService:
    @classmethod
    def build_semantic_fields(cls, selected_type_keys) -> list[SemanticField]:
        """One field per distinct target. The member number is merged into a single field
        across all selected import types; everything else is specific to one import type.
        """
        fields: list[SemanticField] = []
        consumed_columns: dict[str, set[str]] = {}

        for shared_key, shared_def in SHARED_FIELDS.items():
            import_columns = {}
            required_for = []
            for type_key, column in shared_def["columns"].items():
                if type_key not in selected_type_keys:
                    continue
                import_type = IMPORT_TYPES[type_key]
                if column not in import_type.columns:
                    continue
                import_columns[type_key] = column
                consumed_columns.setdefault(type_key, set()).add(column)
                if column in import_type.required_columns:
                    required_for.append(type_key)
            if not import_columns:
                continue
            label = shared_def["label"]
            if len(import_columns) > 1:
                names = ", ".join(
                    IMPORT_TYPES[type_key].name for type_key in import_columns
                )
                label = f"{label} ({names})"
            fields.append(
                SemanticField(
                    key=shared_key,
                    label=label,
                    kind=shared_def["kind"],
                    import_columns=import_columns,
                    required_for=tuple(required_for),
                )
            )

        for type_key in selected_type_keys:
            import_type = IMPORT_TYPES[type_key]
            used = consumed_columns.get(type_key, set())
            for column in import_type.columns:
                if column in used:
                    continue
                key = f"{type_key}:{column}"
                required_for = (
                    (type_key,) if column in import_type.required_columns else ()
                )
                fields.append(
                    SemanticField(
                        key=key,
                        label=f"{column} ({import_type.name})",
                        kind=FIELD_KINDS.get(column, "text"),
                        import_columns={type_key: column},
                        required_for=required_for,
                    )
                )
        return fields

    @staticmethod
    def normalize_header(name: str | None) -> str:
        """Case/whitespace/punctuation tolerant normalisation used to match source headers
        against importer column names and known synonyms."""
        if not name:
            return ""
        name = name.strip().lower()
        for german, ascii_version in GERMAN_CHAR_MAP.items():
            name = name.replace(german, ascii_version)
        name = unicodedata.normalize("NFKD", name)
        name = "".join(c for c in name if not unicodedata.combining(c))
        return re.sub(r"[^a-z0-9]+", "", name)

    @classmethod
    def build_candidates(cls, semantic_fields: list[SemanticField]) -> dict[str, str]:
        """Normalised header text -> semantic field key. Own importer column names always win;
        synonyms only fill in gaps and the first field to claim a synonym keeps it."""
        candidates: dict[str, str] = {}
        for semantic_field in semantic_fields:
            for column in semantic_field.import_columns.values():
                candidates[cls.normalize_header(column)] = semantic_field.key
        for semantic_field in semantic_fields:
            for synonym in SYNONYMS.get(semantic_field.key, []):
                normalized = cls.normalize_header(synonym)
                candidates.setdefault(normalized, semantic_field.key)
        return candidates

    @classmethod
    def auto_map(
        cls, headers: list[str], semantic_fields: list[SemanticField]
    ) -> dict[str, str]:
        """Source header -> semantic field key. At most one header per target."""
        candidates = cls.build_candidates(semantic_fields)
        mapping: dict[str, str] = {}
        used_keys: set[str] = set()
        for header in headers:
            if not header:
                continue
            key = candidates.get(cls.normalize_header(header))
            if key and key not in used_keys:
                mapping[header] = key
                used_keys.add(key)
        return mapping

    @staticmethod
    def missing_required_fields(
        mapping: dict[str, str], semantic_fields: list[SemanticField]
    ) -> list[SemanticField]:
        mapped_keys = {key for key in mapping.values() if key}
        return [f for f in semantic_fields if f.required and f.key not in mapped_keys]

    @staticmethod
    def duplicate_targets(mapping: dict[str, str]) -> set[str]:
        seen: set[str] = set()
        duplicates: set[str] = set()
        for key in mapping.values():
            if not key:
                continue
            if key in seen:
                duplicates.add(key)
            seen.add(key)
        return duplicates

    @staticmethod
    def validate_cell_format(kind: str, value: str) -> bool:
        value = DataImportUtils.normalize_cell(value)
        if kind == "int":
            return DataImportUtils.safe_int(value, default=None) is not None
        if kind == "decimal":
            return DataImportUtils.safe_float(value, default=None) is not None
        if kind == "date":
            return DataImportUtils.to_date(value) is not None
        if kind == "datetime":
            return DataImportUtils.to_datetime(value) is not None
        if kind == "email":
            return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value))
        return True

    @classmethod
    def build_mapped_row(
        cls,
        raw_row: dict[str, str],
        mapping: dict[str, str],
        semantic_fields: list[SemanticField],
        type_key: str,
    ) -> dict[str, str]:
        """Builds the row in the shape the importer for ``type_key`` expects: keyed by its own
        column names (e.g. "Nr"), not by the original source header."""
        header_by_key = {key: header for header, key in mapping.items() if key}
        mapped_row: dict[str, str] = {}
        for semantic_field in semantic_fields:
            column = semantic_field.import_columns.get(type_key)
            if not column:
                continue
            header = header_by_key.get(semantic_field.key)
            mapped_row[column] = raw_row.get(header, "") if header else ""
        return mapped_row

    @classmethod
    def column_has_any_value(cls, raw_rows: list[dict[str, str]], header: str) -> bool:
        return any(
            DataImportUtils.normalize_cell(row.get(header, "")) for row in raw_rows
        )

    @classmethod
    def compute_row_cell_states(
        cls,
        raw_row: dict[str, str],
        headers: list[str],
        mapping: dict[str, str],
        fields_by_key: dict[str, SemanticField],
        column_has_value: dict[str, bool],
    ) -> tuple[dict[str, str], list[str]]:
        cell_states: dict[str, str] = {}
        format_errors: list[str] = []
        for header in headers:
            key = mapping.get(header)
            if not key:
                cell_states[header] = CELL_NEUTRAL
                continue
            semantic_field = fields_by_key[key]
            value = DataImportUtils.normalize_cell(raw_row.get(header, ""))
            if value == "":
                if semantic_field.required:
                    cell_states[header] = CELL_INVALID
                    format_errors.append(
                        f'Pflichtfeld "{semantic_field.label}" ist leer'
                    )
                elif column_has_value.get(header):
                    cell_states[header] = CELL_WARN
                else:
                    cell_states[header] = CELL_NEUTRAL
                continue
            if cls.validate_cell_format(semantic_field.kind, value):
                cell_states[header] = CELL_VALID
            else:
                cell_states[header] = CELL_INVALID
                format_errors.append(
                    f'"{semantic_field.label}" hat ein ungültiges Format: {value}'
                )
        return cell_states, format_errors

    @staticmethod
    def is_row_relevant(raw_row: dict[str, str], mapping: dict[str, str]) -> bool:
        """A row is skipped (like the single-type importers already do) if none of its mapped
        cells carry a value."""
        return any(
            DataImportUtils.normalize_cell(raw_row.get(header, ""))
            for header, key in mapping.items()
            if key
        )

    @classmethod
    def dry_run_row(
        cls,
        selected_type_keys: list[str],
        mapped_rows_by_type: dict[str, dict[str, str]],
        update_existing: bool,
    ) -> tuple[bool, list[str]]:
        """Runs the selected importers for one row, members -> shares -> subscriptions, all
        rolled back at the end (dry run never touches Keycloak, see DataImportService.run).
        """
        messages: list[str] = []
        try:
            with transaction.atomic():
                for type_key in IMPORT_TYPE_ORDER:
                    if type_key not in selected_type_keys:
                        continue
                    import_type = IMPORT_TYPES[type_key]
                    try:
                        import_type.importer(
                            row=mapped_rows_by_type[type_key],
                            update_existing=update_existing,
                        )
                    except Exception as error:
                        raise RuntimeError(
                            f"{import_type.name}: {str(error) or error.__class__.__name__}"
                        ) from error
                raise DryRunException()
        except DryRunException:
            return True, messages
        except RuntimeError as error:
            return False, [str(error)]

    @classmethod
    def evaluate(
        cls,
        selected_type_keys: list[str],
        semantic_fields: list[SemanticField],
        mapping: dict[str, str],
        headers: list[str],
        raw_rows: list[dict[str, str]],
        update_existing: bool,
    ) -> list[RowOutcome]:
        """Cell-level format validation plus a dry run of the selected importers, in order,
        for every non-empty row. Nothing is ever saved here."""
        fields_by_key = {f.key: f for f in semantic_fields}
        column_has_value = {
            header: cls.column_has_any_value(raw_rows, header)
            for header in headers
            if mapping.get(header)
        }
        outcomes: list[RowOutcome] = []
        for index, raw_row in enumerate(raw_rows):
            line = index + 2  # line 1 holds the headers
            if not cls.is_row_relevant(raw_row, mapping):
                outcomes.append(
                    RowOutcome(index=index, line=line, relevant=False, valid=False)
                )
                continue

            cell_states, format_errors = cls.compute_row_cell_states(
                raw_row, headers, mapping, fields_by_key, column_has_value
            )
            if format_errors:
                outcomes.append(
                    RowOutcome(
                        index=index,
                        line=line,
                        relevant=True,
                        valid=False,
                        cell_states=cell_states,
                        messages=format_errors,
                    )
                )
                continue

            mapped_rows_by_type = {
                type_key: cls.build_mapped_row(
                    raw_row, mapping, semantic_fields, type_key
                )
                for type_key in selected_type_keys
            }
            valid, messages = cls.dry_run_row(
                selected_type_keys, mapped_rows_by_type, update_existing
            )
            outcomes.append(
                RowOutcome(
                    index=index,
                    line=line,
                    relevant=True,
                    valid=valid,
                    cell_states=cell_states,
                    messages=messages,
                )
            )
        return outcomes

    @classmethod
    def apply_row(
        cls,
        selected_type_keys: list[str],
        mapped_rows_by_type: dict[str, dict[str, str]],
        update_existing: bool,
    ) -> None:
        """Runs the selected importers for one row for real. Raises on the first failure so the
        caller's outer transaction rolls back every selected row."""
        for type_key in IMPORT_TYPE_ORDER:
            if type_key not in selected_type_keys:
                continue
            import_type = IMPORT_TYPES[type_key]
            try:
                import_type.importer(
                    row=mapped_rows_by_type[type_key], update_existing=update_existing
                )
            except Exception as error:
                raise RuntimeError(
                    f"{import_type.name}: {str(error) or error.__class__.__name__}"
                ) from error

    @classmethod
    def apply_rows(
        cls,
        selected_type_keys: list[str],
        semantic_fields: list[SemanticField],
        mapping: dict[str, str],
        raw_rows: list[dict[str, str]],
        row_indices: list[int],
        update_existing: bool,
    ) -> int:
        """Applies the given rows for real, all in one transaction: if any of them fails the
        whole batch is rolled back, nothing is saved (requirement: no partial apply)."""
        from tapir.utils.services.member_importer import MemberImporter

        keycloak_updates_before = MemberImporter.keycloak_updates_enabled
        MemberImporter.keycloak_updates_enabled = True
        try:
            with transaction.atomic():
                for index in row_indices:
                    raw_row = raw_rows[index]
                    mapped_rows_by_type = {
                        type_key: cls.build_mapped_row(
                            raw_row, mapping, semantic_fields, type_key
                        )
                        for type_key in selected_type_keys
                    }
                    cls.apply_row(
                        selected_type_keys, mapped_rows_by_type, update_existing
                    )
        finally:
            MemberImporter.keycloak_updates_enabled = keycloak_updates_before
        return len(row_indices)
