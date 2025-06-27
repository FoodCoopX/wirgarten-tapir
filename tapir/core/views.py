from typing import Literal

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys


class GetThemeView(APIView):
    permission_classes = ()

    @extend_schema(
        responses={200: Literal["l2g", "biotop", "wirgarten", "mm"]},
    )
    def get(self, request):
        return Response(
            (get_parameter_value(ParameterKeys.ORGANISATION_THEME)),
            status=status.HTTP_200_OK,
        )
