from tapir.wirgarten_site.registration.forms.summary import SummaryForm
from tapir.wirgarten.views.register import RegistrationWizardViewBase


class RegistrationView(RegistrationWizardViewBase):
    def get_summary_form():
        return SummaryForm
