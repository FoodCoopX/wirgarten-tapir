import mimetypes

from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET
from django_filters import (
    FilterSet,
    ChoiceFilter,
    CharFilter,
)
from django_filters.views import FilterView

from tapir.wirgarten.constants import (
    Permission,
)
from tapir.wirgarten.models import (
    WaitingListEntry,
)
from tapir.wirgarten.service.file_export import begin_csv_string
from tapir.wirgarten.utils import (
    get_now,
)


class WaitingListFilter(FilterSet):
    type = ChoiceFilter(
        label=_("Warteliste"),
        lookup_expr="exact",
        choices=WaitingListEntry.WaitingListType.choices,
        empty_label=None,
        initial=0,
    )
    first_name = CharFilter(label=_("Vorname"), lookup_expr="icontains")
    last_name = CharFilter(label=_("Nachname"), lookup_expr="icontains")
    email = CharFilter(label=_("Email"), lookup_expr="icontains")

    def __init__(self, data=None, *args, **kwargs):
        if data is None:
            data = {"type": WaitingListEntry.WaitingListType.HARVEST_SHARES}
        else:
            data = data.copy()

            if not data["type"]:
                data["type"] = WaitingListEntry.WaitingListType.HARVEST_SHARES

        super().__init__(data, *args, **kwargs)

    class Meta:
        model = WaitingListEntry
        fields = ["type", "first_name", "last_name", "email"]


class WaitingListView(PermissionRequiredMixin, FilterView):
    filterset_class = WaitingListFilter
    ordering = ["created_at"]
    permission_required = Permission.Accounts.MANAGE
    template_name = "wirgarten/waitlist/waitlist_filter.html"
    paginated_by = 20


@require_GET
@csrf_protect
@permission_required(Permission.Coop.MANAGE)
def export_waitinglist(request, **kwargs):
    waitlist_type = request.environ["QUERY_STRING"].replace("type=", "")
    if not waitlist_type:
        return  # unknown waitlist type, can never happen from UI

    waitlist_type_label = list(
        filter(
            lambda x: x[0] == waitlist_type, WaitingListEntry.WaitingListType.choices
        )
    )[0][1]

    KEY_FIRST_NAME = "Vorname"
    KEY_LAST_NAME = "Nachname"
    KEY_EMAIL = "Email"
    KEY_SINCE = "Wartet seit"

    output, writer = begin_csv_string(
        [KEY_FIRST_NAME, KEY_LAST_NAME, KEY_EMAIL, KEY_SINCE]
    )
    for entry in WaitingListEntry.objects.filter(type=waitlist_type):
        writer.writerow(
            {
                KEY_FIRST_NAME: entry.first_name,
                KEY_LAST_NAME: entry.last_name,
                KEY_EMAIL: entry.email,
                KEY_SINCE: entry.created_at,
            }
        )

    filename = (
        f"Warteliste-{waitlist_type_label}_{get_now().strftime('%Y%m%d_%H%M%S')}.csv"
    )
    mime_type, _ = mimetypes.guess_type(filename)
    response = HttpResponse("".join(output.csv_string), content_type=mime_type)
    response["Content-Disposition"] = "attachment; filename=%s" % filename
    return response
