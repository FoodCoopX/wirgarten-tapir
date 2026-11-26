import os

import pytest
import redis
from django.conf import settings


def pytest_configure(config):
    # Parallel workers share one redis instance: give each its own database,
    # so that cache.clear() and the mail module's locks don't interfere across workers.
    worker = os.environ.get("PYTEST_XDIST_WORKER")
    if worker is None:
        return

    redis_url = settings.CACHES["default"]["LOCATION"].rstrip("/")
    database_index = int(worker.removeprefix("gw")) + 1
    database_count = int(
        redis.Redis.from_url(redis_url).config_get("databases")["databases"]
    )
    if database_index >= database_count:
        raise pytest.UsageError(
            f"Worker {worker} needs redis database {database_index}, but redis only has "
            f"{database_count} databases (0 to {database_count - 1}). "
            f"Run pytest with at most {database_count - 1} workers (-n {database_count - 1})."
        )

    settings.CACHES["default"]["LOCATION"] = f"{redis_url}/{database_index}"


def pytest_collection_modifyitems(items):
    # Start slow tests first so that they don't become the long tail of parallel runs.
    items.sort(key=lambda item: item.get_closest_marker("slow") is None)
