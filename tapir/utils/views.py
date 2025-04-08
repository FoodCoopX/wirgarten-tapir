from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.urls import reverse
from django.views.generic import FormView

from tapir.utils.config import Organization
from tapir.utils.forms import ResetTestDataForm
from tapir.utils.services.test_data_generator import TestDataGenerator
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.utils import is_debug_instance


class ResetTestData(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    form_class = ResetTestDataForm
    permission_required = Permission.Coop.MANAGE
    template_name = "utils/reset_test_data.html"

    def get_success_url(self):
        return reverse("wirgarten:product")

    def form_valid(self, form):
        if not is_debug_instance():
            raise ImproperlyConfigured("Don't reset data on non-debug instances.")

        with transaction.atomic():
            TestDataGenerator.clear()
            TestDataGenerator.generate_all(
                Organization[form.cleaned_data["generate_test_data_for"]]
            )

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["page_title"] = "Reset test data"
        context_data["card_title"] = context_data["page_title"]
        return context_data
