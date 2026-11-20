from django.http import Http404
from rest_framework.permissions import BasePermission

from tapir.bidding_round.services.bidding_round_view_service import (
    BiddingRoundViewService,
)
from tapir.wirgarten.constants import Permission


class BiddingRoundManagePermission(BasePermission):
    message = "Für die Beitragsrunden-Verwaltung fehlt die Berechtigung."

    def has_permission(self, request, view) -> bool:
        return request.user.is_authenticated and request.user.has_perm(
            Permission.Coop.MANAGE
        )


class BiddingRoundFeatureFlagMixin:
    """Applies the feature-flag gate to a DRF view via ``initial``.

    This keeps the view's own ``permission_classes`` (and therefore the global
    ``IsAuthenticated`` default for admin views) untouched. ``require_public_url`` marks
    the public (member-facing) endpoints, which require authentication while the public
    URL flag is off.
    """

    require_public_url = False

    def initial(self, request, *args, **kwargs):
        cache = {}
        if not BiddingRoundViewService.is_feature_flag_enabled(cache):
            raise Http404
        if (
            self.require_public_url
            and not BiddingRoundViewService.public_access_allowed(request.user, cache)
        ):
            raise Http404
        return super().initial(request, *args, **kwargs)
