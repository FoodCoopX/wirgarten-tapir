from django.db import models

from tapir.log.models import LogEntry
from tapir.wirgarten.models import ProductType, GrowingPeriod
from tapir.wirgarten.utils import format_subscription_list_html


class NoticePeriod(models.Model):
    product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE)
    growing_period = models.ForeignKey(GrowingPeriod, on_delete=models.CASCADE)
    duration = (
        models.IntegerField()
    )  # can be weeks or months depending on ParameterKeys.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD_UNIT


class SubscriptionsRevokedLogEntry(LogEntry):
    template_name = "subscriptions/log/subscriptions_revoked_log_entry.html"

    subscriptions = models.CharField(null=False, blank=False, max_length=10000)

    def populate_subscriptions(self, subscriptions: list, actor, user):
        self.populate(actor, user)
        self.subscriptions = format_subscription_list_html(subscriptions)
        return self
