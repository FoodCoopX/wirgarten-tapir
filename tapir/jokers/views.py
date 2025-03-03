from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.jokers.models import Joker
from tapir.jokers.serializers import JokerSerializer
from tapir.wirgarten.utils import check_permission_or_self


class GetMemberJokers(APIView):
    @extend_schema(
        responses={200: JokerSerializer(many=True)},
        parameters=[OpenApiParameter(name="member_id", type=str)],
    )
    def get(self, request):
        member_id = request.query_params.get("member_id")
        check_permission_or_self(member_id, request)

        return Response(
            JokerSerializer(Joker.objects.filter(member_id=member_id), many=True).data,
            status=status.HTTP_200_OK,
        )
