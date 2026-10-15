from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from localflavor.generic.validators import IBANValidator

from tapir.core.models import TapirModel


class JasminTenant(TapirModel):
    # Copied from jasmin-core/django-core/apps/shared/tenants/models.py:95
    name = models.CharField(max_length=200)
    schema_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    address = models.CharField(max_length=200, blank=True, null=True)
    zip_code = models.CharField(max_length=10, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    organic_control_number = models.CharField(max_length=100, blank=True, null=True)
    tenant_language = models.CharField(max_length=8, blank=True, default="de")
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    email_for_orders = models.EmailField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    legal_form = models.CharField(max_length=100, blank=True, default="")
    data_protection_contact = models.CharField(max_length=200, blank=True, default="")
    dpo = models.CharField(max_length=200, blank=True, default="")
    supervisory_authority = models.CharField(max_length=200, blank=True, default="")
    register_type = models.CharField(max_length=100, blank=True, default="")
    register_number = models.CharField(max_length=50, blank=True, default="")
    register_court = models.CharField(max_length=200, blank=True, default="")
    legal_representatives = models.CharField(max_length=500, blank=True, default="")
    supervisory_board = models.CharField(max_length=500, blank=True, default="")
    content_responsible = models.CharField(max_length=200, blank=True, default="")
    participates_in_dispute_resolution = models.BooleanField(default=False)
    auditing_association = models.TextField(blank=True, default="")
    professional_association = models.TextField(blank=True, default="")
    legal_notice_extra_html = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    currency = models.CharField(max_length=8, default="EUR")
    timezone = models.CharField(
        max_length=64,
        default="UTC",
        help_text=(
            "Frontend display only. The Django backend uses the process-level "
            "``TIME_ZONE`` (settings.py) for every ``timezone.localdate()`` / "
            "``timezone.now()`` call — it does NOT switch per tenant. Onboarding "
            "a tenant in a different zone would silently get the server's "
            "concept of 'today' for backend business logic. If multi-region "
            "tenants ever become a real product requirement, every "
            "``timezone.localdate()`` callsite needs to flow through this field."
        ),
    )
    date_format = models.CharField(max_length=32, default="DD.MM.YYYY")
    time_format = models.CharField(max_length=16, default="HH:mm")
    csv_format = models.CharField(max_length=8, default="de")
    number_locale = models.CharField(max_length=16, default="de-DE")
    navigation = models.JSONField(default=dict, blank=True)
    ai = models.JSONField(default=dict, blank=True)
    allow_upload_for_data_lists = models.BooleanField(default=True)
    logo = models.ImageField(upload_to="logos/", blank=True, null=True)
    bio_logo = models.ImageField(upload_to="bio_logos/", blank=True, null=True)
    app_icon = models.ImageField(upload_to="app_icons/", blank=True, null=True)
    app_short_name = models.CharField(max_length=12, blank=True, default="")

    @property
    def app_icon_version(self) -> str:
        if not self.app_icon:
            return ""
        return f"{int(self.updated_at.timestamp())}{self.updated_at.microsecond:06d}"

    fiscal_year_start_month = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
    )
    iban = models.CharField(
        max_length=34,
        blank=True,
        null=True,
        validators=[IBANValidator()],
    )
    uid = models.CharField(max_length=20, blank=True, null=True)
    days_until_payment_due = models.IntegerField(default=14)
    sepa_creditor_id = models.CharField(max_length=35, blank=True, default="")
    sepa_creditor_name = models.CharField(max_length=70, blank=True, default="")
    sepa_creditor_bic = models.CharField(max_length=11, blank=True, default="")
    sepa_remittance_template = models.CharField(max_length=140, blank=True, default="")
    privacy_policy_html = models.TextField(blank=True, default="")
    action_rate_limit_overrides = models.JSONField(
        default=dict, blank=True, editable=False
    )
    auto_create_schema = True
    auto_drop_schema = True

    def __str__(self) -> str:
        return self.name


