from typing import Callable

from tapir.associations.models import AssociationMembership
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.wirgarten.models import Subscription

type TokenReplacers = dict[str, Callable[[], str]]
type TapirContract = Subscription | SolidarityContribution | AssociationMembership
