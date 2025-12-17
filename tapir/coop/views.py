from django.core.exceptions import BadRequest
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.urls import reverse
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from rest_framework import status, viewsets, permissions, serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.accounts.models import EmailChangeRequest
from tapir.coop.serializers import (
    MinimumNumberOfSharesResponseSerializer,
    GetCoopShareTransactionsResponseSerializer,
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
from tapir.deliveries.models import Joker
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.log.models import LogEntry
from tapir.subscriptions.serializers import (
    MemberSerializer,
)
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.utils.services.tapir_cache import TapirCache
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
from tapir.wirgarten.utils import check_permission_or_self, get_today, get_now


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
        responses={200: str},
        request=inline_serializer(
            name="existing_member_purchases_extra_shares_serializer",
            fields={
                "member_id": serializers.CharField(),
                "number_of_shares_to_add": serializers.IntegerField(),
                "iban": serializers.CharField(allow_null=True),
                "account_owner": serializers.CharField(allow_null=True),
            },
        ),
    )
    def post(self, request):
        member_id = request.data.get("member_id")
        member = get_object_or_404(Member, id=member_id)
        check_permission_or_self(pk=member_id, request=request)

        number_of_shares_to_add = int(request.data.get("number_of_shares_to_add"))
        if number_of_shares_to_add <= 0:
            raise ValidationError("Number of coop shares must be positive")

        if not member.is_student:
            self.validate_number_of_shares(
                number_of_shares_to_add=number_of_shares_to_add,
                cache=self.cache,
                member=member,
            )

        if MembershipCancellationManager.is_in_coop_trial(member):
            raise ValidationError(
                "Du kannst weitere Genossenschaftsanteile erst zeichnen, wenn du formal Mitglied der Genossenschaft geworden bist."
            )

        needs_banking_data = (
            MemberNeedsBankingDataChecker.does_member_need_banking_data(member)
        )
        iban = request.data.get("iban", None)
        account_owner = request.data.get("account_owner", None)
        if needs_banking_data and (iban is None or account_owner is None):
            raise ValidationError("Dieses Mitglied braucht noch Bank-Daten (IBAN usw.)")

        with transaction.atomic():
            CoopSharePurchaseHandler.buy_cooperative_shares(
                quantity=number_of_shares_to_add,
                member=member,
                shares_valid_at=ContractStartDateCalculator.get_next_contract_start_date(
                    reference_date=get_today(cache=self.cache),
                    apply_buffer_time=True,
                    cache=self.cache,
                ),
                cache=self.cache,
                actor=request.user,
            )
            if needs_banking_data:
                member.iban = iban
                member.account_owner = account_owner
                member.sepa_consent = get_now(cache=self.cache)
                member.save()

        return Response(member.get_absolute_url())

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
            raise ValidationError(
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

            member.delete()

        return Response("deleted")
