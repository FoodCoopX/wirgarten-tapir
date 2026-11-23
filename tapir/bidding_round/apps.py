from django.apps import AppConfig


class BiddingRoundConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tapir.bidding_round"

    def ready(self):
        from tapir.bidding_round.services.bidding_round_subscription_price_service import (
            BiddingRoundSubscriptionPriceService,
        )
        from tapir.subscriptions.services.subscription_price_provider import (
            SubscriptionPriceProvider,
        )

        SubscriptionPriceProvider.register(
            BiddingRoundSubscriptionPriceService.get_price_for_subscription
        )
        SubscriptionPriceProvider.register_annotation(
            BiddingRoundSubscriptionPriceService.annotate_price_per_share,
            BiddingRoundSubscriptionPriceService.price_per_share_when,
        )
