from rest_framework import serializers

from tapir.deliveries.serializers import ProductTypeSerializer
from tapir.wirgarten.constants import DeliveryCycle


class ExtendedProductTypeSerializer(serializers.Serializer):
    name = serializers.CharField()
    description_bestellwizard_short = serializers.CharField(
        required=False, allow_blank=True
    )
    description_bestellwizard_long = serializers.CharField(
        required=False, allow_blank=True
    )
    order_in_bestellwizard = serializers.IntegerField()
    icon_link = serializers.URLField(required=False, allow_blank=True)
    contract_link = serializers.URLField(required=False, allow_blank=True)
    capacity = serializers.FloatField()
    delivery_cycle = serializers.ChoiceField(choices=DeliveryCycle)
    notice_period = serializers.IntegerField(required=False)
    tax_rate = serializers.FloatField()
    tax_rate_change_date = serializers.DateField()
    single_subscription_only = serializers.BooleanField()
    is_affected_by_jokers = serializers.BooleanField()
    must_be_subscribed_to = serializers.BooleanField()
    is_association_membership = serializers.BooleanField()
    force_waiting_list = serializers.BooleanField()


class ExtendedProductTypeAndConfigSerializer(serializers.Serializer):
    show_notice_period = serializers.BooleanField()
    show_jokers = serializers.BooleanField()
    show_association_membership = serializers.BooleanField()
    delivery_cycle_options = serializers.DictField()
    extended_product_type = ExtendedProductTypeSerializer()


class SaveExtendedProductTypeSerializer(serializers.Serializer):
    product_type_id = serializers.CharField(required=False)
    growing_period_id = serializers.CharField()
    extended_product_type = ExtendedProductTypeSerializer()


class ProductTypesAndConfigSerializer(serializers.Serializer):
    product_types_without_capacity = ProductTypeSerializer(many=True)
    show_notice_period = serializers.BooleanField()
    show_jokers = serializers.BooleanField()
    show_association_membership = serializers.BooleanField()
    delivery_cycle_options = serializers.DictField()
