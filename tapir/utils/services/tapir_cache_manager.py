class TapirCacheManager:
    @classmethod
    def register_key_in_category(cls, cache: dict, key: str, category: str):
        if cache is None:
            return

        if "categories" not in cache.keys():
            cache["categories"] = {}

        if category not in cache["categories"].keys():
            cache["categories"][category] = set()

        cache["categories"][category].add(key)

    @classmethod
    def clear_category(cls, cache: dict, category: str):
        if cache is None:
            return
        if "categories" not in cache.keys():
            return
        if category not in cache["categories"].keys():
            return
        for key in cache["categories"][category]:
            if key in cache.keys():
                del cache[key]
