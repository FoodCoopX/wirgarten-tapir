from django.core.exceptions import BadRequest
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.urls import reverse
from drf_spectacular.utils import extend_schema, OpenApiParameter
from localflavor.generic.validators import IBANValidator
from rest_framework import status, viewsets, permissions
from rest_framework.exceptions import (
    ValidationError as DrfValidationError,
    PermissionDenied,
)
from rest_framework.response import Response
from rest_framework.views import APIView
from tapir_mail.models import EmailConfigurationDispatch
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.accounts.models import EmailChangeRequest, UpdateTapirUserLogEntry
from tapir.configuration.parameter import get_parameter_value
from tapir.coop.serializers import (
    MinimumNumberOfSharesResponseSerializer,
    GetCoopShareTransactionsResponseSerializer,
    ExistingMemberPurchasesSharesRequestSerializer,
    UpdateMemberBankDataRequestSerializer,
    MemberBankDataResponseSerializer,
    MemberProfilePersonalDataResponseSerializer,
    MemberProfilePersonalDataRequestSerializer,
)
from tapir.coop.services.coop_share_purchase_handler import CoopSharePurchaseHandler
from tapir.coop.services.member_needs_banking_data_checker import (
    MemberNeedsBankingDataChecker,
)
from tapir.coop.services.membership_cancellation_manager import (
    MembershipCancellationManager,
)
from tapir.coop.services.minimum_number_of_shares_validator import (
    MinimumNumberOfSharesValidator,
)
from tapir.coop.services.personal_data_validator import PersonalDataValidator
from tapir.deliveries.models import Joker
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.log.models import LogEntry
from tapir.log.util import freeze_for_log
from tapir.subscriptions.serializers import (
    MemberSerializer,
    OrderConfirmationResponseSerializer,
)
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import (
    Member,
    CoopShareTransaction,
    TransferCoopSharesLogEntry,
    Payment,
    MemberPickupLocation,
    Subscription,
    Deliveries,
    WaitingListEntry,
    QuestionaireTrafficSourceResponse,
    QuestionaireCancellationReasonResponse,
    MandateReference,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import (
    check_permission_or_self,
    get_today,
    get_now,
    legal_status_is_cooperative,
)


class MinimumNumberOfSharesApiView(APIView):
    permission_classes = []

    @extend_schema(
        responses={200: MinimumNumberOfSharesResponseSerializer},
        parameters=[
            OpenApiParameter(name="product_ids", type=str, many=True),
            OpenApiParameter(name="quantities", type=int, many=True),
        ],
    )
    def get(self, request):
        product_ids = request.query_params.getlist("product_ids")
        quantities = request.query_params.getlist("quantities")
        cache = {}

        if len(product_ids) != len(quantities):
            raise BadRequest("Different number of product ids and quantities")

        ordered_products_id_to_quantity_map = {
            product_id: int(quantities[index] or 0)
            for index, product_id in enumerate(product_ids)
            if product_id != ""
        }

        minimum_number_of_shares = (
            MinimumNumberOfSharesValidator.get_minimum_number_of_shares_for_order(
                ordered_products_id_to_quantity_map, cache=cache
            )
        )

        return Response(
            MinimumNumberOfSharesResponseSerializer(
                {
                    "minimum_number_of_shares": minimum_number_of_shares,
                }
            ).data,
            status=status.HTTP_200_OK,
        )


class ExistingMemberPurchasesSharesApiView(APIView):
    def __init__(self):
        super().__init__()
        self.cache = {}

    @extend_schema(
        responses={200: OrderConfirmationResponseSerializer},
        request=ExistingMemberPurchasesSharesRequestSerializer,
    )
    def post(self, request):
        serializer = ExistingMemberPurchasesSharesRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        member_id = serializer.validated_data["member_id"]
        member = get_object_or_404(Member, id=member_id)
        check_permission_or_self(pk=member_id, request=request)

        as_admin = serializer.validated_data["as_admin"]
        if serializer.validated_data["as_admin"] and not request.user.has_perm(
            Permission.Coop.MANAGE
        ):
            raise PermissionDenied("Du hast hast die nötige Berechtigung nicht.")

        iban = serializer.validated_data.get("iban", None)
        account_owner = serializer.validated_data.get("account_owner", None)
        number_of_shares_to_add = serializer.validated_data["number_of_shares_to_add"]
        needs_banking_data = (
            MemberNeedsBankingDataChecker.does_member_need_banking_data(member)
        )

        try:
            self.validate_everything(
                as_admin=as_admin,
                account_owner=account_owner,
                iban=iban,
                member=member,
                needs_banking_data=needs_banking_data,
                number_of_shares_to_add=number_of_shares_to_add,
            )
        except DjangoValidationError as error:
            data = {
                "order_confirmed": False,
                "error": error.message,
            }
            return Response(OrderConfirmationResponseSerializer(data).data)

        if as_admin:
            shares_valid_at = serializer.validated_data["start_date"]
        else:
            shares_valid_at = ContractStartDateCalculator.get_next_contract_start_date(
                reference_date=get_today(cache=self.cache),
                apply_buffer_time=True,
                cache=self.cache,
            )

        with transaction.atomic():
            CoopSharePurchaseHandler.buy_cooperative_shares(
                quantity=number_of_shares_to_add,
                member=member,
                shares_valid_at=shares_valid_at,
                cache=self.cache,
                actor=request.user,
            )
            if needs_banking_data:
                member.iban = iban
                member.account_owner = account_owner
                member.sepa_consent = get_now(cache=self.cache)
                member.save()

        data = {
            "order_confirmed": True,
            "error": None,
            "redirect_url": member.get_absolute_url(),
        }
        return Response(OrderConfirmationResponseSerializer(data).data)

    def validate_everything(
        self,
        as_admin: bool,
        account_owner: str | None,
        iban: str | None,
        member: Member,
        needs_banking_data: bool,
        number_of_shares_to_add: int,
    ):

        if number_of_shares_to_add <= 0:
            raise DjangoValidationError("Number of coop shares must be positive")

        if not member.is_student and not as_admin:
            self.validate_number_of_shares(
                number_of_shares_to_add=number_of_shares_to_add,
                cache=self.cache,
                member=member,
            )

        if MembershipCancellationManager.is_in_coop_trial(member) and not as_admin:
            raise DjangoValidationError(
                "Du kannst weitere Genossenschaftsanteile erst zeichnen, wenn du formal Mitglied der Genossenschaft geworden bist."
            )

        if needs_banking_data and (not iban or not account_owner):
            raise DjangoValidationError(
                "Dieses Mitglied braucht noch Bank-Daten (IBAN usw.)"
            )

    @classmethod
    def validate_number_of_shares(
        cls, number_of_shares_to_add: int, cache: dict, member: Member
    ):
        ordered_products_id_to_quantity_map = {}
        for subscription in TapirCache.get_active_and_future_subscriptions_by_member_id(
            cache=cache, reference_date=get_today(cache=cache)
        ).get(member.id, []):
            ordered_products_id_to_quantity_map[subscription.product_id] = (
                subscription.quantity
            )

        total_min_shares = (
            MinimumNumberOfSharesValidator.get_minimum_number_of_shares_for_order(
                ordered_products_id_to_quantity_map=ordered_products_id_to_quantity_map,
                cache=cache,
            )
        )

        current_shares = sum(
            [
                share_transaction.quantity
                for share_transaction in CoopShareTransaction.objects.filter(
                    member=member
                )
            ]
        )

        if current_shares + number_of_shares_to_add < total_min_shares:
            raise DjangoValidationError(
                f"The minimum final number of shares is {total_min_shares}, "
                f"this member currently has {current_shares}, adding {number_of_shares_to_add} is not enough."
            )


class GetCoopShareTransactionsApiView(APIView):
    def __init__(self):
        super().__init__()
        self.cache = {}

    @extend_schema(
        responses={200: GetCoopShareTransactionsResponseSerializer()},
        parameters=[
            OpenApiParameter(name="member_id", type=str, required=True),
        ],
    )
    def get(self, request):
        member_id = request.query_params.get("member_id")
        check_permission_or_self(pk=member_id, request=request)
        member = get_object_or_404(Member, id=member_id)

        data = {
            "transactions": CoopShareTransaction.objects.filter(member=member).order_by(
                "valid_at"
            ),
            "url_of_bestell_wizard": reverse(
                "bestell_wizard:bestell_wizard_coop_shares", args=[member_id]
            ),
        }

        return Response(GetCoopShareTransactionsResponseSerializer(data).data)


class MemberViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]
    queryset = Member.objects.all()
    serializer_class = MemberSerializer


class DeleteMemberApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        responses={200: str},
        parameters=[OpenApiParameter(name="member_id", type=str)],
    )
    def delete(self, request):
        member_id = request.query_params.get("member_id")
        member = get_object_or_404(Member, id=member_id)

        with transaction.atomic():
            EmailChangeRequest.objects.filter(user=member).delete()
            LogEntry.objects.filter(actor=member).delete()
            LogEntry.objects.filter(user=member).delete()
            TransferCoopSharesLogEntry.objects.filter(target_member=member).delete()
            Payment.objects.filter(mandate_ref__member=member).delete()
            models = [
                Joker,
                MemberPickupLocation,
                Subscription,
                CoopShareTransaction,
                Deliveries,
                WaitingListEntry,
                QuestionaireTrafficSourceResponse,
                QuestionaireCancellationReasonResponse,
                MandateReference,
            ]
            for model in models:
                model.objects.filter(member=member).delete()
            EmailConfigurationDispatch.objects.filter(
                is_sent=False,
                override_recipients__0__recipient_id_in_base_queryset=member.id,
            ).delete()

            member.delete()

        return Response("deleted")


class MemberBankDataApiView(APIView):
    @extend_schema(
        parameters=[OpenApiParameter(name="member_id", type=str)],
        responses={200: MemberBankDataResponseSerializer},
    )
    def get(self, request):
        member_id = request.query_params.get("member_id")
        check_permission_or_self(pk=member_id, request=request)
        member = get_object_or_404(Member, id=member_id)

        return Response(
            MemberBankDataResponseSerializer(
                {
                    "iban": member.iban,
                    "account_owner": member.account_owner,
                    "organisation_name": get_parameter_value(
                        ParameterKeys.SITE_NAME, cache={}
                    ),
                }
            ).data
        )

    @extend_schema(
        responses={200: bool},
        request=UpdateMemberBankDataRequestSerializer,
    )
    def patch(self, request):
        serializer = UpdateMemberBankDataRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        member_id = serializer.validated_data["member_id"]
        check_permission_or_self(pk=member_id, request=request)
        member = get_object_or_404(Member, id=member_id)

        iban = serializer.validated_data["iban"]
        sepa_consent = serializer.validated_data["sepa_consent"]
        self.validate(iban=iban, sepa_consent=sepa_consent)

        member_before = freeze_for_log(member)

        member.account_owner = serializer.validated_data["account_owner"]
        member.iban = iban
        member.sepa_consent = get_now(cache={})

        with transaction.atomic():
            UpdateTapirUserLogEntry().populate(
                old_frozen=member_before,
                new_model=member,
                user=member,
                actor=request.user,
            ).save()

            TransactionalTrigger.fire_action(
                trigger_data=TransactionalTriggerData(
                    key=Events.MEMBERAREA_CHANGE_DATA,
                    recipient_id_in_base_queryset=member.id,
                ),
            )

            member.save()

        return Response(True)

    @staticmethod
    def validate(iban: str, sepa_consent: bool):
        IBANValidator()(iban)

        if not sepa_consent:
            raise DrfValidationError("Zustimmung für SEPA fehlt")


