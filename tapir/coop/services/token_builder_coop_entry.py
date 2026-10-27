from tapir.associations.models import AssociationMembership
from tapir.associations.services.association_membership_price_type_getter import (
    AssociationMembershipTypePriceGetter,
)
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.wirgarten.models import CoopShareTransaction
from tapir.wirgarten.utils import format_currency, format_date


class TokenBuilderCoopEntry:
    @classmethod
    def build_mail_tokens_for_coop_entry(
        cls,
        coop_share_transaction: CoopShareTransaction | None,
        association_membership: AssociationMembership | None,
        solidarity_contribution: SolidarityContribution | None,
        cache: dict,
    ):
        tokens = {
            "number_of_coop_shares": "0",
            "price_of_a_coop_share": format_currency(0),
            "total_cost": format_currency(0),
            "coop_shares_payment_method": "",
            "membership_start_date": "Keine Datum",
            "solidarity_contribution_amount": format_currency(0),
            "solidarity_contribution_start_date": "Kein Datum",
            "membership_monthly_price": format_currency(0),
        }
        if coop_share_transaction is not None:
            tokens |= {
                "number_of_coop_shares": coop_share_transaction.quantity,
                "price_of_a_coop_share": format_currency(
                    coop_share_transaction.share_price
                ),
                "total_cost": format_currency(coop_share_transaction.total_price),
                "coop_shares_payment_method": cls.build_payment_method(
                    coop_share_transaction
                ),
                "membership_start_date": format_date(coop_share_transaction.valid_at),
            }

        if solidarity_contribution is not None:
            tokens |= {
                "solidarity_contribution_amount": format_currency(
                    solidarity_contribution.amount
                ),
                "solidarity_contribution_start_date": (
                    format_date(solidarity_contribution.start_date)
                ),
            }
        if association_membership is not None:
            tokens |= {
                "membership_start_date": format_date(association_membership.start_date),
                "membership_monthly_price": format_currency(
                    AssociationMembershipTypePriceGetter.get_price(
                        membership_type=association_membership.type,
                        reference_date=association_membership.start_date,
                        cache=cache,
                    )
                ),
            }

        return tokens

    @staticmethod
    def build_payment_method(coop_share_transaction: CoopShareTransaction):
        instalments = list(
            coop_share_transaction.payments.filter(instalment_number__isnull=False)
        )
        if len(instalments) == 0:
            return "einmalig"
        return f"in {len(instalments)} monatlichen Raten à {format_currency(instalments[0].amount)} €"
