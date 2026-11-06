from django.http import Http404
from rest_framework.permissions import BasePermission

from tapir.bidding_round.services.bidding_round_view_service import (
    BiddingRoundViewService,
)


class BiddingRoundFeaturePermission(BasePermission):
    """Feature-flag gate for bidding round API endpoints.

    When the master flag ``BIDDING_ROUND_ENABLED`` is off, every endpoint answers with
    404, exactly like the pages. Views that set ``require_public_url = True``
    additionally require ``BIDDING_ROUND_URL_ENABLED``, so the public endpoints disappear
    together with the public page while the admin API stays reachable.
    """

    def has_permission(self, request, view) -> bool:
        cache = {}
        if not BiddingRoundViewService.is_feature_flag_enabled(cache):
            raise Http404
        if getattr(view, "require_public_url", False) and not (
            BiddingRoundViewService.is_public_url_enabled(cache)
        ):
            raise Http404
        return True


class BiddingRoundFeatureFlagMixin:
    """Applies the feature-flag gate to a DRF view via ``initial``.

    This keeps the view's own ``permission_classes`` (and therefore the global
    ``IsAuthenticated`` default for admin views) untouched. ``require_public_url`` marks
    the public (member-facing) endpoints.
    """

    require_public_url = False

    def initial(self, request, *args, **kwargs):
        cache = {}
        if not BiddingRoundViewService.is_feature_flag_enabled(cache):
            raise Http404
        if self.require_public_url and not (
            BiddingRoundViewService.is_public_url_enabled(cache)
        ):
            raise Http404
        return super().initial(request, *args, **kwargs)
