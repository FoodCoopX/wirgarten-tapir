import uuid
from django.core.cache import cache
from django.db import transaction

from tapir.utils.services.data_import_mapping_service import (
    CELL_NEUTRAL,
    DO_NOT_IMPORT,
    DataImportMappingService,
)
from tapir.utils.services.data_import_service import IMPORT_TYPES
from tapir.utils.services.tabular_file_reader import TabularFileReader
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.utils import get_today
from tapir.wirgarten.models import PickupLocation

DATA_IMPORT_CACHE_PREFIX = "data_import:"
DATA_IMPORT_CACHE_SECONDS = 3600
EXPIRED = "Die hochgeladene Datei ist abgelaufen, bitte noch einmal hochladen."


class DataImportWizardService:
    @staticmethod
    def _key(token):
        return DATA_IMPORT_CACHE_PREFIX + token

    @classmethod
    def load(cls, token):
        return cache.get(cls._key(token)) if token else None

    @classmethod
    def save(cls, token, state):
        cache.set(cls._key(token), state, DATA_IMPORT_CACHE_SECONDS)

    @classmethod
    def delete(cls, token):
        cache.delete(cls._key(token))

    @staticmethod
    def new_token():
        return uuid.uuid4().hex

    @classmethod
    def upload(cls, file, import_types, update_existing):
        data = TabularFileReader.read(file, file.name)
        headers = [header for header in data.headers if header]
        cache_data = {}
        fields = DataImportMappingService.build_semantic_fields(
            import_types, cache=cache_data
        )
        mapping = DataImportMappingService.auto_map(headers, fields)
        token = cls.new_token()
        suggested_defaults = []
        if "subscriptions" in import_types:
            period = TapirCache.get_growing_period_at_date(
                get_today(cache={}), cache={}
            )
            if period:
                suggested_defaults = [
                    {
                        "key": "subscriptions:Vertragsbeginn",
                        "value": period.start_date.isoformat(),
                    },
                    {
                        "key": "subscriptions:Vertragsende",
                        "value": period.end_date.isoformat(),
                    },
                ]
        distinct_values = []
        for header in headers:
            counts = {}
            for row in data.rows:
                value = DataImportMappingService.normalize_pickup_value(
                    row.get(header, "")
                )
                if value:
                    counts[value] = counts.get(value, 0) + 1
            distinct_values.append(
                {
                    "header": header,
                    "values": (
                        [
                            {"value": value, "count": count}
                            for value, count in counts.items()
                        ]
                        if len(counts) <= 100
                        else []
                    ),
                    "capped": len(counts) > 100,
                }
            )
        existing_locations = list(PickupLocation.objects.values("id", "name"))
        cls.save(
            token,
            {
                "stage": "mapping",
                "selected_type_keys": import_types,
                "update_existing": update_existing,
                "headers": headers,
                "rows": data.rows,
                "filename": file.name,
                "mapping": mapping,
                "defaults": {},
                "options": {},
                "overrides": {},
            },
        )
        return token, {
            "token": token,
            "filename": file.name,
            "selected_type_names": [IMPORT_TYPES[key].name for key in import_types],
            "columns": [
                {"index": i, "header": h, "selected_key": mapping.get(h, DO_NOT_IMPORT)}
                for i, h in enumerate(headers)
            ],
            "semantic_fields": [
                {
                    "key": f.key,
                    "label": f.label,
                    "kind": f.kind,
                    "required": f.required,
                    "allows_default": f.allows_default,
                    "required_unless_product_columns": f.required_unless_product_columns,
                }
                for f in fields
            ],
            "preview_rows": [
                [row.get(h, "") for h in headers] for row in data.rows[:200]
            ],
            "total_rows": len(data.rows),
            "suggested_defaults": suggested_defaults,
            "pickup_locations": existing_locations,
            "distinct_values": distinct_values,
        }

    @classmethod
    def effective_rows(cls, state):
        rows = [dict(row) for row in state["rows"]]
        for index, overrides in state.get("overrides", {}).items():
            rows[int(index)].update(overrides)
        return rows

    @classmethod
    def _review(cls, state):
        cache_data = {}
        fields = DataImportMappingService.build_semantic_fields(
            state["selected_type_keys"], cache=cache_data
        )
        rows_data = cls.effective_rows(state)
        assigned_member_numbers = DataImportMappingService.assigned_member_numbers(
            rows_data, state["mapping"], cache=cache_data
        )
        outcomes = DataImportMappingService.evaluate(
            state["selected_type_keys"],
            fields,
            state["mapping"],
            state["headers"],
            rows_data,
            state["update_existing"],
            state.get("defaults", {}),
            state.get("pickup_location_mapping", {}),
            assigned_member_numbers,
            options=state.get("options", {}),
        )
        extra_fields = [
            f
            for f in fields
            if f.key not in state["mapping"].values()
            and f.key in state.get("defaults", {})
        ]
        rows = []
        for outcome in outcomes:
            if not outcome.relevant:
                continue
            cells = []
            for header in state["headers"]:
                key = state["mapping"].get(header)
                original_value = state["rows"][outcome.index].get(header, "")
                value = rows_data[outcome.index].get(header, "")
                if outcome.index in assigned_member_numbers and key == "member_no":
                    value = str(assigned_member_numbers[outcome.index])
                if key in state.get("defaults", {}) and not str(value).strip():
                    value = state["defaults"][key]
                edited = header in state.get("overrides", {}).get(
                    str(outcome.index), {}
                )
                cell = {
                    "value": value,
                    "state": outcome.cell_states.get(header, CELL_NEUTRAL),
                    "editable": bool(key) and outcome.editable,
                }
                if edited:
                    cell.update({"edited": True, "original_value": original_value})
                if state.get("update_existing") and header in outcome.old_values:
                    cell["old_value"] = outcome.old_values[header]
                cells.append(cell)
            cells.extend(
                {
                    "value": state["defaults"][f.key],
                    "state": "default",
                    "editable": False,
                }
                for f in extra_fields
            )
            rows.append(
                {
                    "index": outcome.index,
                    "line": outcome.line,
                    "valid": outcome.valid,
                    "status": outcome.status,
                    "editable": outcome.editable,
                    "cells": cells,
                    "messages": outcome.messages,
                }
            )
        state["valid_row_indices"] = [
            o.index for o in outcomes if o.valid and o.status in {"new", "changed"}
        ]
        state["editable_row_indices"] = [o.index for o in outcomes if o.editable]
        state["assigned_member_numbers"] = assigned_member_numbers
        return {
            "headers": state["headers"]
            + [f"{f.label} (Standardwert)" for f in extra_fields],
            "rows": rows,
            "valid_count": sum(r["valid"] for r in rows),
            "invalid_count": sum(not r["valid"] for r in rows),
            "status_counts": {
                status: sum(r["status"] == status for r in rows)
                for status in ("new", "changed", "unchanged", "existing", "invalid")
            },
        }

    @classmethod
    def map(
        cls,
        token,
        mapping_items,
        default_items=None,
        pickup_location_mapping_items=None,
        options=None,
        update_existing=None,
    ):
        state = cls.load(token)
        if state is None or state.get("stage") not in ("mapping", "review"):
            return None, {"detail": EXPIRED}
        cache_data = {}
        options = options or {}
        if update_existing is not None:
            state["update_existing"] = update_existing
        fields = DataImportMappingService.build_semantic_fields(
            state["selected_type_keys"], cache=cache_data
        )
        field_keys = {field.key for field in fields}
        default_keys = {field.key for field in fields if field.allows_default}
        defaults = {}
        for item in default_items or []:
            key = item.get("key")
            value = item.get("value", "")
            if key in default_keys and value is not None and str(value).strip():
                field = next(field for field in fields if field.key == key)
                defaults[key] = DataImportMappingService.normalize_cell_value(
                    field.kind, str(value).strip()
                )
        errors = []
        for field in fields:
            if (
                field.key in defaults
                and not DataImportMappingService.validate_cell_format(
                    field.kind, defaults[field.key]
                )
            ):
                errors.append(
                    f'Standardwert für "{field.label}" hat ein ungültiges Format: {defaults[field.key]}'
                )
        mapping = {header: DO_NOT_IMPORT for header in state["headers"]}
        for item in mapping_items:
            index, key = item["column_index"], item.get("key", DO_NOT_IMPORT)
            if index < len(state["headers"]):
                mapping[state["headers"][index]] = (
                    key if key in field_keys else DO_NOT_IMPORT
                )
        pickup_location_mapping = {
            DataImportMappingService.normalize_pickup_value(
                item.get("value", "")
            ): item.get("target", "")
            for item in (pickup_location_mapping_items or [])
            if item.get("value", "").strip()
        }
        try:
            DataImportMappingService.validate_pickup_mapping(pickup_location_mapping)
        except ValueError as error:
            errors.append(str(error))

        missing = DataImportMappingService.missing_required_fields(
            mapping, fields, defaults, options
        )
        duplicates = DataImportMappingService.duplicate_targets(mapping)
        if duplicates:
            errors.append(
                "Jedes Ziel darf nur einer Spalte zugeordnet werden: "
                + ", ".join(f.label for f in fields if f.key in duplicates)
            )
        if missing:
            errors.append(
                "Diese Pflichtfelder sind noch keiner Spalte zugeordnet: "
                + ", ".join(f.label for f in missing)
            )
        state["mapping"] = mapping
        state["defaults"] = defaults
        state["pickup_location_mapping"] = pickup_location_mapping
        if errors:
            state["stage"] = "mapping"
            cls.save(token, state)
            return None, {"mapping_errors": errors}
        state["options"] = options
        state["stage"] = "review"
        review = cls._review(state)
        cls.save(token, state)
        return review, None

    @classmethod
    def edit_cell(cls, token, row_index, header, value):
        state = cls.load(token)
        if state is None or state.get("stage") != "review":
            return None, {"detail": EXPIRED}
        if header not in state["headers"] or not state["mapping"].get(header):
            return None, {"detail": "Diese Spalte ist nicht zugeordnet."}
        if row_index not in state.get("editable_row_indices", []):
            return None, {"detail": "Diese Zeile kann nicht bearbeitet werden."}
        if row_index < 0 or row_index >= len(state["rows"]):
            return None, {"detail": "Diese Zeile ist ungültig."}
        original = state["rows"][row_index].get(header, "")
        overrides = state.setdefault("overrides", {})
        row_overrides = overrides.setdefault(str(row_index), {})
        if value == original:
            row_overrides.pop(header, None)
            if not row_overrides:
                overrides.pop(str(row_index), None)
        else:
            row_overrides[header] = value
        review = cls._review(state)
        cls.save(token, state)
        return review, None

    @classmethod
    def apply(cls, token, row_indices):
        state = cls.load(token)
        if state is None or state.get("stage") != "review":
            return None, {"detail": EXPIRED}
        requested = set(row_indices)
        if requested - set(state.get("valid_row_indices", [])):
            return None, {
                "detail": "Die Auswahl enthält ungültige oder nicht geprüfte Zeilen, es wurde nichts übernommen."
            }
        if not requested:
            return None, {"detail": "Keine gültige Zeile ausgewählt."}
        fields = DataImportMappingService.build_semantic_fields(
            state["selected_type_keys"], cache={}
        )
        row_indices = sorted(requested)
        pickup_location_mapping = DataImportMappingService.pickup_mapping_used_by_rows(
            cls.effective_rows(state),
            row_indices,
            state["mapping"],
            state.get("pickup_location_mapping", {}),
        )
        try:
            with transaction.atomic():
                count = DataImportMappingService.apply_rows(
                    state["selected_type_keys"],
                    fields,
                    state["mapping"],
                    cls.effective_rows(state),
                    row_indices,
                    state["update_existing"],
                    state.get("defaults", {}),
                    pickup_location_mapping,
                    state.get("assigned_member_numbers", {}),
                    state.get("options", {}),
                )
        except (RuntimeError, ValueError) as error:
            return None, {
                "detail": f"Übernahme aus {state['filename']} abgebrochen, es wurde nichts gespeichert: {error}"
            }
        cls.delete(token)
        names = ", ".join(IMPORT_TYPES[key].name for key in state["selected_type_keys"])
        created_count = sum(
            1 for target in pickup_location_mapping.values() if target == "create"
        )
        message = f"{names} aus {state['filename']} übernommen: {count} Zeilen."
        if created_count:
            message += f" {created_count} Abholorte angelegt."
        return {"count": count, "message": message}, None
