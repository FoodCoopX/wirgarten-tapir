from django.db import transaction
from rest_framework import permissions, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import LimitOffsetPagination
from tapir.mail.models import EmailTemplate, EmailTemplateType
from tapir.mail.permissions import HasEmailManagePermission
from tapir.mail.serializers import EmailTemplateSerializer
from tapir.mail.services.layout import BODY_PLACEHOLDER_SECTION_RE, BODY_TOKEN_RE
from tapir.mail.services.mail_content_validator import MailContentValidator


class EmailTemplateViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, HasEmailManagePermission]
    queryset = EmailTemplate.objects.all()
    serializer_class = EmailTemplateSerializer

    def perform_create(self, serializer):
        self.validate_layout(serializer)
        self.save_with_single_default_layout(serializer)

    def perform_update(self, serializer):
        self.validate_layout(serializer)
        self.save_with_single_default_layout(serializer)

    @staticmethod
    def validate_layout(serializer):
        template_type = serializer.validated_data.get(
            "template_type",
            getattr(serializer.instance, "template_type", EmailTemplateType.START),
        )
        content = serializer.validated_data.get(
            "content", getattr(serializer.instance, "content", "")
        )
        is_default_layout = serializer.validated_data.get(
            "is_default_layout",
            getattr(serializer.instance, "is_default_layout", False),
        )

        if template_type == EmailTemplateType.LAYOUT:
            body_section_count = len(BODY_PLACEHOLDER_SECTION_RE.findall(content))
            if body_section_count != 1:
                raise ValidationError(
                    {
                        "content": "Eine Layout-Vorlage muss genau einen E-Mail-Inhalt-Block enthalten."
                    }
                )
            MailContentValidator.validate_tokens(
                mail_content=BODY_TOKEN_RE.sub("", content),
                trigger_datas=[],
            )
        elif is_default_layout:
            raise ValidationError(
                {
                    "is_default_layout": "Nur Layout-Vorlagen können als Standard markiert werden."
                }
            )

    @staticmethod
    def save_with_single_default_layout(serializer):
        with transaction.atomic():
            if serializer.validated_data.get("is_default_layout"):
                EmailTemplate.objects.filter(is_default_layout=True).exclude(
                    id=getattr(serializer.instance, "id", None)
                ).update(is_default_layout=False)
            serializer.save()


class PaginatedEmailTemplateViewSet(EmailTemplateViewSet):
    pagination_class = LimitOffsetPagination
