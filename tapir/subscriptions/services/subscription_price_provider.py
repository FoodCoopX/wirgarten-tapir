class SubscriptionPriceProvider:
    """Registry for feature modules that price a subscription themselves.

    Features register a callable ``(subscription, cache) -> Decimal | None`` in their
    app config. The calculator asks the registered providers before it falls back to
    the standard product price, so ``subscriptions`` does not import feature apps.
    """

    _providers = []

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
