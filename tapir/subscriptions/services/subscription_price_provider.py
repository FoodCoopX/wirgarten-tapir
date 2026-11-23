class SubscriptionPriceProvider:
    """Registry for feature modules that price a subscription themselves.

    Features register a callable ``(subscription, cache) -> Decimal | None`` in their
    app config. The calculator asks the registered providers before it falls back to
    the standard product price, so ``subscriptions`` does not import feature apps.

    A feature that stores its price outside ``ProductPrice`` registers an annotation
    as well: a callable that adds the queryset annotation it needs and a callable that
    returns the ``When`` making the annotated queryset use it. The calculator applies
    both, so lists show the same price as ``get_monthly_price``.
    """

    _providers = []
    _annotations = []

    @classmethod
    def register(cls, provider) -> None:
        if provider not in cls._providers:
            cls._providers.append(provider)

    @classmethod
    def get_price(cls, subscription, cache):
        for provider in cls._providers:
            price = provider(subscription, cache)
            if price is not None:
                return price
        return None

    @classmethod
    def register_annotation(cls, annotate, price_when) -> None:
        if (annotate, price_when) not in cls._annotations:
            cls._annotations.append((annotate, price_when))

    @classmethod
    def apply_annotations(cls, queryset):
        for annotate, _price_when in cls._annotations:
            queryset = annotate(queryset)
        return queryset

    @classmethod
    def get_price_whens(cls) -> list:
        return [price_when() for _annotate, price_when in cls._annotations]
