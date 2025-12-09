from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.solidarity_contribution.serializers import SolidarityContributionSerializer
from tapir.wirgarten.utils import check_permission_or_self


class MemberSolidarityContributionsApiView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: SolidarityContributionSerializer(many=True)},
        parameters=[OpenApiParameter(name="member_id", type=str)],
    )
    def get(self, request):
        member_id = request.query_params.get("member_id")
        check_permission_or_self(member_id, request)

        contributions = SolidarityContribution.objects.filter(
            member_id=member_id
        ).order_by("start_date")

        return Response(SolidarityContributionSerializer(contributions, many=True).data)
