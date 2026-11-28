import re

from rest_framework.exceptions import ValidationError

from tapir.mail.services.token import token_registry
from tapir.mail.triggers.transactional_trigger import TransactionalTrigger


class MailContentValidator:
    @staticmethod
    def validate_tokens(mail_content: str, trigger_datas: list[dict]):
        pattern = re.compile(r"\{\{\s*(.*?)\s*}}")
        matches = pattern.findall(mail_content)
        tokens = set(matches)

        valid_tokens = set()
        for token_type, known_tokens in token_registry.items():
            for key in known_tokens.keys():
                valid_tokens.add(f"{token_type}.{key}")

        for trigger_data in trigger_datas:
            trigger_key = trigger_data.get("trigger_field_values", {}).get("key", None)
            if trigger_key is None:
                continue
            trigger_name = TransactionalTrigger.transactional_trigger_registry.get(
                trigger_key, None
            )
            if trigger_name is None:
                continue
            trigger_tokens = TransactionalTrigger.trigger_tokens.get(trigger_key, {})

            valid_tokens.update({f"{trigger_name}.{token}" for token in trigger_tokens})

        invalid_tokens = {token for token in tokens if token not in valid_tokens}

        if len(invalid_tokens) > 0:
            raise ValidationError(
                f"Folgende Tokens sind nicht bekannt: {invalid_tokens}. Sollen die Tokens im Editor richtig aussehen, den Fehler aber trotzdem auftreten, lösche bitte die ganze Zeile mit dem Token und schreib sie neu um versteckte Schriftzeichen zu vermeiden."
            )
