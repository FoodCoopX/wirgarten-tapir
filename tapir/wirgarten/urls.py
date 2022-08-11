from django.urls import path

from tapir.wirgarten.views import RegistrationWizardView, RegistrationWizardConfirmView

app_name = "wirgarten"
urlpatterns = [
    path(
        "register",
        RegistrationWizardView.as_view(),
        name="draftuser_register",
    ),
    path(
        "register/confirm",
        RegistrationWizardConfirmView.as_view(),
        name="draftuser_confirm_registration",
    ),
]
