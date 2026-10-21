import uuid

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.cache import cache
from django.db import transaction
from django.http import Http404, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import FormView

from tapir.core.exceptions import TapirImproperlyConfigured
from tapir.utils.config import Organization
from tapir.utils.exceptions import TapirDataImportException
from tapir.utils.forms import DataImportForm, ResetTestDataForm
from tapir.utils.services.data_import_mapping_service import (
    CELL_NEUTRAL,
    DO_NOT_IMPORT,
    IMPORT_TYPE_ORDER,
    DataImportMappingService,
)
from tapir.utils.services.data_import_service import (
    IMPORT_TYPES,
    ActivationMailService,
    DataImportService,
)
from tapir.utils.services.tabular_file_reader import TabularFileReader
from tapir.utils.services.test_data_generation.data_generator import DataGenerator
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.utils import is_debug_instance


class ResetTestData(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    form_class = ResetTestDataForm
    permission_required = Permission.Coop.MANAGE
    template_name = "utils/reset_test_data.html"

    def get_success_url(self):
        return reverse("wirgarten:product")

    def form_valid(self, form):
        if not is_debug_instance():
            raise TapirImproperlyConfigured("Don't reset data on non-debug instances.")

        with transaction.atomic():
            DataGenerator.clear()
            DataGenerator.generate_all(
                Organization[form.cleaned_data["generate_test_data_for"]]
            )

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["page_title"] = "Reset test data"
        context_data["card_title"] = context_data["page_title"]
        return context_data


DATA_IMPORT_CACHE_PREFIX = "data_import:"
DATA_IMPORT_CACHE_SECONDS = 3600


def import_type_choices():
    return [
        (import_type.key, import_type.name) for import_type in IMPORT_TYPES.values()
    ]


class DataImportCacheMixin:
    """Shared helpers to store/load the upload, the column mapping and the dry run result for
    the multi-step data import wizard (upload -> map columns -> review & apply)."""

    @staticmethod
    def cache_key(token: str) -> str:
        return DATA_IMPORT_CACHE_PREFIX + token

    @classmethod
    def load(cls, token: str):
        return cache.get(cls.cache_key(token)) if token else None

    @classmethod
    def save(cls, token: str, stored: dict):
        cache.set(cls.cache_key(token), stored, DATA_IMPORT_CACHE_SECONDS)

    @classmethod
    def delete(cls, token: str):
        cache.delete(cls.cache_key(token))

    @staticmethod
    def new_token() -> str:
        return uuid.uuid4().hex


class DataImportView(
    LoginRequiredMixin, PermissionRequiredMixin, DataImportCacheMixin, FormView
):
    """Takes over existing data from Excel or CSV in three steps:
    1. upload the file for one or more types (members, shares, subscriptions),
    2. map every source column to a target field (auto-mapped, overridable),
    3. review the dry run per row (cell-level validation + combined importer dry run), select
       which valid rows to apply, then apply and send the activation mails.
    """

    form_class = DataImportForm
    permission_required = Permission.Coop.MANAGE
    template_name = "utils/data_import.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["import_type_choices"] = import_type_choices()
        return kwargs

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["page_title"] = "Datenübernahme"
        context_data["import_types"] = IMPORT_TYPES.values()
        context_data["members_without_login"] = (
            ActivationMailService.get_members_without_login().count()
        )
        context_data.setdefault("stage", "upload")
        return context_data

    def form_valid(self, form):
        selected_type_keys = [
            key for key in IMPORT_TYPE_ORDER if key in form.cleaned_data["import_types"]
        ]
        upload = form.cleaned_data["file"]
        try:
            data = TabularFileReader.read(upload, upload.name)
        except TapirDataImportException as error:
            form.add_error("file", str(error))
            return self.form_invalid(form)

        update_existing = form.cleaned_data["update_existing"]
        headers = [header for header in data.headers if header]
        semantic_fields = DataImportMappingService.build_semantic_fields(
            selected_type_keys
        )
        mapping = DataImportMappingService.auto_map(headers, semantic_fields)

        token = self.new_token()
        self.save(
            token,
            {
                "stage": "mapping",
                "selected_type_keys": selected_type_keys,
                "update_existing": update_existing,
                "headers": headers,
                "rows": data.rows,
                "filename": upload.name,
                "mapping": mapping,
            },
        )
        return self.render_mapping(form, token)

    def render_mapping(self, form, token: str, mapping_errors=None):
        stored = self.load(token)
        semantic_fields = DataImportMappingService.build_semantic_fields(
            stored["selected_type_keys"]
        )
        headers = stored["headers"]
        columns = [
            {
                "index": index,
                "header": header,
                "selected_key": stored["mapping"].get(header, DO_NOT_IMPORT),
            }
            for index, header in enumerate(headers)
        ]
        preview_rows = [
            [row.get(header, "") for header in headers] for row in stored["rows"][:200]
        ]
        return self.render_to_response(
            self.get_context_data(
                form=form,
                stage="mapping",
                token=token,
                filename=stored["filename"],
                selected_type_names=[
                    IMPORT_TYPES[key].name for key in stored["selected_type_keys"]
                ],
                semantic_fields=semantic_fields,
                columns=columns,
                preview_rows=preview_rows,
                total_rows=len(stored["rows"]),
                mapping_errors=mapping_errors or [],
            )
        )


class DataImportMappingView(
    LoginRequiredMixin, PermissionRequiredMixin, DataImportCacheMixin, View
):
    """Second 'Prüfen': receives the column mapping, enforces (server-side, independent of the
    client-side JS) that every required semantic field is mapped, then runs the combined dry
    run for every non-empty row."""

    permission_required = Permission.Coop.MANAGE

    def post(self, request, *args, **kwargs):
        token = request.POST.get("token", "")
        stored = self.load(token)
        if stored is None or stored.get("stage") not in ("mapping", "review"):
            messages.error(
                request,
                "Die hochgeladene Datei ist abgelaufen, bitte noch einmal hochladen.",
            )
            return redirect("utils:data_import")

        selected_type_keys = stored["selected_type_keys"]
        semantic_fields = DataImportMappingService.build_semantic_fields(
            selected_type_keys
        )
        semantic_keys = {f.key for f in semantic_fields}

        mapping = {}
        for index, header in enumerate(stored["headers"]):
            value = request.POST.get(f"col_{index}", DO_NOT_IMPORT)
            mapping[header] = value if value in semantic_keys else DO_NOT_IMPORT

        missing = DataImportMappingService.missing_required_fields(
            mapping, semantic_fields
        )
        duplicates = DataImportMappingService.duplicate_targets(mapping)

        mapping_errors = []
        if duplicates:
            duplicate_labels = [f.label for f in semantic_fields if f.key in duplicates]
            mapping_errors.append(
                "Jedes Ziel darf nur einer Spalte zugeordnet werden: "
                + ", ".join(duplicate_labels)
            )
        if missing:
            mapping_errors.append(
                "Diese Pflichtfelder sind noch keiner Spalte zugeordnet: "
                + ", ".join(f.label for f in missing)
            )

        stored["mapping"] = mapping
        if mapping_errors:
            stored["stage"] = "mapping"
            self.save(token, stored)
            form = DataImportForm(import_type_choices=import_type_choices())
            view = DataImportView()
            view.request = self.request
            return view.render_mapping(form, token, mapping_errors=mapping_errors)

        outcomes = DataImportMappingService.evaluate(
            selected_type_keys=selected_type_keys,
            semantic_fields=semantic_fields,
            mapping=mapping,
            headers=stored["headers"],
            raw_rows=stored["rows"],
            update_existing=stored["update_existing"],
        )
        stored["stage"] = "review"
        stored["valid_row_indices"] = [o.index for o in outcomes if o.valid]
        self.save(token, stored)
        return self.render_review(stored, token, outcomes)

    def render_review(self, stored, token, outcomes):
        view = DataImportView()
        view.request = self.request
        form = DataImportForm(import_type_choices=import_type_choices())
        rows = []
        for outcome in outcomes:
            if not outcome.relevant:
                continue
            cells = [
                {
                    "value": stored["rows"][outcome.index].get(header, ""),
                    "state": outcome.cell_states.get(header, CELL_NEUTRAL),
                }
                for header in stored["headers"]
            ]
            rows.append(
                {
                    "index": outcome.index,
                    "line": outcome.line,
                    "valid": outcome.valid,
                    "cells": cells,
                    "messages": outcome.messages,
                }
            )
        valid_count = sum(1 for row in rows if row["valid"])
        return view.render_to_response(
            view.get_context_data(
                form=form,
                stage="review",
                token=token,
                filename=stored["filename"],
                selected_type_names=[
                    IMPORT_TYPES[key].name for key in stored["selected_type_keys"]
                ],
                headers=stored["headers"],
                review_rows=rows,
                valid_count=valid_count,
                invalid_count=len(rows) - valid_count,
            )
        )


class DataImportApplyView(
    LoginRequiredMixin, PermissionRequiredMixin, DataImportCacheMixin, View
):
    permission_required = Permission.Coop.MANAGE

    def post(self, request, *args, **kwargs):
        token = request.POST.get("token", "")
        stored = self.load(token)
        if stored is None or stored.get("stage") != "review":
            messages.error(
                request,
                "Die hochgeladene Datei ist abgelaufen, bitte noch einmal hochladen.",
            )
            return redirect("utils:data_import")

        # Never trust the client: only row indices that were cached as valid by the last dry
        # run (DataImportMappingView.post) may be applied.
        allowed_indices = set(stored.get("valid_row_indices", []))
        try:
            requested_indices = {int(value) for value in request.POST.getlist("rows")}
        except ValueError:
            requested_indices = set()
        selected_indices = sorted(requested_indices & allowed_indices)

        if requested_indices - allowed_indices:
            messages.error(
                request,
                "Die Auswahl enthält ungültige oder nicht geprüfte Zeilen, es wurde nichts übernommen.",
            )
            return redirect("utils:data_import")

        if not selected_indices:
            messages.error(request, "Keine gültige Zeile ausgewählt.")
            return redirect("utils:data_import")

        selected_type_keys = stored["selected_type_keys"]
        semantic_fields = DataImportMappingService.build_semantic_fields(
            selected_type_keys
        )
        try:
            count = DataImportMappingService.apply_rows(
                selected_type_keys=selected_type_keys,
                semantic_fields=semantic_fields,
                mapping=stored["mapping"],
                raw_rows=stored["rows"],
                row_indices=selected_indices,
                update_existing=stored["update_existing"],
            )
        except RuntimeError as error:
            messages.error(
                request,
                f"Übernahme aus {stored['filename']} abgebrochen, es wurde nichts gespeichert: {error}",
            )
            return redirect("utils:data_import")

        self.delete(token)
        type_names = ", ".join(IMPORT_TYPES[key].name for key in selected_type_keys)
        messages.success(
            request,
            f"{type_names} aus {stored['filename']} übernommen: {count} Zeilen.",
        )
        return redirect("utils:data_import")


class DataImportTemplateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = Permission.Coop.MANAGE

    def get(self, request, import_type: str, *args, **kwargs):
        if import_type not in IMPORT_TYPES:
            raise Http404()
        import_type = IMPORT_TYPES[import_type]
        response = HttpResponse(
            DataImportService.build_template(import_type),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="Vorlage {import_type.name}.xlsx"'
        )
        return response


class DataImportActivationView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = Permission.Coop.MANAGE

    def post(self, request, *args, **kwargs):
        sent, errors = ActivationMailService.send(actor=request.user)
        if sent:
            messages.success(request, f"{sent} Aktivierungsmails verschickt.")
        for error in errors:
            messages.error(request, f"Aktivierungsmail nicht verschickt: {error}")
        return redirect("utils:data_import")