class JasminTenantSettings(TapirModel):
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    has_coop_shares = models.BooleanField(default=True)
    coop_shares_payment_after_admin_confirmation_in_days = models.IntegerField(
        default=14
    )
    value_one_coop_share = models.PositiveIntegerField(default=100)
    min_number_coop_shares = models.PositiveIntegerField(default=3)
    max_number_coop_shares = models.PositiveIntegerField(default=100)
    info_sentence_about_coop_shares = models.TextField(blank=True, null=True)
    retention_period_cancelled_members_coop_shares_in_months = (
        models.PositiveIntegerField(default=0)
    )
    uses_member_loans = models.BooleanField(default=False)
    season_start_week = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(53)],
    )
    min_weeks_from_creation_to_start_delivery = models.PositiveIntegerField(default=2)
    allows_share_type_variation_optin = models.BooleanField(default=False)
    allows_trial_subscriptions = models.BooleanField(default=True)
    allowed_trial_subscription_duration = models.PositiveIntegerField(
        default=4
    )  # in count of deliveries
    allows_trial_subscriptions_for_trial_members = models.BooleanField(default=True)
    info_sentence_about_trial_subscriptions = models.TextField(blank=True, null=True)
    trial_subscriptions_have_different_prices = models.BooleanField(default=False)
    allows_waiting_list_for_subscriptions = models.BooleanField(default=True)
    reservation_ttl_days = models.PositiveIntegerField(default=14)
    uses_jokers = models.BooleanField(default=True)
    default_amount_of_jokers = models.PositiveIntegerField(default=4)
    uses_jokers_for_trial_subscriptions = models.BooleanField(default=False)
    uses_donation_jokers = models.BooleanField(default=False)
    default_amount_of_additional_donation_jokers = models.PositiveIntegerField(
        default=3
    )
    packing_mode = models.CharField(
        max_length=10,
        default="BOXES",
    )
    percentage_added_to_bulk_packing_list = models.PositiveSmallIntegerField(
        blank=True, null=True
    )
    number_packing_stations = models.PositiveIntegerField(default=1)
    allows_solidarity_pricing = models.BooleanField(default=False)
    show_size_column = models.BooleanField(default=True)
    distribute_forecast_by_weight = models.BooleanField(default=False)
    show_summary_in_harvest_share_planning_on_top = models.BooleanField(default=True)
    show_seller_name_of_share_article_in_share_for_member_on_page = models.BooleanField(
        default=True
    )
    round_up_to_full_pu_harvesting = models.BooleanField(default=False)
    allows_self_registration = models.BooleanField(default=False)
    onboarding_mode = models.BooleanField(default=False)
    has_markets = models.BooleanField(default=False)
    sells_to_resellers = models.BooleanField(default=True)
    crates_should_be_on_documents = models.BooleanField(default=True)
    payment_terms_reseller_in_days = models.PositiveIntegerField(default=14)
    early_payment_discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True
    )
    early_payment_discount_days = models.PositiveIntegerField(blank=True, null=True)
    order_numbers_start_new_at_year_change = models.BooleanField(default=False)
    order_number_prefix = models.CharField(max_length=10, default="BE")
    delivery_note_numbers_start_new_at_year_change = models.BooleanField(default=False)
    delivery_note_number_prefix = models.CharField(max_length=10, default="LS")
    invoice_numbers_start_new_at_year_change = models.BooleanField(default=False)
    invoice_number_prefix = models.CharField(max_length=10, default="RE")
    correction_invoice_number_prefix = models.CharField(max_length=10, default="RK")
    left_column_footer_documents_reseller = models.TextField(blank=True, null=True)
    middle_column_footer_documents_reseller = models.TextField(blank=True, null=True)
    right_column_footer_documents_reseller = models.TextField(blank=True, null=True)
    entry_line_1_invoice_reseller = models.TextField(blank=True, null=True)
    entry_line_2_invoice_reseller = models.TextField(blank=True, null=True)
    entry_line_3_invoice_reseller = models.TextField(blank=True, null=True)
    greeting_line_1_invoice_reseller = models.TextField(blank=True, null=True)
    greeting_line_2_invoice_reseller = models.TextField(blank=True, null=True)
    greeting_line_3_invoice_reseller = models.TextField(blank=True, null=True)
    entry_line_1_delivery_note_reseller = models.TextField(blank=True, null=True)
    entry_line_2_delivery_note_reseller = models.TextField(blank=True, null=True)
    entry_line_3_delivery_note_reseller = models.TextField(blank=True, null=True)
    greeting_line_1_delivery_note_reseller = models.TextField(blank=True, null=True)
    greeting_line_2_delivery_note_reseller = models.TextField(blank=True, null=True)
    greeting_line_3_delivery_note_reseller = models.TextField(blank=True, null=True)
    entry_line_1_offer_reseller = models.TextField(blank=True, null=True)
    entry_line_2_offer_reseller = models.TextField(blank=True, null=True)
    entry_line_3_offer_reseller = models.TextField(blank=True, null=True)
    greeting_line_1_offer_reseller = models.TextField(blank=True, null=True)
    greeting_line_2_offer_reseller = models.TextField(blank=True, null=True)
    greeting_line_3_offer_reseller = models.TextField(blank=True, null=True)
    order_instructions_offer_reseller = models.TextField(blank=True, null=True)
    used_tiers_for_offers = models.JSONField(default=list, blank=True, null=True)
    offer_prices_are_per_pu = models.BooleanField(default=False)
    use_personalized_offers = models.BooleanField(default=True)
    subscriptions_end_at_end_of_season = models.BooleanField(default=False)
    subscriptions_end_after_one_year = models.BooleanField(default=True)
    subscriptions_are_auto_renewed = models.BooleanField(default=False)
    min_weeks_to_cancel_before_ending = models.PositiveIntegerField(default=6)
    allows_share_type_variation_change = models.BooleanField(default=False)
    max_share_type_variation_changes = models.PositiveIntegerField(default=1)
    allows_delivery_station_change = models.BooleanField(default=False)
    max_delivery_station_changes = models.PositiveIntegerField(default=1)
    default_planning_granularity = models.CharField(
        max_length=10,
        choices=[("basic", "Basic"), ("tours", "Tours"), ("stations", "Stations")],
        default="basic",
    )
    uses_pledge_round = models.BooleanField(default=False)
    uploads_weekly_share_amount = models.BooleanField(default=False)
    default_tax_rate_articles = models.DecimalField(
        max_digits=5, decimal_places=2, default=7
    )
    default_tax_rate_crates = models.DecimalField(
        max_digits=5, decimal_places=2, default=19
    )
    default_tax_rate_shares = models.DecimalField(
        max_digits=5, decimal_places=2, default=7
    )
    BILLING_STRATEGY_EXACT = "EXACT_PER_PERIOD"
    BILLING_STRATEGY_SMOOTHED = "SMOOTHED"
    BILLING_STRATEGY_CHOICES = [
        (BILLING_STRATEGY_EXACT, "Exact per period (count actual deliveries)"),
        (BILLING_STRATEGY_SMOOTHED, "Smoothed across subscription term"),
    ]
    billing_strategy = models.CharField(
        max_length=20,
        choices=BILLING_STRATEGY_CHOICES,
        default=BILLING_STRATEGY_EXACT,
    )
    bills_joker_deliveries = models.BooleanField(
        default=False,
        help_text="If false, ShareDelivery rows with joker_taken=True are not billed.",
    )
    billing_due_day_of_month = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(28)],
        help_text=(
            "Day of month the charge is due. Capped at 28 to avoid month-length issues."
        ),
    )
    sepa_collection_day_of_month = models.PositiveSmallIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(28)],
        help_text=(
            "Default day of month on which the bank should execute SEPA "
            "direct-debit collections. The billing-run form pre-fills the "
            "collection date with this day of the chosen month (today, if that "
            "day has passed); the office can change it. Nothing moves it for "
            "SEPA lead times or TARGET banking days."
        ),
    )
    require_admin_approval_for_gdpr_deletion = models.BooleanField(
        default=True,
        help_text=(
            "Has no effect: every deletion request needs an office/admin "
            "approval after the email-confirm step, whatever this says."
        ),
    )
    requires_paper_signature_for_membership = models.BooleanField(default=False)
    requires_paper_signature_for_cancellation_of_membership = models.BooleanField(
        default=False
    )
    requires_paper_signature_for_sepa_mandate = models.BooleanField(default=False)
