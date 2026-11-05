from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator

from tapir.configuration.models import TapirParameterDatatype
from tapir.configuration.parameter import ParameterMeta, get_parameter_value
from tapir.wirgarten.constants import ParameterCategory
from tapir.wirgarten.parameter_keys import ParameterKeys as K
from tapir.wirgarten.utils import legal_status_is_association


class DepositConfiguration:
    @staticmethod
    def money(value):
        try:
            amount = Decimal(str(value))
            if (
                not amount.is_finite()
                or amount < 0
                or amount > Decimal("999999.99")
                or amount != amount.quantize(Decimal("0.01"))
            ):
                raise InvalidOperation
            return amount.quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError, TypeError):
            raise ValidationError(
                "Bitte einen gültigen Betrag mit höchstens zwei Nachkommastellen eingeben."
            )

    @classmethod
    def positive_money(cls, value):
        if cls.money(value) == 0:
            raise ValidationError("Der Betrag muss größer als 0 sein.")

    @classmethod
    def define(cls, importer):
        definitions = [
            (
                K.ASSOCIATION_DEPOSIT_INSTALMENTS_ENABLED,
                "Standard-Ratenzahlung bei der Anmeldung erlauben",
                False,
            ),
            (
                K.ASSOCIATION_DEPOSIT_INSTALMENT_COUNT,
                "Anzahl monatlicher Standardraten",
                4,
            ),
            (K.ASSOCIATION_DEPOSIT_ENABLED, "Vereinseinlage aktivieren", False),
            (K.ASSOCIATION_DEPOSIT_NAME, "Name der Vereinseinlage", "Vereinseinlage"),
            (
                K.ASSOCIATION_DEPOSIT_MINIMUM,
                "Mindesteinlage pro Mitglied (€)",
                Decimal("200.00"),
            ),
            (
                K.ASSOCIATION_DEPOSIT_INCREMENT,
                "Schrittgröße zusätzlicher Einlagen (€)",
                Decimal("50.00"),
            ),
            (
                K.ASSOCIATION_DEPOSIT_SUPPORTERS_REQUIRED,
                "Einlage auch für Fördermitglieder erforderlich",
                True,
            ),
            (
                K.ASSOCIATION_DEPOSIT_ALLOW_EXTRA_SIGNUP,
                "Höhere Einlage bei der Anmeldung erlauben",
                True,
            ),
            (
                K.ASSOCIATION_DEPOSIT_ALLOW_EXTRA_MEMBER,
                "Erhöhungen im Mitgliederbereich erlauben",
                True,
            ),
            (
                K.ASSOCIATION_DEPOSIT_ALLOW_HARDSHIP,
                "Anmeldung mit ungeklärtem Härtefall erlauben",
                False,
            ),
            (
                K.ASSOCIATION_DEPOSIT_HARDSHIP_LABEL,
                "Beschriftung der Härtefall-Checkbox",
                "Ich kann die Einlage auch mit Raten nicht zahlen und möchte eine individuelle Vereinbarung treffen.",
            ),
            (
                K.ASSOCIATION_DEPOSIT_HARDSHIP_TEXT,
                "Erläuterung zum Härtefall",
                "Individuelle Vereinbarung offen: Dein Anliegen ist für dich und die Verwaltung sichtbar. Bitte kläre eine Vereinbarung mit der Verwaltung. Bis dahin wird keine Einlage eingezogen.",
            ),
        ]
        for index, (key, label, initial) in enumerate(definitions):
            datatype = (
                TapirParameterDatatype.BOOLEAN
                if isinstance(initial, bool)
                else (
                    TapirParameterDatatype.DECIMAL
                    if isinstance(initial, Decimal)
                    else (
                        TapirParameterDatatype.INTEGER
                        if isinstance(initial, int)
                        else TapirParameterDatatype.STRING
                    )
                )
            )
            importer.parameter_definition(
                key=key,
                label=label,
                initial_value=initial,
                datatype=datatype,
                description=(
                    "Zusätzliche Finanzierung; Vereins- und Erntebeiträge bleiben unverändert."
                    if key == K.ASSOCIATION_DEPOSIT_ENABLED
                    else ""
                ),
                category=ParameterCategory.BUSINESS,
                order_priority=-100 - index,
                meta=ParameterMeta(
                    show_only_when=legal_status_is_association,
                    validators=(
                        [cls.positive_money]
                        if isinstance(initial, Decimal)
                        else (
                            [MinValueValidator(1), MaxValueValidator(120)]
                            if type(initial) is int
                            else []
                        )
                    ),
                ),
            )

    @classmethod
    def get(cls, cache: dict):
        fields = {
            "instalments_enabled": K.ASSOCIATION_DEPOSIT_INSTALMENTS_ENABLED,
            "instalment_count": K.ASSOCIATION_DEPOSIT_INSTALMENT_COUNT,
            "enabled": K.ASSOCIATION_DEPOSIT_ENABLED,
            "name": K.ASSOCIATION_DEPOSIT_NAME,
            "minimum": K.ASSOCIATION_DEPOSIT_MINIMUM,
            "increment": K.ASSOCIATION_DEPOSIT_INCREMENT,
            "supporters_required": K.ASSOCIATION_DEPOSIT_SUPPORTERS_REQUIRED,
            "allow_extra_signup": K.ASSOCIATION_DEPOSIT_ALLOW_EXTRA_SIGNUP,
            "allow_extra_member": K.ASSOCIATION_DEPOSIT_ALLOW_EXTRA_MEMBER,
            "allow_hardship": K.ASSOCIATION_DEPOSIT_ALLOW_HARDSHIP,
            "hardship_label": K.ASSOCIATION_DEPOSIT_HARDSHIP_LABEL,
            "hardship_text": K.ASSOCIATION_DEPOSIT_HARDSHIP_TEXT,
        }
        result = {
            name: get_parameter_value(key, cache=cache) for name, key in fields.items()
        }
        result["minimum"] = cls.money(result["minimum"])
        result["increment"] = cls.money(result["increment"])
        result["enabled"] = result["enabled"] and legal_status_is_association(
            cache=cache
        )
        return result
