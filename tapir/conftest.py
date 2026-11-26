import os

from django.conf import settings


def pytest_configure(config):
    # Parallel workers share one redis instance: give each its own database,
    # so that cache.clear() and the mail module's locks don't interfere across workers.
    worker = os.environ.get("PYTEST_XDIST_WORKER")
    if worker is None:
        return

    database_index = int(worker.removeprefix("gw")) + 1
    settings.CACHES["default"][
        "LOCATION"
    ] = f"{settings.CACHES['default']['LOCATION'].rstrip('/')}/{database_index}"


def pytest_collection_modifyitems(items):
    # Start slow tests first so that they don't become the long tail of parallel runs.
    items.sort(key=lambda item: item.get_closest_marker("slow") is None)
