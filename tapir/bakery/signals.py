"""
Receivers that keep bread deliveries in step with core's models.

Registered from BakeryConfig.ready() rather than declared in models.py, so the
models module does not have to import the services it triggers.

These only cover writes that go through Model.save(). Subscriptions written
with bulk_create do not reach a receiver, and those call sites have to invoke
BreadDeliveryService themselves.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from tapir.bakery.services.breaddelivery_service import BreadDeliveryService


@receiver(post_save, sender="wirgarten.Subscription")
def on_subscription_saved(sender, instance, created, **kwargs):
    if not instance.product.type.is_bread:
        return
    if not instance.start_date or not instance.end_date:
        return
    BreadDeliveryService.ensure_bread_deliveries_for_member(instance.member)


@receiver(post_save, sender="wirgarten.MemberPickupLocation")
def on_member_pickup_location_saved(sender, instance, created, **kwargs):
    # A bread chosen at the previous station may not be baked at the new one.
    BreadDeliveryService.clear_breads_unavailable_at_pickup_location(instance.member)


@receiver(post_save, sender="wirgarten.GrowingPeriod")
def on_growing_period_saved(sender, instance, **kwargs):
    # weeks_without_delivery is applied when the rows are written, so editing
    # it on an existing period has to rewrite the rows already created.
    BreadDeliveryService.resync_bread_deliveries_for_growing_period(instance)
