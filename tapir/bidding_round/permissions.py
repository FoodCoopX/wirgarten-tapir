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


class BiddingRoundCacheMixin:
    """Keeps the per-request cache on the view instance.

    Defining it in ``__init__`` lets ``initial`` reuse the same cache as the
    handlers instead of building a second one.
    """

    def __init__(self, *args, **kwargs):
        self.cache = {}
        super().__init__(*args, **kwargs)


class BiddingRoundFeatureFlagMixin(BiddingRoundCacheMixin):
    """Applies the feature-flag gate to a DRF view via ``initial``.

    This keeps the view's own ``permission_classes`` (and therefore the global
    ``IsAuthenticated`` default for admin views) untouched. ``require_public_url`` marks
    the public (member-facing) endpoints. The per-request cache lives on ``self.cache``
    so the handlers reuse it instead of building their own.
    """

    require_public_url = False

    def initial(self, request, *args, **kwargs):
        if not BiddingRoundViewService.is_feature_flag_enabled(self.cache):
            raise Http404
        if self.require_public_url and not (
            BiddingRoundViewService.is_public_url_enabled(self.cache)
        ):
            raise Http404
        return super().initial(request, *args, **kwargs)
