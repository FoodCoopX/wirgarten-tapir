from tapir_mail.models import (
    EmailConfiguration,
    EmailConfigurationVersion,
    EmailTemplate,
    EmailTemplateType,
    ReleaseStatus,
)
from tapir_mail.triggers.transactional_trigger import TransactionalTrigger

EMPTY_MJML = "<mjml><mj-head></mj-head><mj-body></mj-body></mjml>"


class MailTriggerGenerator:
    @classmethod
    def generate_required_triggers(cls):
        cache = {}
        layout_enabled = EmailTemplate.objects.filter(
            template_type=EmailTemplateType.LAYOUT,
            is_default_layout=True,
        ).exists()

        for key in TransactionalTrigger.required_triggers.keys():
            if not TransactionalTrigger.is_trigger_required(key=key, cache=cache):
                continue
            cls._create_released_version(key=key, layout_enabled=layout_enabled)

    @staticmethod
    def _create_released_version(key: str, layout_enabled: bool):
        name = TransactionalTrigger.transactional_trigger_registry[key]
        email_configuration = EmailConfiguration.objects.create(name=name)
        default_content = TransactionalTrigger.required_trigger_to_default_content_map[
            key
        ]

        EmailConfigurationVersion.objects.create(
            content=EMPTY_MJML.replace("</mj-body>", default_content + "</mj-body>"),
            subject=name,
            email_configuration=email_configuration,
            status=ReleaseStatus.RELEASED,
            triggers=[
                {
                    "trigger_id": TransactionalTrigger.get_id(),
                    "trigger_field_values": {"key": key},
                }
            ],
            layout_enabled=layout_enabled,
        )
