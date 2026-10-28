from django.core.exceptions import ValidationError

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys


class CoopShareInstalmentOrderValidator:
    @staticmethod
    def validate_instalments(
        number_of_coop_shares: int, minimum_number_of_coop_shares: int, cache: dict
    ):
        if not get_parameter_value(
            key=ParameterKeys.COOP_SHARES_INSTALMENTS_ENABLED, cache=cache
        ):
            raise ValidationError("Ratenzahlung ist nicht möglich")

        if number_of_coop_shares != minimum_number_of_coop_shares:
            raise ValidationError(
                f"Ratenzahlung ist nur für die Mindestanzahl an Genossenschaftsanteilen ({minimum_number_of_coop_shares}) möglich"
            )
