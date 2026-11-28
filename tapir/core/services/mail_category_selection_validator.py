from rest_framework.exceptions import ValidationError

from tapir.mail.models import MailCategory


class MailCategorySelectionValidator:
    @staticmethod
    def resolve_submitted_registrations(
        available_categories: list[MailCategory],
        categories_registered_to: dict[str, bool],
    ) -> dict[MailCategory, bool]:
        categories_by_id = {category.id: category for category in available_categories}
        unavailable_ids = sorted(set(categories_registered_to) - set(categories_by_id))
        if unavailable_ids:
            raise ValidationError(
                f"Diese Mail-Kategorien sind nicht verfügbar: {', '.join(unavailable_ids)}"
            )

        return {
            categories_by_id[category_id]: is_registered
            for category_id, is_registered in categories_registered_to.items()
        }
