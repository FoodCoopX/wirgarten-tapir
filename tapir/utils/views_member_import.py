from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render
from django.views import View
from django.views.generic import FormView

from tapir.utils.exceptions import TapirDataImportException
from tapir.utils.forms import MemberImportForm, MemberImportApplyForm
from tapir.utils.services.member_import_service import MemberImportService
from tapir.wirgarten.constants import Permission


class MemberImportView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    permission_required = Permission.Coop.MANAGE
    form_class = MemberImportForm
    template_name = "utils/member_import.html"
    extra_context = {"page_title": "Mitglieder importieren"}

    def form_valid(self, form):
        try:
            token, result = MemberImportService.preview(
                file=form.cleaned_data["file"], user_id=self.request.user.pk
            )
        except TapirDataImportException as error:
            form.add_error("file", str(error))
            return self.form_invalid(form)
        return self.render_to_response(
            self.get_context_data(form=form, result=result, token=token)
        )


class MemberImportApplyView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = Permission.Coop.MANAGE

    def post(self, request):
        form = MemberImportApplyForm(request.POST)
        result = None
        error = None
        if form.is_valid():
            try:
                result = MemberImportService.apply(
                    user_id=request.user.pk, token=form.cleaned_data["token"]
                )
            except TapirDataImportException as exception:
                error = str(exception)
        else:
            error = "Bitte zuerst eine Datei hochladen und prüfen."
        return render(
            request,
            "utils/member_import.html",
            {
                "page_title": "Mitglieder importieren",
                "form": MemberImportForm(),
                "result": result,
                "error": error,
            },
        )


class MemberImportTemplateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = Permission.Coop.MANAGE

    def get(self, request):
        response = HttpResponse(
            MemberImportService.build_template(), content_type="text/csv; charset=utf-8"
        )
        response["Content-Disposition"] = (
            'attachment; filename="Mitglieder-Vorlage.csv"'
        )
        return response
