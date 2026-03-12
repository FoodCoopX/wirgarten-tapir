from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.accounts.models import TapirUser
from tapir.configuration.parameter import get_parameter_value
from tapir.coop.services.membership_cancellation_manager import (
    MembershipCancellationManager,
)
from tapir.solidarity_contribution.services.member_solidarity_contribution_service import (
    MemberSolidarityContributionService,
)
from tapir.subscriptions.serializers import (
    CancellationDataSerializer,
    CancelSubscriptionsViewResponseSerializer,
    CancelSubscriptionsRequestSerializer,
)
from tapir.subscriptions.services.base_product_type_service import (
    BaseProductTypeService,
)
from tapir.subscriptions.services.subscription_cancellation_manager import (
    SubscriptionCancellationManager,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import (
    Member,
    Product,
    SubscriptionChangeLogEntry,
    QuestionaireCancellationReasonResponse,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import (
    get_active_and_future_subscriptions,
)
from tapir.wirgarten.utils import (
    check_permission_or_self,
    format_date,
    format_subscription_list_html,
    get_now,
    get_today,
)


class GetCancellationDataView(APIView):
    @extend_schema(
        responses={200: CancellationDataSerializer()},
        parameters=[
            OpenApiParameter(name="member_id", type=str),
        ],
    )
    def get(self, request):
        member = get_object_or_404(Member, id=request.query_params.get("member_id"))
        check_permission_or_self(member.id, request)

        cache = {}
        data = {
            "can_cancel_coop_membership": MembershipCancellationManager.can_member_cancel_coop_membership(
                member, cache=cache
            ),
            "subscribed_products": self.build_subscribed_products_data(
                member, cache=cache
            ),
            "legal_status": get_parameter_value(
                ParameterKeys.ORGANISATION_LEGAL_STATUS, cache=cache
            ),
            "default_cancellation_reasons": [
                reason.strip()
                for reason in get_parameter_value(
                    ParameterKeys.MEMBER_CANCELLATION_REASON_CHOICES, cache=cache
                ).split(";")
            ],
            "solidarity_contribution_data": self.build_solidarity_contribution_data(
                member, cache=cache
            ),
        }

        return Response(
            CancellationDataSerializer(data).data,
            status=status.HTTP_200_OK,
        )

    @classmethod
    def build_solidarity_contribution_data(cls, member: Member, cache: dict):
        contributions = SubscriptionCancellationManager.get_solidarity_contributions_that_could_be_cancelled(
            member=member, cache=cache
        )
        today = get_today(cache=cache)

        if not contributions.exists():
            return {
                "exists": False,
                "is_in_trial": False,
                "cancellation_date": today,
            }

        return {
            "exists": True,
            "is_in_trial": any(
                TrialPeriodManager.is_contract_in_trial(
                    contract=contribution, reference_date=today, cache=cache
                )
                for contribution in contributions
            ),
            "cancellation_date": SubscriptionCancellationManager.get_earliest_possible_cancellation_date_for_solidarity_contribution(
                member=member, cache=cache
            ),
        }

    @classmethod
    def build_subscribed_products_data(cls, member: Member, cache: dict):
        return [
            {
                "product": subscribed_product,
                "is_in_trial": TrialPeriodManager.is_product_in_trial(
                    subscribed_product, member, cache=cache
                ),
                "cancellation_date": SubscriptionCancellationManager.get_earliest_possible_cancellation_date_for_product(
                    product=subscribed_product, member=member, cache=cache
                ),
            }
            for subscribed_product in cls.get_subscribed_products(member, cache=cache)
        ]

    @classmethod
    def get_subscribed_products(cls, member: Member, cache: dict):
        return {
            subscription.product
            for subscription in get_active_and_future_subscriptions(cache=cache).filter(
                member=member, cancellation_ts__isnull=True
            )
        }


class CancelSubscriptionsView(APIView):
    def __init__(self):
        super().__init__()
        self.cache = {}

    @extend_schema(
        responses={200: CancelSubscriptionsViewResponseSerializer()},
        request=CancelSubscriptionsRequestSerializer,
    )
    def post(self, request):
        serializer = CancelSubscriptionsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        member = get_object_or_404(Member, id=serializer.validated_data["member_id"])
        check_permission_or_self(member.id, request)

        product_ids = serializer.validated_data.get("product_ids", [])
        products_selected_for_cancellation = {
            get_object_or_404(Product, id=product_id)
            for product_id in product_ids
            if product_id != ""
        }

        cancel_coop_membership = serializer.validated_data["cancel_coop_membership"]
        cancellation_reasons = serializer.validated_data.get("cancellation_reasons", [])
        custom_cancellation_reason = serializer.validated_data.get(
            "custom_cancellation_reason", None
        )
        cancel_solidarity_contribution = serializer.validated_data.get(
            "cancel_solidarity_contribution", []
        )

        try:
            self.validate_everything(
                cancel_coop_membership=cancel_coop_membership,
                member=member,
                products_selected_for_cancellation=products_selected_for_cancellation,
                cancellation_reasons=cancellation_reasons,
                custom_cancellation_reason=custom_cancellation_reason,
                cancel_solidarity_contribution=cancel_solidarity_contribution,
            )
        except ValidationError as e:
            return self.build_response(
                subscriptions_cancelled=False, errors=[e.message]
            )

        self.apply_changes(
            cancel_coop_membership=cancel_coop_membership,
            member=member,
            products_selected_for_cancellation=products_selected_for_cancellation,
            actor=request.user,
            cancellation_reasons=cancellation_reasons,
            custom_cancellation_reason=custom_cancellation_reason,
            cancel_solidarity_contribution=cancel_solidarity_contribution,
        )

        return self.build_response(subscriptions_cancelled=True, errors=[])

    @transaction.atomic
    def apply_changes(
        self,
        cancel_coop_membership,
        member,
        products_selected_for_cancellation,
        actor: TapirUser,
        cancellation_reasons: list[str],
        custom_cancellation_reason: str | None,
        cancel_solidarity_contribution: bool,
    ):
        all_cancelled_subscriptions = []
        all_deleted_subscriptions = []
        for product in products_selected_for_cancellation:
            cancelled_subscriptions, deleted_subscriptions = (
                SubscriptionCancellationManager.cancel_subscriptions(
                    product, member, cache=self.cache
                )
            )
            all_cancelled_subscriptions.extend(cancelled_subscriptions)
            all_deleted_subscriptions.extend(deleted_subscriptions)

        all_relevant_subscriptions = (
            all_cancelled_subscriptions + all_deleted_subscriptions
        )
        if len(all_relevant_subscriptions) > 0:
            all_relevant_subscriptions.sort(
                key=lambda subscription: subscription.end_date, reverse=False
            )
            TransactionalTrigger.fire_action(
                TransactionalTriggerData(
                    key=Events.CONTRACT_CANCELLED,
                    recipient_id_in_base_queryset=member.id,
                    token_data={
                        "contract_list": format_subscription_list_html(
                            all_relevant_subscriptions
                        ),
                        "contract_end_date": format_date(
                            all_relevant_subscriptions[0].end_date
                        ),
                    },
                ),
            )

        if cancel_solidarity_contribution:
            MemberSolidarityContributionService.assign_contribution_to_member(
                member=member,
                change_date=SubscriptionCancellationManager.get_earliest_possible_cancellation_date_for_solidarity_contribution(
                    member=member, cache=self.cache
                ),
                amount=0,
                actor=actor,
                cache=self.cache,
            )

        if len(all_cancelled_subscriptions) > 0:
            SubscriptionChangeLogEntry().populate_subscription_changed(
                actor=actor,
                user=member,
                change_type=SubscriptionChangeLogEntry.SubscriptionChangeLogEntryType.CANCELLED,
                subscriptions=all_cancelled_subscriptions,
                admin_confirmed=get_now(cache=self.cache),
            ).save()

        if len(all_deleted_subscriptions) > 0:
            SubscriptionChangeLogEntry().populate_subscription_changed(
                actor=actor,
                user=member,
                change_type=SubscriptionChangeLogEntry.SubscriptionChangeLogEntryType.CANCELLED,
                subscriptions=all_deleted_subscriptions,
                admin_confirmed=None,
            ).save()

        if cancel_coop_membership:
            MembershipCancellationManager.cancel_coop_membership(
                member, cache=self.cache, actor=actor
            )

        for reason in cancellation_reasons:
            QuestionaireCancellationReasonResponse.objects.create(
                member=member, reason=reason, custom=False
            )
        if custom_cancellation_reason is not None:
            QuestionaireCancellationReasonResponse.objects.create(
                member=member,
                reason=custom_cancellation_reason,
                custom=True,
            )

    def validate_everything(
        self,
        cancel_coop_membership: bool,
        member: Member,
        products_selected_for_cancellation: set[Product],
        cancellation_reasons: list[str],
        custom_cancellation_reason: str | None,
        cancel_solidarity_contribution: bool,
    ):
        if (
            cancel_coop_membership
            and not MembershipCancellationManager.can_member_cancel_coop_membership(
                member, cache=self.cache
            )
        ):
            raise ValidationError(
                "Es ist nur möglich die Beitrittserklärung zu widerrufen wenn du noch nicht Mitglied bist."
            )

        subscribed_products = GetCancellationDataView.get_subscribed_products(
            member, cache=self.cache
        )
        if (
            cancel_coop_membership
            and products_selected_for_cancellation != subscribed_products
        ):
            raise ValidationError(
                "Es ist nur möglich die Beitrittserklärung zu widerrufen wenn du alle Verträge auch kündigst."
            )

        if (
            not get_parameter_value(
                ParameterKeys.SUBSCRIPTION_ADDITIONAL_PRODUCT_ALLOWED_WITHOUT_BASE_PRODUCT,
                cache=self.cache,
            )
            and self.is_at_least_one_additional_product_not_selected(
                subscribed_products,
                products_selected_for_cancellation,
                cache=self.cache,
            )
            and self.are_all_base_products_selected(
                subscribed_products,
                products_selected_for_cancellation,
                cache=self.cache,
            )
        ):
            raise ValidationError(
                "Du kannst keine Zusatzabos beziehen wenn du das Basis-Abo kündigst."
            )

        valid_cancellation_reasons = get_parameter_value(
            ParameterKeys.MEMBER_CANCELLATION_REASON_CHOICES, cache=self.cache
        ).split(";")
        valid_cancellation_reasons = [
            reason.strip() for reason in valid_cancellation_reasons
        ]
        for reason in cancellation_reasons:
            if reason not in valid_cancellation_reasons:
                raise ValidationError(
                    f"Folgende Kündigungsgrund ist nicht gültig: {reason}, gültige Gründe sind: {valid_cancellation_reasons}"
                )

        if len(cancellation_reasons) == 0 and custom_cancellation_reason is None:
            raise ValidationError(
                "Es muss mindestens 1 Kündigungsgrund angegeben werden."
            )

        if cancel_solidarity_contribution:
            contributions = SubscriptionCancellationManager.get_solidarity_contributions_that_could_be_cancelled(
                member=member, cache=self.cache
            )
            if not contributions.exists():
                raise ValidationError("Es kann kein Solidarbeitrag gekündigt werden.")

    @staticmethod
    def are_all_base_products_selected(
        subscribed_products: set[Product],
        products_selected_for_cancellation: set[Product],
        cache: dict,
    ):
        base_product_type = BaseProductTypeService.get_base_product_type(cache=cache)
        for subscribed_product in subscribed_products:
            if (
                subscribed_product.type_id == base_product_type.id
                and subscribed_product not in products_selected_for_cancellation
            ):
                return False

        return True

    @staticmethod
    def is_at_least_one_additional_product_not_selected(
        subscribed_products: set[Product],
        products_selected_for_cancellation: set[Product],
        cache: dict,
    ):
        base_product_type = BaseProductTypeService.get_base_product_type(cache=cache)
        for subscribed_product in subscribed_products:
            if (
                subscribed_product.type_id != base_product_type.id
                and subscribed_product not in products_selected_for_cancellation
            ):
                return True

        return False

    @staticmethod
    def build_response(subscriptions_cancelled: bool, errors: list[str]):
        return Response(
            CancelSubscriptionsViewResponseSerializer(
                {"subscriptions_cancelled": subscriptions_cancelled, "errors": errors}
            ).data,
            status=status.HTTP_200_OK,
        )
