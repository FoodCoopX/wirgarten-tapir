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
from tapir.utils.services.data_import_service import (
    IMPORT_TYPES,
    ActivationMailService,
    DataImportService,
)
from tapir.utils.services.tabular_file_reader import TabularData, TabularFileReader
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


class DataImportView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """Takes over existing data from Excel or CSV: upload, dry run with a preview per row,
    apply, then send the activation mails."""

    form_class = DataImportForm
    permission_required = Permission.Coop.MANAGE
    template_name = "utils/data_import.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["import_types"] = [
            (import_type.key, import_type.name) for import_type in IMPORT_TYPES.values()
        ]
        return kwargs

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["page_title"] = "Datenübernahme"
        context_data["import_types"] = IMPORT_TYPES.values()
        context_data["members_without_login"] = (
            ActivationMailService.get_members_without_login().count()
        )
        return context_data

    def form_valid(self, form):
        import_type = IMPORT_TYPES[form.cleaned_data["import_type"]]
        upload = form.cleaned_data["file"]
        try:
            data = TabularFileReader.read(upload, upload.name)
        except TapirDataImportException as error:
            form.add_error("file", str(error))
            return self.form_invalid(form)

        update_existing = form.cleaned_data["update_existing"]
        result = DataImportService.run(
            import_type=import_type,
            data=data,
            update_existing=update_existing,
            dry_run=True,
        )
        token = uuid.uuid4().hex
        cache.set(
            DATA_IMPORT_CACHE_PREFIX + token,
            {
                "import_type": import_type.key,
                "update_existing": update_existing,
                "headers": data.headers,
                "rows": data.rows,
                "filename": upload.name,
            },
            DATA_IMPORT_CACHE_SECONDS,
        )
        return self.render_to_response(
            self.get_context_data(
                form=form, result=result, token=token, filename=upload.name
            )
        )


class DataImportApplyView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = Permission.Coop.MANAGE

    def post(self, request, *args, **kwargs):
        key = DATA_IMPORT_CACHE_PREFIX + request.POST.get("token", "")
        stored = cache.get(key)
        if stored is None:
            messages.error(
                request,
                "Die hochgeladene Datei ist abgelaufen, bitte noch einmal hochladen.",
            )
            return redirect("utils:data_import")

        import_type = IMPORT_TYPES[stored["import_type"]]
        result = DataImportService.run(
            import_type=import_type,
            data=TabularData(headers=stored["headers"], rows=stored["rows"]),
            update_existing=stored["update_existing"],
            dry_run=False,
        )
        cache.delete(key)
        if result.can_be_applied:
            counts = result.counts
            messages.success(
                request,
                f"{import_type.name} aus {stored['filename']} übernommen: "
                f"{counts['created']} angelegt, {counts['updated']} aktualisiert, "
                f"{counts['skipped']} übersprungen.",
            )
        else:
            messages.error(
                request,
                f"{import_type.name} aus {stored['filename']} nicht übernommen: "
                f"{result.count('error')} Zeilen mit Fehlern, es wurde nichts gespeichert.",
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
