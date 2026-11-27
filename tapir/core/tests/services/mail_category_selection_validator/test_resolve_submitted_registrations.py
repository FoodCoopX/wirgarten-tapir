from rest_framework.exceptions import ValidationError

from tapir.core.services.mail_category_selection_validator import (
    MailCategorySelectionValidator,
)
from tapir.mail.tests.factories import MailCategoryFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestResolveSubmittedRegistrations(TapirUnitTest):
    def test_resolveSubmittedRegistrations_allCategoriesAvailable_returnsTheStatesByCategory(
        self,
    ):
        category_1 = MailCategoryFactory.build(id="c1")
        category_2 = MailCategoryFactory.build(id="c2")

        result = MailCategorySelectionValidator.resolve_submitted_registrations(
            available_categories=[category_1, category_2],
            categories_registered_to={"c1": True, "c2": False},
        )

        self.assertEqual({category_1: True, category_2: False}, result)

    def test_resolveSubmittedRegistrations_someCategoriesUnavailable_raisesValidationError(
        self,
    ):
        with self.assertRaisesMessage(
            ValidationError, "Diese Mail-Kategorien sind nicht verfügbar: c2, c3"
        ):
            MailCategorySelectionValidator.resolve_submitted_registrations(
                available_categories=[MailCategoryFactory.build(id="c1")],
                categories_registered_to={"c1": True, "c3": True, "c2": False},
            )
