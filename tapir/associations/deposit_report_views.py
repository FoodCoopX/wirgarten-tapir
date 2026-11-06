import csv

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse
from django.views.generic import TemplateView

from tapir.associations.deposit_forms import DepositDepartureReportForm
from tapir.associations.services.association_deposit_departure_report_provider import (
    AssociationDepositDepartureReportProvider,
)
from tapir.associations.services.association_deposit_export_column_provider import (
    AssociationDepositExportColumnProvider,
)
from tapir.associations.services.association_deposit_policy import (
    AssociationDepositPolicy,
)
from tapir.coop.services.member_number_service import MemberNumberService
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.utils import format_date, get_today, legal_status_is_association


class DepositDepartureReportView(PermissionRequiredMixin, TemplateView):
    permission_required = Permission.Coop.MANAGE
    template_name = "associations/deposit_departure_report.html"
    paginate_by = 25

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cache = {}

    def get(self, request, *args, **kwargs):
        if not legal_status_is_association(cache=self.cache):
            raise Http404
        today = get_today(self.cache)
        data = request.GET.copy()
        data.setdefault("year", today.year - 1)
        form = DepositDepartureReportForm(data, reference_date=today)
        report = None
        if form.is_valid():
            report = AssociationDepositDepartureReportProvider.get_report(
                form.cleaned_data["year"], self.cache
            )
            if request.GET.get("format") == "csv":
                return self._csv(report)
        return self.render_to_response(
            {
                "form": form,
                "report": report,
                "page": (
                    Paginator(report["rows"], self.paginate_by).get_page(
                        request.GET.get("page")
                    )
                    if report
                    else None
                ),
                "cache": self.cache,
                "deposit_name": AssociationDepositPolicy.get_settings(self.cache)[
                    "name"
                ],
            }
        )

    def _csv(self, report):
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="Einlagen_Austritte_{report["year"]}_Stand_{report["as_of"].isoformat()}.csv"'
        )
        writer = csv.writer(response, delimiter=";")
        columns = AssociationDepositExportColumnProvider.get_columns(self.cache)
        writer.writerow(
            [
                "Mitgliedsnummer",
                "Name",
                "Email",
                "Letzter wirksamer Austritt",
                "Buchungsstand vom",
                "Kontoinhaber",
                "IBAN",
            ]
            + [column.display_name for column in columns]
        )
        for row in report["rows"]:
            member = row["member"]
            writer.writerow(
                [
                    MemberNumberService.format_member_number(
                        member.member_no, cache=self.cache
                    ),
                    member.get_display_name(),
                    member.email,
                    format_date(row["departure_date"]),
                    format_date(report["as_of"]),
                    member.account_owner,
                    member.iban,
                ]
                + list(
                    AssociationDepositExportColumnProvider.get_csv_row(
                        member, self.cache
                    ).values()
                )
            )
        return response