class MemberPersonalDataApiView(APIView):
    def __init__(self, **kwargs):
        self.cache = {}
        super().__init__(**kwargs)

    @extend_schema(
        parameters=[OpenApiParameter(name="member_id", type=str)],
        responses={200: MemberProfilePersonalDataResponseSerializer},
    )
    def get(self, request):
        member_id = request.query_params.get("member_id")
        check_permission_or_self(pk=member_id, request=request)
        member = get_object_or_404(Member, id=member_id)

        is_student = None
        if legal_status_is_cooperative(cache=self.cache) and get_parameter_value(
            key=ParameterKeys.ALLOW_STUDENT_TO_ORDER_WITHOUT_COOP_SHARES,
            cache=self.cache,
        ):
            is_student = member.is_student

        return Response(
            MemberProfilePersonalDataResponseSerializer(
                {
                    "member_id": member.id,
                    "first_name": member.first_name,
                    "last_name": member.last_name,
                    "email": member.email,
                    "phone_number": member.phone_number,
                    "street": member.street,
                    "street_2": member.street_2,
                    "postcode": member.postcode,
                    "city": member.city,
                    "is_student": is_student,
                    "can_edit_student": self.user_can_edit_student_status(request.user),
                }
            ).data
        )

    @classmethod
    def user_can_edit_student_status(cls, user):
        return user.has_perm(Permission.Coop.MANAGE)

    @extend_schema(
        responses={200: OrderConfirmationResponseSerializer},
        request=MemberProfilePersonalDataRequestSerializer,
    )
    def patch(self, request):
        serializer = MemberProfilePersonalDataRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        member_id = serializer.validated_data["member_id"]
        check_permission_or_self(pk=member_id, request=request)
        member = get_object_or_404(Member, id=member_id)

        member_before = freeze_for_log(member)
        student_status_enabled = legal_status_is_cooperative(
            cache=self.cache
        ) and get_parameter_value(
            key=ParameterKeys.ALLOW_STUDENT_TO_ORDER_WITHOUT_COOP_SHARES,
            cache=self.cache,
        )

        try:
            PersonalDataValidator.validate_phone_number_is_valid(
                serializer.validated_data.get("phone_number")
            )
            if serializer.validated_data["email"] != member.email:
                PersonalDataValidator.validate_email_address_not_in_use(
                    email=serializer.validated_data["email"],
                    check_waiting_list=True,
                    cache=self.cache,
                )
            if (
                student_status_enabled
                and serializer.validated_data["is_student"] != member.is_student
                and not self.user_can_edit_student_status(request.user)
            ):
                raise DjangoValidationError(
                    "Nur Admins dürfen den Studenten-Status ändern."
                )
        except DjangoValidationError as error:
            return Response(
                OrderConfirmationResponseSerializer(
                    {"order_confirmed": False, "error": error.message}
                ).data
            )

        simple_fields = [
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "street",
            "street_2",
            "postcode",
            "city",
        ]
        for field in simple_fields:
            setattr(member, field, serializer.validated_data.get(field))

        if student_status_enabled:
            member.is_student = serializer.validated_data["is_student"]

        with transaction.atomic():
            UpdateTapirUserLogEntry().populate(
                old_frozen=member_before,
                new_model=member,
                user=member,
                actor=request.user,
            ).save()

            TransactionalTrigger.fire_action(
                TransactionalTriggerData(
                    key=Events.MEMBERAREA_CHANGE_DATA,
                    recipient_id_in_base_queryset=member.id,
                ),
            )

            member.save()

        return Response(
            OrderConfirmationResponseSerializer(
                {"order_confirmed": True, "error": None}
            ).data
        )
