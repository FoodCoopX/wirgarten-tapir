from nanoid import generate

from tapir.core.models import ID_LENGTH
from tapir.wirgarten.models import MandateReference

MANDATE_REF_LENGTH = 35
MANDATE_REF_ALPHABET = "1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ"
GENO_SUFFIX = "/GENO"
SUBS_SUFFIX = "/PROD"


def generate_mandate_ref(member_id: int | str, coop_shares: bool):
    prefix = f"""{str(member_id).zfill(ID_LENGTH)}/"""

    def __generate_ref(suffix):
        return f"""{generate(MANDATE_REF_ALPHABET, MANDATE_REF_LENGTH - len(prefix) - len(suffix))}{suffix}"""

    return f"""{prefix}{__generate_ref(GENO_SUFFIX if coop_shares else SUBS_SUFFIX)}"""


def is_mandate_ref_for_coop_shares(mandate_ref: str | MandateReference):
    if type(mandate_ref) == MandateReference:
        mandate_ref = mandate_ref.ref

    return mandate_ref.endswith(GENO_SUFFIX)
