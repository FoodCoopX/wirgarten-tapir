from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404, JsonResponse
from django.views import View

from tapir.subscriptions.services.admin_contract_prototype import AdminContractPrototype
from tapir.wirgarten.constants import Permission


class AdminContractPrototypeDataView(PermissionRequiredMixin, View):
    permission_required = Permission.Accounts.MANAGE

    def get(self, request):
        if not settings.DEBUG:
            raise Http404
        cache = {}
        try:
            if request.GET.get("check"):
                data = AdminContractPrototype.preview(request.GET, cache=cache)
            elif request.GET.get("member"):
                data = AdminContractPrototype.member(request.GET["member"], cache=cache)
            elif "q" in request.GET:
                query = request.GET["q"].strip()
                data = (
                    AdminContractPrototype.search(query, cache=cache)
                    if len(query) >= 2
                    else []
                )
            else:
                data = AdminContractPrototype.configuration(cache=cache)
        except (ValueError, KeyError, ObjectDoesNotExist):
            return JsonResponse(
                {"error": "Bitte Vertrag, Menge und Startdatum prüfen."}, status=400
            )
        response = JsonResponse(data, safe=False)
        response["Cache-Control"] = "no-store"
        return response
