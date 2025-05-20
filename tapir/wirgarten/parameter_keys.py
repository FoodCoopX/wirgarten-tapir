PREFIX = "wirgarten"


class ParameterKeys:
    MEMBER_PICKUP_LOCATION_CHANGE_UNTIL = (
        f"{PREFIX}.member.pickup_location_change_until"
    )
    MEMBER_BYPASS_KEYCLOAK = f"{PREFIX}.temporarily.bypass_keycloak"
    SITE_NAME = f"{PREFIX}.site.name"
    SITE_STREET = f"{PREFIX}.site.street"
    SITE_CITY = f"{PREFIX}.site.city"
    SITE_EMAIL = f"{PREFIX}.site.email"
    SITE_ADMIN_EMAIL = f"{PREFIX}.site.admin_email"
    SITE_ADMIN_NAME = f"{PREFIX}.site.admin_name"
    SITE_ADMIN_TELEPHONE = f"{PREFIX}.site.admin_telephone"
    SITE_ADMIN_IMAGE = f"{PREFIX}.site.admin_image"
    SITE_PRIVACY_LINK = f"{PREFIX}.site.privacy_link"
    SITE_FAQ_LINK = f"{PREFIX}.site.faq_link"
    COOP_MIN_SHARES = f"{PREFIX}.coop.min_shares"
    COOP_STATUTE_LINK = f"{PREFIX}.coop.statute_link"
    COOP_INFO_LINK = f"{PREFIX}.coop.info_link"
    COOP_BASE_PRODUCT_TYPE = f"{PREFIX}.coop.base_product_type"
    COOP_SHARES_INDEPENDENT_FROM_HARVEST_SHARES = f"{PREFIX}.coop.shares_independent"
    COOP_MEMBERSHIP_NOTICE_PERIOD = f"{PREFIX}.coop.membership_notice_period"
    COOP_MEMBERSHIP_NOTICE_PERIOD_UNIT = f"{PREFIX}.coop.membership_notice_period_unit"
    CHICKEN_MAX_SHARES = f"{PREFIX}.chicken.max_shares"
    HARVEST_NEGATIVE_SOLIPRICE_ENABLED = f"{PREFIX}.harvest.negative_soliprice_enabled"
    HARVEST_MEMBERS_ARE_ALLOWED_TO_CHANGE_SOLIPRICE = (
        f"{PREFIX}.harvest.members_are_allowed_to_change_soliprice"
    )
    SUPPLIER_LIST_PRODUCT_TYPES = f"{PREFIX}.supplier_list.product_types"
    SUPPLIER_LIST_SEND_ADMIN_EMAIL = f"{PREFIX}.supplier_list.admin_email_enabled"
    PICKING_SEND_ADMIN_EMAIL = f"{PREFIX}.pick_list.admin_email_enabled"
    PICKING_PRODUCT_TYPES = f"{PREFIX}.pick_list.product_types"
    PICKING_MODE = f"{PREFIX}.picking.picking_mode"
    PICKING_BASKET_SIZES = f"{PREFIX}.picking.basket_sizes"
    PAYMENT_DUE_DAY = f"{PREFIX}.payment.due_date"
    DELIVERY_DAY = f"{PREFIX}.delivery.weekday"
    MEMBER_RENEWAL_ALERT_UNKOWN_HEADER = (
        f"{PREFIX}.member.dashboard.renewal_alert.unkown.header"
    )
    MEMBER_RENEWAL_ALERT_UNKOWN_CONTENT = (
        f"{PREFIX}.member.dashboard.renewal_alert.unkown.content"
    )
    MEMBER_RENEWAL_ALERT_CANCELLED_HEADER = (
        f"{PREFIX}.member.dashboard.renewal_alert.cancelled.header"
    )
    MEMBER_RENEWAL_ALERT_CANCELLED_CONTENT = (
        f"{PREFIX}.member.dashboard.renewal_alert.cancelled.content"
    )
    MEMBER_RENEWAL_ALERT_RENEWED_HEADER = (
        f"{PREFIX}.member.dashboard.renewal_alert.renewed.header"
    )
    MEMBER_RENEWAL_ALERT_RENEWED_CONTENT = (
        f"{PREFIX}.member.dashboard.renewal_alert.renewed.content"
    )
    MEMBER_RENEWAL_ALERT_WAITLIST_HEADER = (
        f"{PREFIX}.member.dashboard.renewal_alert.waitlist.header"
    )
    MEMBER_RENEWAL_ALERT_WAITLIST_CONTENT = (
        f"{PREFIX}.member.dashboard.renewal_alert.waitlist.content"
    )
    MEMBER_CANCELLATION_REASON_CHOICES = f"{PREFIX}.member.cancellation_reason.choices"
    EMAIL_NOT_RENEWED_CONFIRMATION_SUBJECT = (
        f"{PREFIX}.email.not_renewed_confirmation.subject"
    )
    EMAIL_NOT_RENEWED_CONFIRMATION_CONTENT = (
        f"{PREFIX}.email.not_renewed_confirmation.content"
    )
    EMAIL_CONTRACT_ORDER_CONFIRMATION_SUBJECT = (
        f"{PREFIX}.email.contract_order_confirmation.subject"
    )
    EMAIL_CONTRACT_ORDER_CONFIRMATION_CONTENT = (
        f"{PREFIX}.email.contract_order_confirmation.content"
    )
    EMAIL_CONTRACT_CHANGE_CONFIRMATION_SUBJECT = (
        f"{PREFIX}.email.contract_change_confirmation.subject"
    )
    EMAIL_CONTRACT_CHANGE_CONFIRMATION_CONTENT = (
        f"{PREFIX}.email.contract_change_confirmation.content"
    )
    JOKERS_ENABLED = f"{PREFIX}.jokers.enabled"
    SUBSCRIPTION_AUTOMATIC_RENEWAL = f"{PREFIX}.subscriptions.automatic_renewal"
    SUBSCRIPTION_DEFAULT_NOTICE_PERIOD = f"{PREFIX}.subscriptions.default_notice_period"
    SUBSCRIPTION_DEFAULT_NOTICE_PERIOD_UNIT = (
        f"{PREFIX}.subscriptions.default_notice_period_unit"
    )
    SUBSCRIPTION_ADDITIONAL_PRODUCT_ALLOWED_WITHOUT_BASE_PRODUCT = (
        f"{PREFIX}.subscriptions.additional_product_allowed_without_base_product"
    )
    SUBSCRIPTION_WAITING_LIST_CATEGORIES = (
        f"{PREFIX}.subscriptions.waiting_list_categories"
    )
    TESTS_OVERRIDE_DATE_PRESET = f"{PREFIX}.tests.override_date_preset"
    TESTS_OVERRIDE_DATE = f"{PREFIX}.tests.override_date"
    ORGANISATION_LEGAL_STATUS = f"{PREFIX}.organisation.legal_status"
    SUBSCRIPTION_FOUR_WEEK_CYCLE_START_POINT = (
        f"{PREFIX}.subscriptions.four_week_cycle_start_point"
    )
