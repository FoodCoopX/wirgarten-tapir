from tapir.mail.addressed_recipient import AddressedRecipient
from tapir.mail.models import EmailConfigurationDispatch
from tapir.mail.services.segment import resolve_segments


class RecipientListProvider:
    @staticmethod
    def get_recipient_list_from_email_configuration_dispatch(
        email_configuration_dispatch: EmailConfigurationDispatch, cache: dict
    ) -> list[AddressedRecipient]:
        version = email_configuration_dispatch.email_configuration_version
        return resolve_segments(
            dynamic_segment_names_additive=version.dynamic_segments_additive,
            dynamic_segment_names_subtractive=version.dynamic_segments_subtractive,
            static_segment_ids_additive=version.static_segments_additive.values_list(
                "id", flat=True
            ),
            static_segment_ids_subtractive=version.static_segments_subtractive.values_list(
                "id", flat=True
            ),
            mail_category_ids_additive=version.mail_categories_additive.values_list(
                "id", flat=True
            ),
            override_recipients=email_configuration_dispatch.override_recipients,
            cache=cache,
        )
