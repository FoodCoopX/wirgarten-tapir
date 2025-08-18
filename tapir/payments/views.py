from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.payments.serializers import PaymentSerializer
from tapir.payments.services.month_payment_builder import MonthPaymentBuilder
from tapir.utils.shortcuts import get_first_of_next_month
from tapir.wirgarten.models import Member, Payment
from tapir.wirgarten.service.member import get_or_create_mandate_ref
from tapir.wirgarten.utils import check_permission_or_self, get_today


class GetFutureMemberPaymentsApiView(APIView):
    def __init__(self):
        super().__init__()
        self.cache = {}

    @extend_schema(
        responses={200: PaymentSerializer(many=True)},
        parameters=[OpenApiParameter(name="member_id", type=str)],
    )
    def get(self, request):
        member_id = request.query_params.get("member_id")
        member = get_object_or_404(Member, id=member_id)
        check_permission_or_self(pk=member_id, request=request)

        mandate_ref = get_or_create_mandate_ref(member=member, cache=self.cache)
        member_payments = list(
            Payment.objects.filter(
                mandate_ref=mandate_ref, due_date__gte=get_today(cache=self.cache)
            )
        )

        current_month = get_today(cache=self.cache)
        for _ in range(12):
            current_month = get_first_of_next_month(current_month)
            payments = MonthPaymentBuilder.build_payments_for_month(
                reference_date=current_month, cache=self.cache
            )
            member_payments.extend(
                [payment for payment in payments if payment.mandate_ref == mandate_ref]
            )

        return Response(PaymentSerializer(member_payments, many=True).data)
