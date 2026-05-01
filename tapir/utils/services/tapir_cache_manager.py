class TapirCacheManager:
    @classmethod
    def register_key_in_category(cls, cache: dict, key: str, category: str):
        if cache is None:
            return

        if "categories" not in cache:
            cache["categories"] = {}

        if category not in cache["categories"]:
            cache["categories"][category] = set()

        cache["categories"][category].add(key)

    @classmethod
    def clear_category(cls, cache: dict, category: str):
        if cache is None:
            return
        if "categories" not in cache:
            return
        if category not in cache["categories"]:
            return
        for key in cache["categories"][category]:
            if key in cache:
                del cache[key]
