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
from localflavor.generic.validators import IBANValidator

from tapir.utils.services.data_import_service import IMPORT_TYPES, discarded_stdout
from tapir.utils.config import (
    MEMBER_IMPORT_STATUS_CREATED,
    MEMBER_IMPORT_STATUS_UPDATED,
)
from tapir.utils.services.data_import_utils import (
    DataImportUtils,
    collect_data_import_changes,
)
from tapir.wirgarten.models import (
    Member,
    PickupLocation,
    PickupLocationCapability,
    Product,
    ProductType,
    Subscription,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.utils import get_today
from tapir.coop.services.member_number_service import MemberNumberService

# Sentinel used in <select> options and posted mapping values for "do not import this column".
DO_NOT_IMPORT = ""

IMPORT_TYPE_ORDER = ("members", "shares", "subscriptions")

CELL_NEUTRAL = "neutral"
CELL_VALID = "valid"
CELL_INVALID = "invalid"
CELL_WARN = "warn"
CELL_DROPPED = "dropped"
CELL_DEFAULT = "default"

DROPPABLE_KINDS = {"iban"}

# Person-specific values where a shared default value would make no sense.
NO_DEFAULT_FIELD_KEYS = {"member_no", "email"}
NO_DEFAULT_COLUMNS = {
    "Vorname",
    "Nachname",
    "Mailadresse",
    "Email",
    "Telefon",
    "Telefon 2",
    "IBAN",
    "Straße",
    "Hausnr.",
    "PLZ",
    "Ort",
}

# Fields shared between importers are mapped once and copied to each importer.
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
    "email": {
        "label": "Mailadresse",
        "kind": "email",
        "columns": {
            "members": "Mailadresse",
            "subscriptions": "Email",
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
    "IBAN": "iban",
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
    "email": ["mail 1", "mail", "e-mail", "email", "mailadresse"],
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
    "members:Abholort": [
        "abholort",
        "pickup location",
        "pickup",
        "abholstelle",
        "depot",
        "verteilstelle",
    ],
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
        "vertragsdatum",
        "vertrags datum",
        "vetragsdatum",
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
    status: str = "invalid"
    editable: bool = True
    old_values: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SemanticField:
    key: str
    label: str
    kind: str
    import_columns: dict[str, str]  # import_type key -> importer column name
    required_for: tuple[str, ...]  # import_type keys this field is required for
    required_unless_product_columns: bool = False
    product_id: str | None = None
    product_name: str | None = None
    product_type_name: str | None = None
    allows_default_override: bool | None = None

    @property
    def required(self) -> bool:
        return bool(self.required_for)

    @property
    def allows_default(self) -> bool:
        if self.allows_default_override is not None:
            return self.allows_default_override
        return self.key not in NO_DEFAULT_FIELD_KEYS and not any(
            column in NO_DEFAULT_COLUMNS for column in self.import_columns.values()
        )


class DataImportMappingService:
    @staticmethod
    def normalize_pickup_value(value: str) -> str:
        return " ".join(str(value).strip().split())

    @classmethod
    def pickup_mapping_for_row(cls, raw_row, mapping, pickup_location_mapping):
        header = next(
            (h for h, key in mapping.items() if key == "members:Abholort"), None
        )
        if header is None or not pickup_location_mapping:
            return raw_row
        value = cls.normalize_pickup_value(raw_row.get(header, ""))
        target = pickup_location_mapping.get(value)
        if not value or target is None:
            return raw_row
        transformed = dict(raw_row)
        if target == "skip":
            transformed[header] = ""
        elif target == "create":
            transformed[header] = value
        elif target.startswith("existing:"):
            transformed[header] = PickupLocation.objects.get(
                pk=target.removeprefix("existing:")
            ).name
        return transformed

    @classmethod
    def pickup_mapping_used_by_rows(
        cls,
        raw_rows: list[dict[str, str]],
        row_indices: list[int],
        mapping: dict[str, str],
        pickup_location_mapping: dict[str, str],
    ) -> dict[str, str]:
        header = next(
            (h for h, key in mapping.items() if key == "members:Abholort"), None
        )
        if header is None:
            return {}
        used_values = {
            cls.normalize_pickup_value(raw_rows[index].get(header, ""))
            for index in row_indices
        }
        return {
            value: target
            for value, target in pickup_location_mapping.items()
            if value in used_values
        }

    @classmethod
    def validate_pickup_mapping(cls, pickup_location_mapping):
        for value, target in pickup_location_mapping.items():
            value = cls.normalize_pickup_value(value)
            if not value:
                raise ValueError(
                    "Abholort-Zuordnungen dürfen keinen leeren Wert enthalten."
                )
            if target == "create":
                if PickupLocation.objects.filter(name=value).exists():
                    raise ValueError(f'Abholort "{value}" existiert bereits.')
            elif target == "skip":
                continue
            elif target.startswith("existing:"):
                if not PickupLocation.objects.filter(
                    pk=target.removeprefix("existing:")
                ).exists():
                    raise ValueError(f'Abholort-Zuordnung für "{value}" ist ungültig.')
            else:
                raise ValueError(f'Abholort-Zuordnung für "{value}" ist ungültig.')

    @classmethod
    def create_pickup_locations(cls, pickup_location_mapping):
        created = {}
        for value, target in pickup_location_mapping.items():
            if target != "create":
                continue
            name = cls.normalize_pickup_value(value)
            location = PickupLocation.objects.create(
                name=name, street="", postcode="", city=""
            )
            PickupLocationCapability.objects.bulk_create(
                [
                    PickupLocationCapability(
                        product_type=product_type, pickup_location=location
                    )
                    for product_type in ProductType.objects.all()
                ]
            )
            created[name] = location
        return created

    @classmethod
    def build_semantic_fields(
        cls, selected_type_keys, cache: dict | None = None
    ) -> list[SemanticField]:
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
                        required_unless_product_columns=(
                            type_key == "subscriptions"
                            and column in {"product", "Quantity"}
                        ),
                        allows_default_override=(
                            False
                            if column == "Kontoinhaber"
                            else (
                                False
                                if column == "consent_sepa"
                                and "subscriptions" in selected_type_keys
                                else None
                            )
                        ),
                    )
                )
        if "subscriptions" in selected_type_keys:
            cache = cache if cache is not None else {}
            today = get_today(cache=cache)
            period = TapirCache.get_growing_period_at_date(today, cache=cache)
            products = list(
                Product.objects.filter(
                    deleted=False,
                    productprice__valid_from__lte=(
                        period.end_date if period else today
                    ),
                )
                .distinct()
                .select_related("type")
            )
            products.sort(key=lambda product: (product.type.name, product.name))
            for product in products:
                fields.append(
                    SemanticField(
                        key=f"product:{product.pk}",
                        label=f"Menge: {product.type.name} – {product.name}",
                        kind="quantity",
                        import_columns={},
                        required_for=(),
                        product_id=str(product.pk),
                        product_name=product.name,
                        product_type_name=product.type.name,
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
        product_fields = [f for f in semantic_fields if f.kind == "quantity"]
        by_name = {}
        by_type = {}
        for field in product_fields:
            product = Product.objects.select_related("type").get(pk=field.product_id)
            by_name.setdefault(cls.normalize_header(product.name), []).append(field)
            by_type.setdefault(cls.normalize_header(product.type.name), []).append(
                field
            )
        for normalized in set(by_name) | set(by_type):
            matches = {field.key for field in by_name.get(normalized, [])}
            matches.update(field.key for field in by_type.get(normalized, []))
            if len(matches) == 1:
                candidates.setdefault(normalized, next(iter(matches)))
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
        mapping: dict[str, str],
        semantic_fields: list[SemanticField],
        defaults: dict[str, str] | None = None,
        options: dict[str, bool] | None = None,
    ) -> list[SemanticField]:
        options = options or {}
        mapped_keys = {key for key in mapping.values() if key}
        defaults = defaults or {}
        return [
            f
            for f in semantic_fields
            if f.required
            and not (
                (
                    f.key == "members:consent_sepa"
                    and options.get("sepa_consent_from_contract_start")
                    and ("members:consent_sepa" not in mapped_keys)
                    and (
                        "subscriptions:Vertragsbeginn" in mapped_keys
                        or "subscriptions:Vertragsbeginn" in defaults
                    )
                )
            )
            and not (
                f.required_unless_product_columns
                and any(key.startswith("product:") for key in mapped_keys)
            )
            and f.key not in mapped_keys
            and not (
                f.allows_default
                and DataImportUtils.normalize_cell(defaults.get(f.key, ""))
            )
        ]

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
        if kind == "quantity":
            return bool(re.fullmatch(r"(?:0|[1-9]\d*)", str(value)))
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
        if kind == "iban":
            try:
                IBANValidator()(re.sub(r"\s+", "", value).upper())
            except Exception:
                return False
        return True

    @staticmethod
    def normalize_cell_value(kind: str, value: str) -> str:
        if kind == "iban":
            value = DataImportUtils.normalize_cell(value)
            return re.sub(r"\s+", "", value).upper()
        return value

    @staticmethod
    def derived_value(
        key: str,
        raw_row: dict[str, str],
        mapping: dict[str, str],
        defaults: dict[str, str],
        options: dict[str, bool],
    ) -> str:
        """Value for an empty cell derived from other columns, as enabled by the mapping options."""

        def mapped_value(target_key: str) -> str:
            header = next((h for h, k in mapping.items() if k == target_key), None)
            return str(raw_row.get(header, "")).strip() if header else ""

        if key == "members:Kontoinhaber" and options.get("account_owner_from_name"):
            names = (mapped_value("members:Vorname"), mapped_value("members:Nachname"))
            return " ".join(name for name in names if name)
        if key == "members:consent_sepa" and options.get(
            "sepa_consent_from_contract_start"
        ):
            return mapped_value("subscriptions:Vertragsbeginn") or defaults.get(
                "subscriptions:Vertragsbeginn", ""
            )
        return ""

    @classmethod
    def build_mapped_row(
        cls,
        raw_row: dict[str, str],
        mapping: dict[str, str],
        semantic_fields: list[SemanticField],
        type_key: str,
        defaults: dict[str, str] | None = None,
        options: dict[str, bool] | None = None,
    ) -> dict[str, str]:
        """Builds the row in the shape the importer for ``type_key`` expects: keyed by its own
        column names (e.g. "Nr"), not by the original source header."""
        header_by_key = {key: header for header, key in mapping.items() if key}
        defaults = defaults or {}
        options = options or {}
        mapped_row: dict[str, str] = {}
        for semantic_field in semantic_fields:
            column = semantic_field.import_columns.get(type_key)
            if not column:
                continue
            header = header_by_key.get(semantic_field.key)
            value = raw_row.get(header, "") if header else ""
            if not DataImportUtils.normalize_cell(value):
                value = cls.derived_value(
                    semantic_field.key, raw_row, mapping, defaults, options
                )
            if (
                not DataImportUtils.normalize_cell(value)
                and semantic_field.key in defaults
            ):
                value = defaults[semantic_field.key]
            value = cls.normalize_cell_value(semantic_field.kind, value)
            if (
                semantic_field.kind in DROPPABLE_KINDS
                and value
                and not cls.validate_cell_format(semantic_field.kind, value)
            ):
                # Left out entirely so that the importer keeps the member's current value.
                continue
            mapped_row[column] = value
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
        defaults: dict[str, str] | None = None,
        options: dict[str, bool] | None = None,
    ) -> tuple[dict[str, str], list[str], list[str]]:
        cell_states: dict[str, str] = {}
        format_errors: list[str] = []
        dropped_messages: list[str] = []
        defaults = defaults or {}
        options = options or {}
        for header in headers:
            key = mapping.get(header)
            if not key:
                cell_states[header] = CELL_NEUTRAL
                continue
            semantic_field = fields_by_key[key]
            value = DataImportUtils.normalize_cell(raw_row.get(header, ""))
            if value == "":
                value = DataImportUtils.normalize_cell(
                    cls.derived_value(
                        semantic_field.key, raw_row, mapping, defaults, options
                    )
                )
            used_default = value == "" and semantic_field.key in defaults
            if used_default:
                value = DataImportUtils.normalize_cell(defaults[semantic_field.key])
                cell_states[header] = CELL_DEFAULT
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
                if not used_default:
                    cell_states[header] = CELL_VALID
            elif semantic_field.kind in DROPPABLE_KINDS:
                cell_states[header] = CELL_DROPPED
                dropped_messages.append(
                    f'IBAN "{value}" ist ungültig, Mitglied wird ohne IBAN übernommen'
                )
            else:
                cell_states[header] = CELL_INVALID
                if semantic_field.kind == "quantity":
                    format_errors.append(
                        f'Menge "{value}" für {semantic_field.label.removeprefix("Menge: ")}: nur ganze Zahlen möglich'
                    )
                else:
                    format_errors.append(
                        f'"{semantic_field.label}" hat ein ungültiges Format: {value}'
                    )
        return cell_states, format_errors, dropped_messages

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
    def assigned_member_numbers(cls, raw_rows, mapping, cache: dict) -> dict[int, int]:
        member_header = next(
            (h for h, key in mapping.items() if key == "member_no"), None
        )
        if member_header is None:
            return {}
        numeric_values = []
        for row in raw_rows:
            value = DataImportUtils.normalize_cell(row.get(member_header, ""))
            try:
                numeric_values.append(int(value))
            except (TypeError, ValueError):
                pass
        next_number = max(
            MemberNumberService.compute_next_member_number(cache=cache),
            (max(numeric_values) + 1) if numeric_values else 0,
        )
        assigned = {}
        for index, row in enumerate(raw_rows):
            value = (
                str(DataImportUtils.normalize_cell(row.get(member_header, "")))
                .strip()
                .lower()
            )
            if value not in {"pz", "pa"} or not cls.is_row_relevant(row, mapping):
                continue
            assigned[index] = next_number
            next_number += 1
        return assigned

    @classmethod
    def _row_for_import(cls, raw_row, mapping, assigned_number=None):
        if assigned_number is None:
            return raw_row
        member_header = next(
            (h for h, key in mapping.items() if key == "member_no"), None
        )
        transformed = dict(raw_row)
        if member_header:
            transformed[member_header] = str(assigned_number)
        return transformed

    @classmethod
    def prepare_raw_row(
        cls, raw_row, index, mapping, pickup_location_mapping, assigned_member_numbers
    ):
        prepared = cls.pickup_mapping_for_row(raw_row, mapping, pickup_location_mapping)
        return cls._row_for_import(
            prepared, mapping, (assigned_member_numbers or {}).get(index)
        )

    @classmethod
    def build_import_rows(
        cls,
        raw_row,
        index,
        selected_type_keys,
        semantic_fields,
        mapping,
        defaults,
        pickup_location_mapping,
        assigned_member_numbers,
        cache: dict,
        options: dict[str, bool] | None = None,
    ) -> dict[str, list[dict[str, str]]]:
        raw_row = cls.prepare_raw_row(
            raw_row, index, mapping, pickup_location_mapping, assigned_member_numbers
        )
        assigned_number = (assigned_member_numbers or {}).get(index)
        mapped_rows = {
            type_key: [
                cls.build_mapped_row(
                    raw_row, mapping, semantic_fields, type_key, defaults
                )
            ]
            for type_key in selected_type_keys
        }
        if "subscriptions" not in selected_type_keys:
            return mapped_rows
        subscription_row = mapped_rows["subscriptions"][0]
        if not DataImportUtils.normalize_cell(subscription_row.get("Probezeit")):
            subscription_row["Probezeit"] = (
                "true" if assigned_number is not None else "false"
            )
        product_fields = {
            field.key: field
            for field in semantic_fields
            if field.kind == "quantity" and field.product_id
        }
        mapped_product_keys = {
            key for key in mapping.values() if key.startswith("product:")
        }
        expanded = []
        if (
            "subscriptions:product" in mapping.values()
            and "subscriptions:Quantity" in mapping.values()
        ):
            expanded.append(dict(subscription_row))
        for key, field in product_fields.items():
            if key not in mapped_product_keys:
                continue
            header = next(h for h, mapped_key in mapping.items() if mapped_key == key)
            quantity = DataImportUtils.safe_int(
                DataImportUtils.normalize_cell(raw_row.get(header, "")), default=0
            )
            if quantity > 0:
                product_row = dict(subscription_row)
                product_row["product"] = field.product_name
                product_row["product_type"] = field.product_type_name
                product_row["Quantity"] = str(quantity)
                expanded.append(product_row)
        mapped_rows["subscriptions"] = expanded
        return mapped_rows

    @classmethod
    def dry_run_row(cls, selected_type_keys, mapped_rows_by_type, update_existing):
        messages = []
        statuses = []
        try:
            with collect_data_import_changes() as changes:
                with transaction.atomic():
                    for type_key in IMPORT_TYPE_ORDER:
                        if type_key not in selected_type_keys:
                            continue
                        import_type = IMPORT_TYPES[type_key]
                        for row in mapped_rows_by_type[type_key]:
                            try:
                                statuses.append(
                                    import_type.importer(
                                        row=row,
                                        update_existing=update_existing,
                                        dry_run=True,
                                        stdout=discarded_stdout(),
                                        **(
                                            {"match_by_growing_period": True}
                                            if type_key == "subscriptions"
                                            else {}
                                        ),
                                    )
                                )
                            except Exception as error:
                                raise RuntimeError(
                                    f"{import_type.name}: {str(error) or error.__class__.__name__}"
                                ) from error
                    transaction.set_rollback(True)
            return True, messages, statuses, changes
        except RuntimeError as error:
            return False, [str(error)], statuses, changes

    @staticmethod
    def row_status(
        valid: bool, statuses: list, member_existed: bool, update_existing: bool
    ) -> str:
        if not valid:
            return "invalid"
        if any(
            status in {MEMBER_IMPORT_STATUS_CREATED, MEMBER_IMPORT_STATUS_UPDATED}
            for status in statuses
        ):
            return "changed" if member_existed else "new"
        if member_existed and not update_existing:
            return "existing"
        return "unchanged"

    @classmethod
    def subscription_change_messages(cls, changes) -> list[str]:
        labels = {"quantity": "Menge", "end_date": "Vertragsende"}
        return [
            f"{change.instance.product.name}: {labels[change.field]} "
            f"{cls._format_old_value(change.old_value)} → "
            f"{cls._format_old_value(change.new_value)}"
            for change in changes
            if isinstance(change.instance, Subscription) and change.field in labels
        ]

    @staticmethod
    def _format_old_value(value):
        if value is None:
            return ""
        if hasattr(value, "strftime"):
            return value.strftime("%d.%m.%Y")
        return str(value)

    @classmethod
    def _old_values_for_row(cls, changes, mapping):
        attribute_to_columns = {
            "first_name": "members:Vorname",
            "last_name": "members:Nachname",
            "birthdate": "members:Geburtstag/Gründungsdatum",
            "form_of_address": "members:Anrede",
            "postcode": "members:PLZ",
            "city": "members:Ort",
            "phone_number": "members:Telefon",
            "phone_number_landline": "members:Telefon 2",
            "iban": "members:IBAN",
            "account_owner": "members:Kontoinhaber",
            "pseudonym": "members:Pseudonym",
            "street": "members:Straße",
            "sepa_consent": "members:consent_sepa",
            "privacy_consent": "members:privacy_consent",
        }
        old = {}
        for change in changes:
            key = attribute_to_columns.get(change.field)
            if not key:
                continue
            header = next((h for h, mapped in mapping.items() if mapped == key), None)
            if header is not None:
                old[header] = cls._format_old_value(change.old_value)
        return old

    @classmethod
    def evaluate(
        cls,
        selected_type_keys,
        semantic_fields,
        mapping,
        headers,
        raw_rows,
        update_existing,
        defaults=None,
        pickup_location_mapping=None,
        assigned_member_numbers=None,
        options=None,
    ):
        fields_by_key = {f.key: f for f in semantic_fields}
        defaults = defaults or {}
        pickup_location_mapping = pickup_location_mapping or {}
        column_has_value = {
            header: cls.column_has_any_value(raw_rows, header)
            for header in headers
            if mapping.get(header)
        }
        outcomes = []
        with transaction.atomic():
            cls.validate_pickup_mapping(pickup_location_mapping)
            cls.create_pickup_locations(pickup_location_mapping)
            for index, original_row in enumerate(raw_rows):
                raw_row = cls.prepare_raw_row(
                    original_row,
                    index,
                    mapping,
                    pickup_location_mapping,
                    assigned_member_numbers,
                )
                line = index + 2
                if not cls.is_row_relevant(raw_row, mapping):
                    outcomes.append(
                        RowOutcome(index=index, line=line, relevant=False, valid=False)
                    )
                    continue
                cell_states, format_errors, dropped_messages = (
                    cls.compute_row_cell_states(
                        raw_row,
                        headers,
                        mapping,
                        fields_by_key,
                        column_has_value,
                        defaults,
                        options,
                    )
                )
                assigned_number = (assigned_member_numbers or {}).get(index)
                if assigned_number is not None:
                    member_header = next(
                        h for h, key in mapping.items() if key == "member_no"
                    )
                    cell_states[member_header] = CELL_DEFAULT
                    dropped_messages.append(
                        f"Probezeit/Probeabo: Mitgliedsnummer {assigned_number} wird automatisch vergeben, Verträge mit Probezeit"
                    )
                pickup_header = next(
                    (h for h, key in mapping.items() if key == "members:Abholort"), None
                )
                pickup_value = (
                    cls.normalize_pickup_value(original_row.get(pickup_header, ""))
                    if pickup_header
                    else ""
                )
                target = pickup_location_mapping.get(pickup_value)
                if target == "skip" and pickup_value:
                    cell_states[pickup_header] = CELL_DROPPED
                    dropped_messages.append(
                        f'Abholort "{pickup_value}" wird nicht zugeordnet, Mitglied wird ohne Abholort übernommen'
                    )
                elif target == "create" and pickup_value:
                    cell_states[pickup_header] = CELL_VALID
                    dropped_messages.append(
                        f'Abholort "{pickup_value}" wird neu angelegt'
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
                mapped_rows_by_type = cls.build_import_rows(
                    original_row,
                    index,
                    selected_type_keys,
                    semantic_fields,
                    mapping,
                    defaults,
                    pickup_location_mapping,
                    assigned_member_numbers,
                    cache={},
                    options=options,
                )
                quantity_messages = []
                for subscription_row in mapped_rows_by_type.get("subscriptions", []):
                    quantity_messages.append(
                        f'{subscription_row.get("Quantity")}× {subscription_row.get("product")}'
                    )
                member_no = DataImportUtils.safe_int(
                    next(
                        (
                            v
                            for h, k in mapping.items()
                            if k == "member_no"
                            for v in [raw_row.get(h)]
                        ),
                        "",
                    ),
                    default=-1,
                )
                member_existed = Member.objects.filter(member_no=member_no).exists()
                valid, messages, statuses, changes = cls.dry_run_row(
                    selected_type_keys, mapped_rows_by_type, update_existing
                )
                status = cls.row_status(
                    valid, statuses, member_existed, update_existing
                )
                if status == "changed" and not update_existing and member_existed:
                    messages.insert(
                        0, "Mitglied besteht bereits, wird nicht aktualisiert"
                    )
                messages.extend(cls.subscription_change_messages(changes))
                outcomes.append(
                    RowOutcome(
                        index=index,
                        line=line,
                        relevant=True,
                        valid=valid,
                        cell_states=cell_states,
                        messages=dropped_messages + quantity_messages + messages,
                        status=status,
                        old_values=cls._old_values_for_row(changes, mapping),
                        editable=status in {"new", "changed", "invalid"}
                        or (status == "unchanged" and update_existing),
                    )
                )
            transaction.set_rollback(True)
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
            for row in mapped_rows_by_type[type_key]:
                try:
                    import_type.importer(
                        row=row,
                        update_existing=update_existing,
                        dry_run=False,
                        stdout=discarded_stdout(),
                        **(
                            {"match_by_growing_period": True}
                            if type_key == "subscriptions"
                            else {}
                        ),
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
        defaults: dict[str, str] | None = None,
        pickup_location_mapping: dict[str, str] | None = None,
        assigned_member_numbers: dict[int, int] | None = None,
        options: dict[str, bool] | None = None,
    ) -> int:
        """Applies the given rows for real, all in one transaction: if any of them fails the
        whole batch is rolled back, nothing is saved (requirement: no partial apply)."""
        pickup_location_mapping = pickup_location_mapping or {}
        with transaction.atomic():
            cls.validate_pickup_mapping(pickup_location_mapping)
            cls.create_pickup_locations(pickup_location_mapping)
            for index in row_indices:
                mapped_rows_by_type = cls.build_import_rows(
                    raw_rows[index],
                    index,
                    selected_type_keys,
                    semantic_fields,
                    mapping,
                    defaults or {},
                    pickup_location_mapping,
                    assigned_member_numbers,
                    cache={},
                    options=options,
                )
                cls.apply_row(selected_type_keys, mapped_rows_by_type, update_existing)
        return len(row_indices)
