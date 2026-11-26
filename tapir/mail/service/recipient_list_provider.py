from tapir.mail.models import EmailConfigurationDispatch, EmailConfigurationVersion
from tapir.mail.service.segment import resolve_segments


class RecipientListProvider:
    @classmethod
    def get_recipient_list_from_email_configuration_dispatch(
        cls,
        email_configuration_dispatch: EmailConfigurationDispatch,
    ) -> list:
        if email_configuration_dispatch.is_sent:
            return [
                dispatch.recipient
                for dispatch in email_configuration_dispatch.emaildispatch_set.all()
            ]

        return cls.get_recipient_list_from_email_configuration_version(
            version=email_configuration_dispatch.email_configuration_version,
            override_recipients=email_configuration_dispatch.override_recipients,
        )

    @staticmethod
    def get_recipient_list_from_email_configuration_version(
        version: EmailConfigurationVersion, override_recipients: list | None
    ) -> list:
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
            override_recipients=override_recipients,
        )
