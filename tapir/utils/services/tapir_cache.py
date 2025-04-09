from typing import Dict

from tapir.utils.shortcuts import get_from_cache_or_compute
from tapir.wirgarten.models import Subscription


class TapirCache:
    @classmethod
    def get_all_subscriptions(cls, cache: Dict):
        return get_from_cache_or_compute(
            cache, "all_subscriptions", lambda: set(Subscription.objects.order_by("id"))
        )
