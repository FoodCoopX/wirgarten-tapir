from decimal import Decimal

from django.core.exceptions import ValidationError

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys


class CoopShareInstalmentConfigValidator:
    @staticmethod
    def validate_instalment_amount(instalment_amount: Decimal):
        if instalment_amount <= 0:
            # Already rejected by MinValueValidator, but all validators run
            return

        try:
            share_price = get_parameter_value(key=ParameterKeys.COOP_SHARE_PRICE)
        except KeyError:
            # During the first setup of the instance, the share price parameter may not be defined yet.
            return
        if Decimal(share_price) % instalment_amount != 0:
            raise ValidationError(
                f"Der Preis eines Anteils ({share_price} €) muss durch die Höhe einer Rate teilbar sein."
            )
