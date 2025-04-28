from typing import Dict

from tapir.configuration.parameter import get_parameter_value
from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.wirgarten.parameter_keys import ParameterKeys


class MembershipTextService:
    @classmethod
    def get_membership_text(cls, cache: Dict):
        if (
            get_parameter_value(ParameterKeys.ORGANISATION_LEGAL_STATUS, cache=cache)
            == LEGAL_STATUS_ASSOCIATION
        ):
            return "Beitrittserklärung zum Verein"

        return "Beitrittserklärung zur Genossenschaft"
