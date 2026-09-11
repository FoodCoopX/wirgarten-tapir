from decimal import Decimal

from django.db import models

from tapir.accounts.models import TapirUser
from tapir.core.models import TapirModel
from tapir.log.models import LogEntry, UpdateModelLogEntry
from tapir.subscriptions.config import NOTICE_PERIOD_UNIT_OPTIONS
from tapir.wirgarten.models import ProductType, GrowingPeriod, Member, Subscription
from tapir.wirgarten.utils import format_subscription_list_html, format_currency


class NoticePeriod(models.Model):
    product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE)
    growing_period = models.ForeignKey(GrowingPeriod, on_delete=models.CASCADE)
    duration = models.IntegerField()
    unit = models.CharField(choices=NOTICE_PERIOD_UNIT_OPTIONS, max_length=20)


class SubscriptionsRevokedLogEntry(LogEntry):
    template_name = "subscriptions/log/subscriptions_revoked_log_entry.html"

    subscriptions = models.CharField(null=False, blank=False, max_length=10000)

    def populate_subscriptions(self, subscriptions: list, actor, user):
        self.populate(actor, user)
        self.subscriptions = format_subscription_list_html(subscriptions)
        return self


class SubscriptionChangedLogEntry(UpdateModelLogEntry):
    template_name = "subscriptions/log/subscription_changed_log_entry.html"


class SubscriptionPriceChangedLogEntry(UpdateModelLogEntry):
    template_name = "subscriptions/log/subscription_price_changed_log_entry.html"
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True)
    subscription_formatted = models.CharField(max_length=200)
    price_before = models.DecimalField(
        decimal_places=2, max_digits=8, null=True, blank=True
    )
    price_after = models.DecimalField(
        decimal_places=2, max_digits=8, null=True, blank=True
    )

    def populate_price_change(
        self,
        subscription_frozen_before_changes: dict,
        subscription: Subscription,
        price_before: Decimal | None,
        actor: TapirUser,
        user: Member,
    ):
        self.subscription = subscription
        self.subscription_formatted = subscription.long_str()
        self.price_before = price_before
        self.price_after = subscription.price_override
        super().populate(
            old_frozen=subscription_frozen_before_changes,
            new_model=subscription,
            actor=actor,
            user=user,
        )
        return self

    def get_context_data(self):
        context_data = super().get_context_data()
        price_before = (
            "Standard"
            if self.price_before is None
            else f"{format_currency(self.price_before)}€"
        )
        context_data["price_before"] = price_before
        price_after = (
            "Standard"
            if self.price_after is None
            else f"{format_currency(self.price_after)}€"
        )
        context_data["price_after"] = price_after
        return context_data
