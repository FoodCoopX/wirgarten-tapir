def pytest_collection_modifyitems(items):
    # Start slow tests first so that they don't become the long tail of parallel runs.
    items.sort(key=lambda item: item.get_closest_marker("slow") is None)
