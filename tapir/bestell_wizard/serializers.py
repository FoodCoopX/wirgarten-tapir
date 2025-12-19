from rest_framework import serializers

from tapir.deliveries.serializers import (
    PublicGrowingPeriodSerializer,
)
from tapir.pickup_locations.serializers import PublicPickupLocationSerializer
from tapir.subscriptions.serializers import PublicProductTypeSerializer


class PersonalDataSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    phone_number = serializers.CharField()
    street = serializers.CharField()
    street_2 = serializers.CharField(allow_blank=True)
    postcode = serializers.CharField()
    city = serializers.CharField()
    country = serializers.CharField()
    birthdate = serializers.DateField()
    account_owner = serializers.CharField(allow_blank=True)
    iban = serializers.CharField(allow_blank=True)


class BestellWizardConfirmOrderRequestSerializer(serializers.Serializer):
    # map of productId -> quantity ordered
    shopping_cart_order = serializers.DictField(child=serializers.IntegerField())
    shopping_cart_waiting_list = serializers.DictField(child=serializers.IntegerField())
    personal_data = PersonalDataSerializer()
    sepa_allowed = serializers.BooleanField()
    contract_accepted = serializers.BooleanField()
    statute_accepted = serializers.BooleanField()
    number_of_coop_shares = serializers.IntegerField()
    pickup_location_ids = serializers.ListField(child=serializers.CharField())
    student_status_enabled = serializers.BooleanField()
    payment_rhythm = serializers.CharField()
    become_member_now = serializers.BooleanField(allow_null=True)
    privacy_policy_read = serializers.BooleanField()
    cancellation_policy_read = serializers.BooleanField()
    growing_period_id = serializers.CharField()
    solidarity_contribution = serializers.FloatField()


class BestellWizardCapacityCheckRequestSerializer(serializers.Serializer):
    # map of productId -> quantity ordered
    shopping_cart = serializers.DictField(child=serializers.IntegerField())
    growing_period_id = serializers.CharField()


class BestellWizardCapacityCheckResponseSerializer(serializers.Serializer):
    ids_of_products_over_capacity = serializers.ListField(child=serializers.CharField())
    ids_of_product_types_over_capacity = serializers.ListField(
        child=serializers.CharField()
    )


class BestellWizardStringsSerializer(serializers.Serializer):
    step1a_title = serializers.CharField()
    step1a_text = serializers.CharField()
    step1b_title = serializers.CharField()
    step1b_text = serializers.CharField()
    step2_title = serializers.CharField()
    step2_text = serializers.CharField()
    step3_title = serializers.CharField()
    step3_text = serializers.CharField()
    step3b_title = serializers.CharField()
    step3b_text = serializers.CharField()
    step4b_waiting_list_modal_title = serializers.CharField()
    step4b_waiting_list_modal_text = serializers.CharField()
    step4d_title = serializers.CharField()
    step4d_text = serializers.CharField()
    step5a_title = serializers.CharField()
    step5a_text = serializers.CharField()
    step5b_title = serializers.CharField()
    step5c_title = serializers.CharField()
    step5c_text = serializers.CharField()
    step6a_title = serializers.CharField()
    step6a_text = serializers.CharField()
    step6b_title = serializers.CharField()
    step6b_text = serializers.CharField()
    step6c_checkbox_statute = serializers.CharField()
    step6c_text_statute = serializers.CharField()
    step6c_checkbox_commitment = serializers.CharField()
    step6c_title = serializers.CharField()
    step6c_text = serializers.CharField()
    step8_title = serializers.CharField()
    step9_title = serializers.CharField()
    step9_payment_rhythm_modal_text = serializers.CharField()
    step10_title = serializers.CharField()
    step11_title = serializers.CharField()
    step12_title = serializers.CharField()
    step13_title = serializers.CharField()
    step13_text = serializers.CharField()
    step14_title = serializers.CharField()
    step14_text = serializers.CharField()
    step14b_title = serializers.CharField()
    step14b_text = serializers.CharField()
    privacy_policy_url = serializers.URLField()


class BestellWizardImagesSerializer(serializers.Serializer):
    step1_background_image = serializers.URLField()
    step2_background_image = serializers.URLField()
    step3_background_image = serializers.URLField()
    step4d_background_image = serializers.URLField()
    step5_background_image = serializers.URLField()
    step6_background_image = serializers.URLField()
    step8_background_image = serializers.URLField()
    step9_background_image = serializers.URLField()
    step10_background_image = serializers.URLField()
    step11_background_image = serializers.URLField()
    step12_background_image = serializers.URLField()
    step13_background_image = serializers.URLField()
    step14_background_image = serializers.URLField()


class BestellWizardBaseDataResponseSerializer(serializers.Serializer):
    price_of_a_share = serializers.FloatField()
    theme = serializers.CharField()
    allow_investing_membership = serializers.BooleanField()
    product_types = PublicProductTypeSerializer(many=True)
    pickup_locations = PublicPickupLocationSerializer(many=True)
    force_waiting_list = serializers.BooleanField()
    intro_enabled = serializers.BooleanField()
    student_status_allowed = serializers.BooleanField()
    show_coop_content = serializers.BooleanField()
    intro_step_text = serializers.CharField()
    label_checkbox_sepa_mandat = serializers.CharField()
    label_checkbox_contract_policy = serializers.CharField()
    revocation_rights_explanation = serializers.CharField()
    trial_period_length_in_weeks = serializers.IntegerField()
    payment_rhythm_choices = serializers.DictField(child=serializers.CharField())
    default_payment_rhythm = serializers.CharField()
    product_type_ids_that_are_already_at_capacity = serializers.ListField(
        child=serializers.CharField()
    )
    product_ids_that_are_already_at_capacity = serializers.ListField(
        child=serializers.CharField()
    )
    coop_statute_link = serializers.CharField()
    organization_name = serializers.CharField()
    logo_url = serializers.URLField()
    contact_mail_address = serializers.EmailField()
    distribution_channels = serializers.ListField(child=serializers.CharField())
    solidarity_contribution_choices = serializers.ListField(
        child=serializers.CharField()
    )
    solidarity_contribution_minimum = serializers.FloatField(allow_null=True)
    solidarity_contribution_default = serializers.FloatField()
    feedback_step_enabled = serializers.BooleanField()
    growing_period_choices = PublicGrowingPeriodSerializer(many=True)
    strings = BestellWizardStringsSerializer()
    images = BestellWizardImagesSerializer()
    debug = serializers.BooleanField()


class BestellWizardDeliveryDatesForOrderRequestSerializer(serializers.Serializer):
    shopping_cart = serializers.DictField(child=serializers.IntegerField())
    waiting_list_entry_id = serializers.CharField(required=False)
    growing_period_id = serializers.CharField(required=False)


class BestellWizardDeliveryDatesForOrderResponseSerializer(serializers.Serializer):
    delivery_date_by_pickup_location_id_and_product_type_id = serializers.DictField(
        child=serializers.DictField(child=serializers.DateField())
    )


class PublicProductPricesResponseSerializer(serializers.Serializer):
    prices_by_product_id = serializers.DictField(child=serializers.FloatField())
