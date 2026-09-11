import datetime

import weasyprint
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse
from django.template.loader import render_to_string

from tapir.bakery.services.baking_list_service import BakingListService
from tapir.bakery.services.distribution_list_service import DistributionListService
from tapir.bakery.services.pickup_list_service import PickupListService
from tapir.pickup_locations.models import PickupLocation
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.constants import Permission

DAY_LABELS = {
    0: "Montag",
    1: "Dienstag",
    2: "Mittwoch",
    3: "Donnerstag",
    4: "Freitag",
    5: "Samstag",
    6: "Sonntag",
}


class InvalidWeek(Exception):
    """The requested ISO week does not exist in that year."""


def _build_base_context(year: int, week: int, day: int, report_title: str) -> dict:
    try:
        # ISO years have 52 or 53 weeks, and both week and day come straight
        # from the URL.
        date = datetime.date.fromisocalendar(year, week, day + 1)
    except ValueError:
        raise InvalidWeek

    return {
        "year": year,
        "week": week,
        "day": day,
        "day_label": DAY_LABELS.get(day, f"Tag {day}"),
        "date_string": date.strftime("%d.%m.%Y"),
        "today": datetime.date.today().strftime("%d.%m.%Y"),
        "report_title": report_title,
    }


def _render_pdf_response(
    template_name: str, context: dict, filename: str
) -> HttpResponse:
    html_string = render_to_string(template_name, context)
    pdf = weasyprint.HTML(string=html_string).write_pdf()
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


@login_required
@permission_required(Permission.Coop.MANAGE, raise_exception=True)
def baking_list_pdf(request, year: int, week: int, day: int):
    try:
        context = _build_base_context(year, week, day, "Backliste")
    except InvalidWeek:
        return HttpResponse("Ungültige Kalenderwoche.", status=400)
    context.update(BakingListService.get_baking_list(year, week, day))

    filename = f"Backliste_KW{week}_{year}_{context['day_label']}.pdf"
    return _render_pdf_response("bakery/pdfs/baking_list.html", context, filename)


@login_required
@permission_required(Permission.Coop.MANAGE, raise_exception=True)
def distribution_list_pdf(request, year: int, week: int, day: int):
    try:
        context = _build_base_context(year, week, day, "Verteilliste")
    except InvalidWeek:
        return HttpResponse("Ungültige Kalenderwoche.", status=400)
    context.update(DistributionListService.get_distribution_list(year, week, day))

    filename = f"Verteilliste_KW{week}_{year}_{context['day_label']}.pdf"
    return _render_pdf_response("bakery/pdfs/distribution_list.html", context, filename)


@login_required
@permission_required(Permission.Coop.MANAGE, raise_exception=True)
def pickup_list_pdf(request, year: int, week: int, day: int, pickup_location_id: str):
    try:
        context = _build_base_context(year, week, day, "Abholliste")
    except InvalidWeek:
        return HttpResponse("Ungültige Kalenderwoche.", status=400)

    try:
        pickup_location = PickupLocation.objects.get(id=pickup_location_id)
    except PickupLocation.DoesNotExist:
        return HttpResponse("Abholstation nicht gefunden.", status=404)

    context["pickup_location_name"] = pickup_location.name
    context.update(PickupListService.get_pickup_list(year, week, pickup_location_id))

    filename = (
        f"Abholliste_KW{week}_{year}_{context['day_label']}_{pickup_location.name}.pdf"
    )
    return _render_pdf_response("bakery/pdfs/pickup_list.html", context, filename)


@login_required
@permission_required(Permission.Coop.MANAGE, raise_exception=True)
def pickup_lists_all_pdf(request, year: int, week: int, day: int):
    try:
        context = _build_base_context(
            year, week, day, "Abhollisten – Alle Abholstationen"
        )
    except InvalidWeek:
        return HttpResponse("Ungültige Kalenderwoche.", status=400)

    # Built once outside the loop: the location weekdays and the grouping of
    # the week's deliveries by station are shared across every station here.
    cache = {}
    delivery_days = TapirCache.get_delivery_day_by_pickup_location_id(cache=cache)
    pickup_locations = sorted(
        [pl for pl in PickupLocation.objects.all() if delivery_days.get(pl.id) == day],
        key=lambda pl: pl.name,
    )
    all_pickup_lists = []
    for pl in pickup_locations:
        data = PickupListService.get_pickup_list(year, week, str(pl.id), cache=cache)
        if data["entries"]:
            all_pickup_lists.append(
                {
                    "pickup_location_name": pl.name,
                    "bread_names": data["bread_names"],
                    "entries": data["entries"],
                    "bread_totals": data["bread_totals"],
                    "grand_total": data["grand_total"],
                }
            )

    if not all_pickup_lists:
        return HttpResponse("Keine Abhollisten für diesen Tag.", status=404)

    context["all_pickup_lists"] = all_pickup_lists

    filename = f"Abhollisten_alle_KW{week}_{year}_{context['day_label']}.pdf"
    return _render_pdf_response("bakery/pdfs/pickup_lists_all.html", context, filename)
