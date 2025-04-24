import re
from typing import Dict

from django.core.exceptions import ValidationError

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys


class AssociationMembershipsManager:
    @classmethod
    def get_association_memberships(
        cls, memberships_as_string: str = None, cache: Dict = None
    ) -> Dict[str, float]:
        if memberships_as_string is None:
            memberships_as_string = get_parameter_value(
                ParameterKeys.COOP_ASSOCIATION_MEMBERSHIPS, cache=cache
            )

        if memberships_as_string == "disabled":
            return {}

        memberships = {}
        for membership_as_string in memberships_as_string.split(";"):
            if membership_as_string.strip() == "":
                continue

            # Example: membership A[12.5]
            result = re.search(r"(.+)\[(.+)]", membership_as_string)
            if result is None:
                raise ValidationError(
                    f"Invalid restriction given: {membership_as_string}"
                )

            (
                category_name,
                preis_as_string,
            ) = result.groups()
            category_name = category_name.strip()
            preis_as_string = preis_as_string.replace(",", ".")
            memberships[category_name] = float(preis_as_string)

        return memberships

    @classmethod
    def validate_association_memberships(cls, memberships_as_string: str):
        try:
            cls.get_association_memberships(memberships_as_string)
        except Exception as e:
            raise ValidationError(f"Invalid association memberships value: {e}")
