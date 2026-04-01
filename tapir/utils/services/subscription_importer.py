import datetime

from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.subscriptions.services.notice_period_manager import NoticePeriodManager
from tapir.utils.config import (
    MEMBER_IMPORT_STATUS_SKIPPED,
    MEMBER_IMPORT_STATUS_CREATED,
    MEMBER_IMPORT_STATUS_UPDATED,
)
from tapir.utils.exceptions import TapirDataImportException
from tapir.utils.services.data_import_utils import DataImportUtils
from tapir.wirgarten.constants import NO_DELIVERY
from tapir.wirgarten.models import Member, GrowingPeriod, Product, Subscription
from tapir.wirgarten.service.member import get_or_create_mandate_ref
from tapir.wirgarten.utils import get_today


class SubscriptionImporter:
    @classmethod
    def import_subscription(cls, row: dict[str, str], update_existing: bool):
        # VertragNr,Zeitstempel,E-Mail-Adresse,Tapir-ID,Mitgliedernummer,Probevertrag,Vertragsbeginn,[S-Ernteanteil],[M-Ernteanteil],[L-Ernteanteil],[XL-Ernteanteil],product,Quantity,"Gesamtzahlung",Vertragsgrundsätze,Abholort,Email-Adressen,Ernteanteilsreduzierung/erhöhung,consent_widerruf,consent_vertragsgrundsätze,cancellation.ts

        member_no = DataImportUtils.safe_int(row.get("Mitgliedernummer"), default=-1)
        email = DataImportUtils.normalize_cell(row.get("Email"))
        member = cls.get_member_by_number_or_email(member_no=member_no, email=email)

        start_date = DataImportUtils.to_date(row.get("Vertragsbeginn"))
        if not start_date:
            raise TapirDataImportException(
                f"No start_date (Vertragsbeginn) found, cell value: {row.get('Vertragsbeginn')}"
            )

        growing_period = GrowingPeriod.objects.filter(
            start_date__lte=start_date, end_date__gte=start_date
        ).first()

        if not growing_period:
            raise TapirDataImportException(
                f"No growing period (=Vertragsperiode) found that contains the given contract start date ({start_date}) for member number {member_no}"
            )

        mandate_ref = get_or_create_mandate_ref(member)

        product_name = DataImportUtils.normalize_cell(row.get("product"))
        product_type_name = DataImportUtils.normalize_cell(row.get("product_type"))
        product = cls.get_product_by_name(
            product_name=product_name, product_type_name=product_type_name
        )

        if product.type.delivery_cycle != NO_DELIVERY[0] and (
            MemberPickupLocationGetter.get_member_pickup_location_id(
                member=member, reference_date=max(start_date, get_today())
            )
            is None
        ):
            raise TapirDataImportException(
                f"Member {member} should get a subscription for {product} but they don't have a pickup location"
            )

        cancellation_ts = DataImportUtils.to_datetime(row.get("cancellation.ts"))

        trial_period_is_enabled = DataImportUtils.safe_bool(row.get("Probezeit"))
        trial_end_date_override = DataImportUtils.to_date(
            row.get("Ende Probezeit (Sonntag)")
        )

        quantity = DataImportUtils.safe_int(row.get("Quantity"))
        start_date = DataImportUtils.to_date(row.get("Vertragsbeginn"))
        end_date = DataImportUtils.to_date(row.get("Vertragsende"))
        if end_date is None:
            # we must explicitly check for end date because the end_date field accepts None and
            # DataImportUtils.to_date can return None if for example the column doesn't exist.
            raise TapirDataImportException("Missing end date")
        consent_ts = DataImportUtils.to_datetime(row.get("consent_vertragsgrundsätze"))
        withdrawal_consent_ts = DataImportUtils.to_datetime(row.get("consent_widerruf"))

        subscription = Subscription.objects.filter(
            member=member, product=product, start_date=start_date
        ).first()

        if subscription:
            if not update_existing:
                return MEMBER_IMPORT_STATUS_SKIPPED

            import_status = cls.updated_existing_subscription(
                cancellation_ts=cancellation_ts,
                consent_ts=consent_ts,
                end_date=end_date,
                existing_subscription=subscription,
                quantity=quantity,
                trial_end_date_override=trial_end_date_override,
                trial_period_is_enabled=trial_period_is_enabled,
                withdrawal_consent_ts=withdrawal_consent_ts,
            )
        else:
            subscription = Subscription.objects.create(
                member=member,
                quantity=quantity,
                start_date=start_date,
                end_date=end_date,
                cancellation_ts=cancellation_ts,
                mandate_ref=mandate_ref,
                period=growing_period,
                product=product,
                consent_ts=consent_ts,
                withdrawal_consent_ts=withdrawal_consent_ts,
                trial_disabled=(
                    not trial_period_is_enabled
                    if trial_period_is_enabled is not None
                    else False
                ),
                trial_end_date_override=trial_end_date_override,
                notice_period_duration=NoticePeriodManager.get_notice_period_duration(
                    product_type=product.type,
                    growing_period=growing_period,
                    cache={},
                ),
                notice_period_unit=NoticePeriodManager.get_notice_period_unit(
                    product_type=product.type,
                    growing_period=growing_period,
                    cache={},
                ),
            )

            import_status = MEMBER_IMPORT_STATUS_CREATED

        cls.update_trial_period_for_solidarity_contributions(member, subscription)
        return import_status

    @classmethod
    def updated_existing_subscription(
        cls,
        cancellation_ts: datetime.datetime | None,
        consent_ts: datetime.datetime | None,
        end_date: datetime.date | None,
        existing_subscription: Subscription,
        quantity: int,
        trial_end_date_override: datetime.date | None,
        trial_period_is_enabled: bool | None,
        withdrawal_consent_ts: datetime.datetime | None,
    ) -> str:
        is_updated = False

        map_from_attribute_to_value = {
            "quantity": quantity,
            "end_date": end_date,
            "cancellation_ts": cancellation_ts,
            "consent_ts": consent_ts,
            "withdrawal_consent_ts": withdrawal_consent_ts,
            "trial_end_date_override": trial_end_date_override,
        }

        for attribute, value in map_from_attribute_to_value.items():
            if DataImportUtils.update_if_diff(existing_subscription, attribute, value):
                is_updated = True

        if trial_period_is_enabled is not None and DataImportUtils.update_if_diff(
            existing_subscription,
            "trial_disabled",
            not trial_period_is_enabled,
        ):
            is_updated = True

        if not is_updated:
            return MEMBER_IMPORT_STATUS_SKIPPED

        try:
            existing_subscription.save()
            return MEMBER_IMPORT_STATUS_UPDATED
        except Exception as e:
            raise TapirDataImportException(f"Error updating subscription: {e}")

    @staticmethod
    def get_member_by_number_or_email(member_no: int, email: str):
        if member_no != -1:
            member = Member.objects.filter(member_no=member_no).first()
            if member:
                return member

        if email != "":
            member = Member.objects.filter(email=email).first()
            if member:
                return member

        raise TapirDataImportException(
            f"Could not find member with number '{member_no}' or email '{email}'"
        )

    @staticmethod
    def get_product_by_name(product_name: str, product_type_name: str):
        if not product_type_name:
            products = Product.objects.filter(name=product_name)
            if products.count() > 1:
                raise TapirDataImportException(
                    f"Multiple product exist with the name '{product_name}', you must specify the product type name too (column product_type)"
                )
            if products.count() == 0:
                raise TapirDataImportException(
                    f"No product found with the name '{product_name}' (product type name not specified)"
                )
            return products.get()

        return Product.objects.get(name=product_name, type__name=product_type_name)

    @classmethod
    def update_trial_period_for_solidarity_contributions(
        cls, member: Member, subscription: Subscription
    ):
        contributions = SolidarityContribution.objects.filter(member=member)
        if not contributions.exists():
            return

        if subscription.trial_disabled:
            contributions.update(trial_disabled=True)

        if subscription.trial_end_date_override:
            contributions.update(
                trial_end_date_override=subscription.trial_end_date_override
            )
