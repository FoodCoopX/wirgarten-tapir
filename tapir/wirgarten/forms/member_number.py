from django.forms import IntegerField, ModelForm
from django.utils.translation import gettext_lazy as _

from tapir.coop.services.member_number_service import MemberNumberService
from tapir.wirgarten.forms.member import PersonalDataForm
from tapir.wirgarten.models import Member


class MemberNumberForm(ModelForm):
    member_no = IntegerField(
        label=_("Mitgliedsnummer"),
        min_value=1,
        error_messages={"unique": MemberNumberService.DUPLICATE_NUMBER_MESSAGE},
        help_text=_("Bestehende Mandatsreferenzen bleiben unverändert."),
    )

    class Meta:
        model = Member
        fields = ["member_no"]


class AdminMemberCreationForm(PersonalDataForm):
    member_no = IntegerField(
        label=_("Mitgliedsnummer (optional)"),
        required=False,
        min_value=1,
        error_messages={"unique": MemberNumberService.DUPLICATE_NUMBER_MESSAGE},
        help_text=_(
            "Vorhandene Mitgliedsnummer übernehmen. Ohne Angabe wird automatisch eine Nummer vergeben."
        ),
    )

    class Meta(PersonalDataForm.Meta):
        fields = [*PersonalDataForm.Meta.fields, "member_no"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["member_no"].required = False
