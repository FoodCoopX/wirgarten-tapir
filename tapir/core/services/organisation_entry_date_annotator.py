from django.db.models import QuerySet, F
from tapir_mail.models import StaticSegmentRecipient

from tapir.associations.services.association_entry_date_annotater import (
    AssociationEntryDateAnnotater,
)
from tapir.coop.services.cooperative_entry_date_annotater import (
    CooperativeEntryDateAnnotater,
)
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import (
    legal_status_is_association,
    legal_status_is_cooperative,
    format_date,
)


class OrganisationEntryDateAnnotator:
    ANNOTATION_ORGANISATION_ENTRY_DATE = "organisation_entry_date"

    @classmethod
    def annotate_with_organisation_entry_date(
        cls, queryset: QuerySet[Member], cache: dict
    ):
        if legal_status_is_association(cache=cache):
            queryset = AssociationEntryDateAnnotater.annotate_queryset_with_association_entry_date(
                queryset
            )
            return queryset.annotate(
                **{
                    cls.ANNOTATION_ORGANISATION_ENTRY_DATE: F(
                        AssociationEntryDateAnnotater.ANNOTATION_ASSOCIATION_ENTRY_DATE
                    )
                }
            )

        if legal_status_is_cooperative(cache=cache):
            queryset = CooperativeEntryDateAnnotater.annotate_member_queryset_with_coop_entry_date(
                queryset=queryset
            )
            return queryset.annotate(
                **{
                    cls.ANNOTATION_ORGANISATION_ENTRY_DATE: F(
                        CooperativeEntryDateAnnotater.ANNOTATION_COOP_ENTRY_DATE
                    )
                }
            )

        return queryset.annotate(
            **{cls.ANNOTATION_ORGANISATION_ENTRY_DATE: F("created_at__date")}
        )

    @classmethod
    def get_organisation_entry_date(
        cls, recipient: Member | StaticSegmentRecipient, cache: dict
    ):
        if isinstance(recipient, StaticSegmentRecipient):
            return None

        if not hasattr(recipient, cls.ANNOTATION_ORGANISATION_ENTRY_DATE):
            recipient = cls.annotate_with_organisation_entry_date(
                queryset=Member.objects.filter(id=recipient.id), cache=cache
            ).get()

        return format_date(getattr(recipient, cls.ANNOTATION_ORGANISATION_ENTRY_DATE))
