from django.urls import path

from tapir.bestell_wizard import views

app_name = "bestell_wizard"
urlpatterns = [
    path(
        "api/bestell_wizard_capacity_check",
        views.BestellWizardCapacityCheckApiView.as_view(),
        name="bestell_wizard_capacity_check",
    ),
    path(
        "api/bestell_wizard_base_data",
        views.BestellWizardBaseDataApiView.as_view(),
        name="bestell_wizard_base_data",
    ),
    path(
        "api/bestell_wizard_delivery_dates",
        views.BestellWizardDeliveryDatesForOrderApiView.as_view(),
        name="bestell_wizard_delivery_dates",
    ),
    path(
        "bestell_wizard",
        views.BestellWizardView.as_view(),
        name="bestell_wizard",
    ),
    path(
        "bestell_wizard_mobile",
        views.BestellWizardMobileView.as_view(),
        name="bestell_wizard_mobile",
    ),
    path(
        "bestell_wizard_confirm_order",
        views.BestellWizardConfirmOrderApiView.as_view(),
        name="bestell_wizard_confirm_order",
    ),
    path(
        "api/is_email_address_valid",
        views.PublicBestellWizardIsEmailAddressValidApiView.as_view(),
        name="is_email_address_valid",
    ),
    path(
        "api/earliest_contract_start_date",
        views.GetEarliestContractStartDateApiView.as_view(),
        name="earliest_contract_start_date",
    ),
    path(
        "api/contract_start_date_waiting_list_entry",
        views.GetContractStartDateForWaitingListEntryApiView.as_view(),
        name="contract_start_date_waiting_list_entry",
    ),
    path(
        "api/product_prices",
        views.PublicProductPricesApiView.as_view(),
        name="product_prices",
    ),
]
