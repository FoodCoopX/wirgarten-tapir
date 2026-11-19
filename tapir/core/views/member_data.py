import weasyprint
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.views import APIView
from rest_framework.response import Response

from tapir.core.serializers import MemberDataDisclosureSerializer
from tapir.core.services.member_data_disclosure_service import (
    MemberDataDisclosureService,
)
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import check_permission_or_self


class MemberDataDisclosureApiView(APIView):
    @extend_schema(
        responses={200: MemberDataDisclosureSerializer},
        parameters=[OpenApiParameter("member_id", type=str)],
    )
    def get(self, request):
        member = _get_member_checking_permission(request)
        data = MemberDataDisclosureService.build(member, cache={})
        return Response(MemberDataDisclosureSerializer(data).data)


class MemberDataDisclosurePdfApiView(APIView):
    @extend_schema(
        responses={200: OpenApiTypes.BINARY},
        parameters=[OpenApiParameter("member_id", type=str)],
    )
    def get(self, request):
        member = _get_member_checking_permission(request)
        data = MemberDataDisclosureService.build(member, cache={})
        html = render_to_string("core/member_data_disclosure.html", data)
        response = HttpResponse(
            weasyprint.HTML(string=html).write_pdf(),
            content_type="application/pdf",
        )
        file_name = f"gespeicherte-daten-{member.member_no or member.id}.pdf"
        response["Content-Disposition"] = f'attachment; filename="{file_name}"'
        return response


def _get_member_checking_permission(request) -> Member:
    member_id = request.query_params.get("member_id")
    check_permission_or_self(pk=member_id, request=request)
    return get_object_or_404(Member, id=member_id)
