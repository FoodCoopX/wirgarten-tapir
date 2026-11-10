import datetime

from django.core.management.base import OutputWrapper
from django.utils import timezone

from tapir.accounts.models import TapirUser
from tapir.accounts.services.email_normaliser import EmailNormaliser
from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager
from tapir.associations.models import (
    AssociationMembership,
    AssociationMembershipType,
    AssociationMembershipCreatedLogEntry,
    AssociationMembershipUpdatedLogEntry,
)
from tapir.bakery.models import PreferredBread, Bread
from tapir.configuration.parameter import get_parameter_value
from tapir.log.models import TextLogEntry
from tapir.log.util import freeze_for_log
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.pickup_locations.services.home_delivery_address_validator import (
    HomeDeliveryAddressValidator,
)
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.utils.config import (
    MEMBER_IMPORT_STATUS_UPDATED,
    MEMBER_IMPORT_STATUS_SKIPPED,
    MEMBER_IMPORT_STATUS_CREATED,
)
from tapir.utils.exceptions import TapirDataImportException
from tapir.utils.models import MemberImportedLogEntry, MemberImportUpdatedLogEntry
from tapir.utils.services.data_import_utils import DataImportUtils
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import (
    PickupLocation,
    Member,
    MemberPickupLocation,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import get_now, get_today

DELIVERY_ADDRESS_COLUMNS = {
    "Lieferadresse Straße": "delivery_street",
    "Lieferadresse Adresszusatz": "delivery_street_2",
    "Lieferadresse PLZ": "delivery_postcode",
    "Lieferadresse Ort": "delivery_city",
}


class MemberImporter:
    @classmethod
    def import_member(
        cls,
        row: dict[str, str],
        update_existing: bool,
        dry_run: bool,
        stdout: OutputWrapper,
    ):
        if DataImportUtils.is_row_empty(row):
            return None

        member_no = int(DataImportUtils.normalize_cell(row.get("Nr")))
        member = Member.objects.filter(member_no=member_no).first()

        if member:
            if not update_existing:
                return MEMBER_IMPORT_STATUS_SKIPPED

            try:
                return cls.update_existing_member_if_necessary(
                    member=member, row=row, dry_run=dry_run
                )
            except Exception as e:
                raise TapirDataImportException(
                    f"Error updating member {member_no}: {e}"
                )

        try:
            return cls.create_new_member(
                member_no=member_no, row=row, dry_run=dry_run, stdout=stdout
            )
        except Exception as e:
            raise TapirDataImportException(f"Error creating member {member_no}: {e}")

    @classmethod
    def get_pickup_location_by_name(cls, name: str):
        if name == "":
            return None

        pickup_location = PickupLocation.objects.filter(name=name).first()
        if pickup_location is None:
            raise TapirDataImportException(f"No pickup location found with name {name}")

        return pickup_location

    @classmethod
    def update_existing_member_if_necessary(
        cls, member: Member, row: dict[str, str], dry_run: bool
    ):
        member_before = freeze_for_log(member)
        member_attributes_updated = cls.update_member_attributes_and_save_member(
            member=member, row=row, dry_run=dry_run
        )
        if member_attributes_updated:
            MemberImportUpdatedLogEntry().populate(
                old_frozen=member_before, new_model=member, actor=None, user=member
            ).save()
        pickup_location_updated = cls.update_member_pickup_location(
            member=member, row=row
        )
        solidarity_updated = cls.update_solidarity_contribution(member=member, row=row)

        payment_rhythm_updated = cls.update_payment_rhythm_if_necessary(
            member=member,
            reference_date=cls.get_payment_rhythm_reference_date(member=member),
            rhythm_from_import=row.get("Zahlungsintervall", None),
        )

        association_membership_updated = cls.update_association_membership_if_necessary(
            member=member, row=row
        )

        preferred_breads_updated = cls.update_preferred_breads(member=member, row=row)

        if (
            member_attributes_updated
            or pickup_location_updated
            or solidarity_updated
            or payment_rhythm_updated
            or association_membership_updated
            or preferred_breads_updated
        ):
            return MEMBER_IMPORT_STATUS_UPDATED
        return MEMBER_IMPORT_STATUS_SKIPPED

    @classmethod
    def update_payment_rhythm_if_necessary(
        cls, member, rhythm_from_import: str | None, reference_date: datetime.date
    ):
        current_payment_rhythm = MemberPaymentRhythmService.get_member_payment_rhythm(
            member=member, cache={}, reference_date=reference_date
        )

        if rhythm_from_import is None or rhythm_from_import == "":
            target_payment_rhythm = get_parameter_value(
                ParameterKeys.PAYMENT_DEFAULT_RHYTHM, cache={}
            )
        else:
            target_payment_rhythm = (
                MemberPaymentRhythmService.get_rhythm_from_display_name(
                    display_name=rhythm_from_import
                )
            )

        if current_payment_rhythm == target_payment_rhythm:
            return False

        MemberPaymentRhythmService.assign_payment_rhythm_to_member(
            member=member,
            rhythm=target_payment_rhythm,
            valid_from=reference_date,
            actor=None,
            cache={},
        )
        return True

    @classmethod
    def update_member_attributes_and_save_member(
        cls, member: Member, row: dict[str, str], dry_run: bool
    ):
        member_updated = False
        email_before = member.email

        map_from_row_header_to_member_attribute = {
            "Vorname": "first_name",
            "Nachname": "last_name",
            "Geburtstag/Gründungsdatum": "birthdate",
            "Anrede": "form_of_address",
            "PLZ": "postcode",
            "Ort": "city",
            "Telefon": "phone_number",
            "Telefon 2": "phone_number_landline",
            "IBAN": "iban",
            "Kontoinhaber": "account_owner",
            "Pseudonym": "pseudonym",
        }

        map_from_row_header_to_converter = {
            "Geburtstag/Gründungsdatum": DataImportUtils.to_date,
            "IBAN": lambda value: DataImportUtils.normalize_cell(value).replace(
                " ", ""
            ),
        }

        for (
            row_header,
            member_attribute,
        ) in map_from_row_header_to_member_attribute.items():
            converter = map_from_row_header_to_converter.get(
                row_header, DataImportUtils.normalize_cell
            )
            if DataImportUtils.update_if_diff(
                member,
                member_attribute,
                converter(row.get(row_header)),
            ):
                member_updated = True

        target_consents = {
            "sepa_consent": DataImportUtils.get_value_or_default(
                row=row,
                column="consent_sepa",
                converter=DataImportUtils.to_datetime,
                current_value=member.sepa_consent,
                default=get_now(cache={}),
                use_default=DataImportUtils.is_cell_filled(row=row, column="IBAN"),
            ),
            "privacy_consent": DataImportUtils.get_value_or_default(
                row=row,
                column="privacy_consent",
                converter=DataImportUtils.to_datetime,
                current_value=member.privacy_consent,
                default=get_now(cache={}),
                use_default=True,
            ),
        }
        for member_attribute, target_consent in target_consents.items():
            if DataImportUtils.update_if_diff(member, member_attribute, target_consent):
                member_updated = True

        new_street = " ".join(
            s.strip()
            for s in [
                DataImportUtils.normalize_cell(row.get("Straße")),
                DataImportUtils.normalize_cell(row.get("Hausnr.")),
            ]
            if s and s.strip() != ""
        )
        if DataImportUtils.update_if_diff(member, "street", new_street):
            member_updated = True

        if cls.update_delivery_address(member=member, row=row):
            member_updated = True

        target_mail = cls.build_mail(row=row, member_no=member.member_no)
        if DataImportUtils.update_if_diff(
            member,
            "email",
            target_mail,
        ):
            member_updated = True
            member.username = member.email

        if email_before != member.email and member.keycloak_id:
            Member.objects.filter(id=member.id).update(email=member.email)
            if not dry_run:
                KeycloakUserManager.get_keycloak_client().update_user(
                    user_id=member.keycloak_id, payload={"email": member.email}
                )

        if member_updated:
            member.save()

        return member_updated

    @classmethod
    def update_delivery_address(cls, member: Member, row: dict[str, str]) -> bool:
        if not any(
            DataImportUtils.is_cell_filled(row=row, column=column)
            for column in DELIVERY_ADDRESS_COLUMNS
        ):
            return False

        member_updated = DataImportUtils.update_if_diff(
            member, "delivery_same_as_billing_address", False
        )
        for column, member_attribute in DELIVERY_ADDRESS_COLUMNS.items():
            if DataImportUtils.update_if_diff(
                member,
                member_attribute,
                DataImportUtils.normalize_cell(row.get(column)),
            ):
                member_updated = True
        return member_updated

    @classmethod
    def build_mail(cls, row: dict[str, str], member_no: int):
        target_mail = DataImportUtils.normalize_cell(row.get("Mailadresse"))
        if target_mail == "":
            return f"team+missing_mail_katringer_{member_no}@foodcoopx.de"

        with_suffix = cls.build_mail_with_suffix(
            original_mail=target_mail, member_no=member_no
        )
        return EmailNormaliser.normalise(with_suffix)

    @classmethod
    def build_mail_with_suffix(cls, original_mail: str, member_no: int):
        other_members = Member.objects.exclude(member_no=member_no)
        if not other_members.filter(email=original_mail).exists():
            return original_mail

        counter = 1
        prefix, suffix = original_mail.split("@", maxsplit=1)
        while other_members.filter(email=f"{prefix}+{counter}@{suffix}").exists():
            counter += 1

        return f"{prefix}+{counter}@{suffix}"

    @classmethod
    def update_member_pickup_location(cls, member: Member, row: dict[str, str]):
        target_pickup_location = cls.get_pickup_location_by_name(
            name=DataImportUtils.normalize_cell(row.get("Abholort"))
        )
        member_pickup_location = MemberPickupLocation.objects.filter(
            member=member
        ).first()

        if target_pickup_location is None:
            if member_pickup_location is None:
                return False

            MemberPickupLocation.objects.filter(member=member).delete()
            return True

        HomeDeliveryAddressValidator.validate(
            address_owner=member, pickup_location=target_pickup_location
        )

        if member_pickup_location is None:
            MemberPickupLocation.objects.create(
                member=member,
                pickup_location=target_pickup_location,
                valid_from=cls.get_pickup_location_valid_from(
                    row=row, current_value=None
                ),
            )
            return True

        target_valid_from = cls.get_pickup_location_valid_from(
            row=row,
            current_value=(
                member_pickup_location.valid_from
                if member_pickup_location.pickup_location == target_pickup_location
                else None
            ),
        )
        location_updated = DataImportUtils.update_if_diff(
            member_pickup_location, "pickup_location", target_pickup_location
        )
        valid_from_updated = DataImportUtils.update_if_diff(
            member_pickup_location, "valid_from", target_valid_from
        )
        updated = location_updated or valid_from_updated

        if updated:
            member_pickup_location.save()

        return updated

    @classmethod
    def get_pickup_location_valid_from(
        cls, row: dict[str, str], current_value: datetime.date | None
    ):
        return DataImportUtils.get_value_or_default(
            row=row,
            column="AO_gueltig_ab",
            converter=DataImportUtils.to_date,
            current_value=current_value,
            default=get_today(cache={}),
            use_default=DataImportUtils.is_cell_filled(row=row, column="Abholort"),
        )

    @staticmethod
    def get_payment_rhythm_reference_date(member: Member):
        if member.sepa_consent is None:
            return None
        return timezone.localdate(member.sepa_consent)

    @classmethod
    def update_solidarity_contribution(cls, member: Member, row: dict[str, str]):
        target_amount = DataImportUtils.safe_float(row.get("Solidarpreis in EUR"))

        solidarity_contribution = SolidarityContribution.objects.filter(
            member=member
        ).first()
        if target_amount == 0:
            if not solidarity_contribution:
                return False

            SolidarityContribution.objects.filter(member=member).delete()
            return True

        target_start_date = DataImportUtils.to_date(row.get("Solidarpreis Start_Date"))
        target_start_date = target_start_date or member.created_at.date()

        target_end_date = DataImportUtils.to_date(row.get("Solidarpreis End_Date"))
        target_end_date = (
            target_end_date
            or TapirCache.get_growing_period_at_date(
                reference_date=target_start_date, cache={}
            ).end_date
        )

        if not solidarity_contribution:
            SolidarityContribution.objects.create(
                member=member,
                amount=target_amount,
                start_date=target_start_date,
                end_date=target_end_date,
            )
            return True

        updated = False
        map_from_attribute_to_value = {
            "amount": target_amount,
            "start_date": target_start_date,
            "end_date": target_end_date,
        }

        for attribute, value in map_from_attribute_to_value.items():
            if DataImportUtils.update_if_diff(
                solidarity_contribution, attribute, value
            ):
                updated = True

        if updated:
            solidarity_contribution.save()

        return updated

    @classmethod
    def create_new_member(
        cls,
        member_no: int,
        row: dict[str, str],
        dry_run: bool,
        stdout: OutputWrapper,
    ):
        member = cls.build_new_member(member_no=member_no, row=row, stdout=stdout)
        cls.update_member_attributes_and_save_member(
            member=member, row=row, dry_run=dry_run
        )

        pickup_location = cls.get_pickup_location_by_name(
            name=DataImportUtils.normalize_cell(row.get("Abholort"))
        )
        if pickup_location:
            HomeDeliveryAddressValidator.validate(
                address_owner=member, pickup_location=pickup_location
            )
            member_pickup_location = MemberPickupLocation(
                member=member,
                pickup_location=pickup_location,
                valid_from=cls.get_pickup_location_valid_from(
                    row=row, current_value=None
                ),
            )
            member_pickup_location.save()

        target_amount = DataImportUtils.safe_float(row.get("Solidarpreis in EUR"))
        if target_amount != 0:
            cls.create_solidarity_contribution(member, row, target_amount)

        cls.update_payment_rhythm_if_necessary(
            member=member,
            reference_date=cls.get_payment_rhythm_reference_date(member=member),
            rhythm_from_import=row.get("Zahlungsintervall", None),
        )

        cls.create_association_membership_if_necessary(member=member, row=row)

        cls.update_preferred_breads(member=member, row=row)

        MemberImportedLogEntry().populate(model=member, actor=None, user=member).save()

        return MEMBER_IMPORT_STATUS_CREATED

    @classmethod
    def build_new_member(
        cls, member_no: int, row: dict[str, str], stdout: OutputWrapper
    ):
        # The TapirUser could already exist, typically if an admin user has been created
        # using the create_admin command. In that case we want to reuse that account.

        tapir_user_without_member = TapirUser.objects.filter(
            email__iexact=cls.build_mail(row=row, member_no=member_no),
            member__isnull=True,
        ).first()
        if tapir_user_without_member is None:
            return Member(member_no=member_no)

        # raw=True inserts only the Member row, the TapirUser row already exists.
        Member(
            tapiruser_ptr=tapir_user_without_member,
            member_no=member_no,
            created_at=get_now(cache={}),
        ).save_base(raw=True)
        member = Member.objects.get(id=tapir_user_without_member.id)

        TextLogEntry().populate(
            text="Beim Import wurde das bestehende Benutzerkonto mit dieser E-Mail-Adresse für das Mitglied übernommen",
            user=member,
            actor=None,
        ).save()
        stdout.write(
            f"Member {member_no}: existing account {member.email} (ID {member.id}) is kept for this member"
        )

        return member

    @classmethod
    def create_association_membership_if_necessary(
        cls, member: Member, row: dict[str, str]
    ):
        membership_type, start_date, end_date = cls.get_association_membership_data(row)
        if membership_type is None:
            return

        membership = AssociationMembership.objects.create(
            member=member,
            type=membership_type,
            start_date=start_date,
            end_date=end_date,
        )
        AssociationMembershipCreatedLogEntry().populate_membership(
            membership=membership,
            actor=None,
        ).save()

    @classmethod
    def get_association_membership_data(cls, row: dict[str, str]):
        membership_type_name = DataImportUtils.normalize_cell(
            row.get("Vereinsmitgliedschafttyp", None)
        )
        if membership_type_name == "":
            return None, None, None

        membership_type = AssociationMembershipType.objects.filter(
            name=membership_type_name
        ).first()
        if membership_type is None:
            raise TapirDataImportException(
                f"Keine Vereinsmitgliedsachttyp mit Name {membership_type_name} gefunden, gültige Namen sind: {", ". join(AssociationMembershipType.objects.values_list("name", flat=True))}"
            )

        start_date = DataImportUtils.to_date(
            row.get("Vereinsmitgliedschaft Start_Date", None)
        )
        if start_date is None:
            raise TapirDataImportException(
                "Keine Start-Datum gefunden für die Vereinsmitgliedschaft"
            )

        end_date = DataImportUtils.to_date(
            row.get("Vereinsmitgliedschaft End_Date", None)
        )
        return membership_type, start_date, end_date

    @classmethod
    def update_association_membership_if_necessary(
        cls, member: Member, row: dict[str, str]
    ):
        membership_type, start_date, end_date = cls.get_association_membership_data(row)

        existing_memberships = AssociationMembership.objects.filter(member=member)
        nb_memberships = existing_memberships.count()
        if membership_type is None:
            if nb_memberships == 0:
                return False

            existing_memberships.delete()
            return True

        if nb_memberships != 1:
            existing_memberships.delete()
            membership = AssociationMembership.objects.create(
                member=member,
                type=membership_type,
                start_date=start_date,
                end_date=end_date,
            )
            AssociationMembershipCreatedLogEntry().populate_membership(
                membership=membership,
                actor=None,
            ).save()
            return True

        membership = existing_memberships.get()
        if (
            membership.type_id == membership_type.id
            and membership.start_date == start_date
            and membership.end_date == end_date
        ):
            return False

        before_changes = freeze_for_log(membership)
        membership.type = membership_type
        membership.start_date = start_date
        membership.end_date = end_date
        membership.save()
        AssociationMembershipUpdatedLogEntry().populate(
            old_frozen=before_changes, new_model=membership, actor=None, user=member
        ).save()
        return True

    @classmethod
    def create_solidarity_contribution(
        cls, member: Member, row: dict[str, str], target_amount: float
    ):
        target_start_date = DataImportUtils.to_date(row.get("Solidarpreis Start_Date"))
        target_start_date = target_start_date or member.created_at.date()

        target_end_date = DataImportUtils.to_date(row.get("Solidarpreis End_Date"))
        target_end_date = (
            target_end_date
            or TapirCache.get_growing_period_at_date(
                reference_date=target_start_date, cache={}
            ).end_date
        )

        SolidarityContribution.objects.create(
            member=member,
            amount=target_amount,
            start_date=target_start_date,
            end_date=target_end_date,
        )

    @classmethod
    def update_preferred_breads(cls, member: Member, row: dict[str, str]):
        row_value = row.get("Lieblingsbrote", None)
        if row_value is None:
            return False
        preferred_bread_names = DataImportUtils.normalize_cell(row_value).split(",")

        new_preferred_breads = set()
        for raw_bread_name in preferred_bread_names:
            bread_name = raw_bread_name.strip()
            if bread_name == "":
                continue

            bread = Bread.objects.filter(name__iexact=bread_name.strip()).first()
            if bread is None:
                raise TapirDataImportException(
                    f"Brot mit Name {bread_name.strip()} existiert nicht"
                )

            new_preferred_breads.add(bread)

        preferred_bread_object, _ = PreferredBread.objects.get_or_create(
            member_id=member.id
        )
        if set(preferred_bread_object.breads.all()) == new_preferred_breads:
            return False

        preferred_bread_object.breads.set(new_preferred_breads)
        return True
