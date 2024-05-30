from tapir.wirgarten.views.register import RegistrationWizardViewBase
from tapir.wirgarten_site.registration.forms.summary import SummaryForm


class RegistrationView(RegistrationWizardViewBase):
    @classmethod
    def get_summary_form(cls):
        return SummaryForm
