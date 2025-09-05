from rest_framework import serializers

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
    account_owner = serializers.CharField()
    iban = serializers.CharField()


class BestellWizardConfirmOrderRequestSerializer(serializers.Serializer):
    # map of productId -> quantity ordered
    shopping_cart = serializers.DictField(child=serializers.IntegerField())
    personal_data = PersonalDataSerializer()
    sepa_allowed = serializers.BooleanField()
    contract_accepted = serializers.BooleanField()
    statute_accepted = serializers.BooleanField()
    nb_shares = serializers.IntegerField()
    pickup_location_id = serializers.CharField(required=False)
    student_status_enabled = serializers.BooleanField()
    payment_rhythm = serializers.CharField()
    waiting_list_shopping_cart = serializers.DictField(child=serializers.IntegerField())
    become_member_now = serializers.BooleanField()


class BestellWizardCapacityCheckRequestSerializer(serializers.Serializer):
    # map of productId -> quantity ordered
    shopping_cart = serializers.DictField(child=serializers.IntegerField())


class BestellWizardCapacityCheckResponseSerializer(serializers.Serializer):
    ids_of_products_over_capacity = serializers.ListField(child=serializers.CharField())
    ids_of_product_types_over_capacity = serializers.ListField(
        child=serializers.CharField()
    )


class BestellWizardBaseDataResponseSerializer(serializers.Serializer):
    price_of_a_share = serializers.FloatField()
    theme = serializers.CharField()
    allow_investing_membership = serializers.BooleanField()
    product_types = PublicProductTypeSerializer(many=True)
    force_waiting_list = serializers.BooleanField()
    intro_enabled = serializers.BooleanField()
    student_status_allowed = serializers.BooleanField()
    show_coop_content = serializers.BooleanField()
    intro_step_text = serializers.CharField()
    coop_step_text = serializers.CharField()
    label_checkbox_sepa_mandat = serializers.CharField()
    label_checkbox_contract_policy = serializers.CharField()
    revocation_rights_explanation = serializers.CharField()
    trial_period_length_in_weeks = serializers.IntegerField()
    payment_rhythm_choices = serializers.DictField(child=serializers.CharField())
    default_payment_rhythm = serializers.CharField()


class BestellWizardDeliveryDatesForOrderRequestSerializer(serializers.Serializer):
    shopping_cart = serializers.DictField(child=serializers.IntegerField())
    pickup_location_id = serializers.CharField()
    waiting_list_entry_id = serializers.CharField(required=False)


class BestellWizardDeliveryDatesForOrderResponseSerializer(serializers.Serializer):
    product_type_id_to_next_delivery_date_map = serializers.DictField(
        child=serializers.DateField()
    )
