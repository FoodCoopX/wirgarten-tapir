import json

import weasyprint
from django.core.serializers.json import DjangoJSONEncoder
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
        data = MemberDataDisclosureService.build(member)
        return Response(MemberDataDisclosureSerializer(data).data)


class MemberDataDisclosureDownloadApiView(APIView):
    # "format" is taken by DRF's content negotiation, hence "file_type"
    @extend_schema(
        responses={200: OpenApiTypes.BINARY},
        parameters=[
            OpenApiParameter("member_id", type=str),
            OpenApiParameter("file_type", type=str, enum=["json", "pdf"]),
        ],
    )
    def get(self, request):
        member = _get_member_checking_permission(request)
        data = MemberDataDisclosureService.build(member)
        file_name = f"gespeicherte-daten-{member.member_no or member.id}"

        if request.query_params.get("file_type") == "pdf":
            html = render_to_string("core/member_data_disclosure.html", data)
            response = HttpResponse(
                weasyprint.HTML(string=html).write_pdf(),
                content_type="application/pdf",
            )
            response["Content-Disposition"] = f'attachment; filename="{file_name}.pdf"'
            return response

        response = HttpResponse(
            json.dumps(
                _to_machine_readable(data),
                cls=DjangoJSONEncoder,
                ensure_ascii=False,
                indent=2,
            ),
            content_type="application/json; charset=utf-8",
        )
        response["Content-Disposition"] = f'attachment; filename="{file_name}.json"'
        return response


def _get_member_checking_permission(request) -> Member:
    member_id = request.query_params.get("member_id")
    check_permission_or_self(pk=member_id, request=request)
    return get_object_or_404(Member, id=member_id)


def _to_machine_readable(data: dict) -> dict:
    """Records become objects keyed by the field name (Art. 20 GDPR)."""
    return {
        **data,
        "sections": [
            {
                **section,
                "records": [
                    {field["name"]: field["value"] for field in record}
                    for record in section["records"]
                ],
            }
            for section in data["sections"]
        ],
    }
