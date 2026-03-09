from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.utils.config import (
    MEMBER_IMPORT_STATUS_UPDATED,
    MEMBER_IMPORT_STATUS_SKIPPED,
    MEMBER_IMPORT_STATUS_CREATED,
)
from tapir.utils.exceptions import TapirDataImportException
from tapir.utils.services.data_import_utils import DataImportUtils
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import (
    PickupLocation,
    Member,
    MemberPickupLocation,
)


class MemberImporter:
    @classmethod
    def import_member(cls, row: dict[str, str], update_existing: bool):
        if DataImportUtils.is_row_empty(row):
            return None

        member_no = int(DataImportUtils.normalize_cell(row.get("Nr")))
        member = Member.objects.filter(member_no=member_no).first()

        if member:
            if not update_existing:
                return MEMBER_IMPORT_STATUS_SKIPPED

            try:
                return cls.update_existing_member_if_necessary(member=member, row=row)
            except Exception as e:
                raise TapirDataImportException(
                    f"Error updating member {member_no}: {e}"
                )

        try:
            return cls.create_new_member(member_no=member_no, row=row)
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
    def update_existing_member_if_necessary(cls, member: Member, row: dict[str, str]):
        member_attributes_updated = cls.update_member_attributes(member=member, row=row)
        pickup_location_updated = cls.update_member_pickup_location(
            member=member, row=row
        )
        solidarity_updated = cls.update_solidarity_contribution(member=member, row=row)

        if member_attributes_updated or pickup_location_updated or solidarity_updated:
            return MEMBER_IMPORT_STATUS_UPDATED
        return MEMBER_IMPORT_STATUS_SKIPPED

    @classmethod
    def update_member_attributes(cls, member: Member, row: dict[str, str]):
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
            "consent_sepa": "sepa_consent",
            "privacy_consent": "privacy_consent",
        }

        map_from_row_header_to_converter = {
            "Geburtstag/Gründungsdatum": DataImportUtils.to_date,
            "consent_sepa": DataImportUtils.to_datetime,
            "privacy_consent": DataImportUtils.to_datetime,
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

        target_mail = cls.build_mail(row=row, member_no=member.member_no)
        if DataImportUtils.update_if_diff(
            member,
            "email",
            target_mail,
        ):
            member_updated = True

        if email_before != member.email and member.keycloak_id:
            Member.objects.filter(id=member.id).update(email=member.email)
            KeycloakUserManager.get_keycloak_client(cache={}).update_user(
                user_id=member.keycloak_id, payload={"email": member.email}
            )

        if member_updated:
            member.save(bypass_keycloak=True)

        return member_updated

    @classmethod
    def build_mail(cls, row: dict[str, str], member_no: int):
        target_mail = DataImportUtils.normalize_cell(row.get("Mailadresse"))
        if target_mail == "":
            return f"team+missing_mail_katringer_{member_no}@foodcoopx.de"

        number_of_duplicate_mails = (
            Member.objects.exclude(member_no=member_no)
            .filter(email=target_mail)
            .count()
        )
        if number_of_duplicate_mails == 0:
            return target_mail

        prefix, suffix = target_mail.split("@", maxsplit=1)
        return f"{prefix}+{number_of_duplicate_mails}@{suffix}"

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

        if member_pickup_location is None:
            MemberPickupLocation.objects.create(
                member=member,
                pickup_location=target_pickup_location,
                valid_from=DataImportUtils.to_date(row.get("AO_gueltig_ab")),
            )
            return True

        updated = DataImportUtils.update_if_diff(
            member_pickup_location, "pickup_location", target_pickup_location
        ) or DataImportUtils.update_if_diff(
            member_pickup_location,
            "valid_from",
            DataImportUtils.to_date(row.get("AO_gueltig_ab")),
        )

        if updated:
            member_pickup_location.save()

        return updated

    @classmethod
    def update_solidarity_contribution(cls, member: Member, row: dict[str, str]):
        target_amount = DataImportUtils.safe_float(row.get("Solidarpreis in EUR"))

        target_start_date = DataImportUtils.to_date(row.get("Solidarpreis Start_Date"))
        target_start_date = target_start_date or member.created_at.date()

        target_end_date = DataImportUtils.to_date(row.get("Solidarpreis End_Date"))
        target_end_date = (
            target_end_date
            or TapirCache.get_growing_period_at_date(
                reference_date=target_start_date, cache={}
            ).end_date
        )

        solidarity_contribution = SolidarityContribution.objects.filter(
            member=member
        ).first()
        if target_amount == 0:
            if not solidarity_contribution:
                return False

            SolidarityContribution.objects.filter(member=member).delete()
            return True

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
    def create_new_member(cls, member_no: int, row: dict[str, str]):
        member = Member(
            member_no=member_no,
        )
        cls.update_member_attributes(member=member, row=row)
        member.save()

        pickup_location = cls.get_pickup_location_by_name(
            name=DataImportUtils.normalize_cell(row.get("Abholort"))
        )
        if pickup_location:
            member_pickup_location = MemberPickupLocation(
                member=member,
                pickup_location=pickup_location,
                valid_from=DataImportUtils.to_date(row.get("AO_gueltig_ab")),
            )
            member_pickup_location.save()

        target_amount = DataImportUtils.safe_float(row.get("Solidarpreis in EUR"))

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

        return MEMBER_IMPORT_STATUS_CREATED
