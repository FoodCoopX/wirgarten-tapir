from django.db import transaction
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from tapir.mail.models import StaticSegment, MailCategory
from tapir.mail.permissions import HasEmailManagePermission
from tapir.mail.serializers import MailCategorySerializer


class MailCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, HasEmailManagePermission]
    queryset = MailCategory.objects.order_by("name")
    serializer_class = MailCategorySerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["cache"] = {}
        return context

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        static_segment = StaticSegment.objects.create(
            name=f"Mail-Kategorie:{data["name"]}"
        )

        category = MailCategory.objects.create(
            name=data["name"],
            mode=data["mode"],
            available_for_external_recipients=data["available_for_external_recipients"],
            static_segment=static_segment,
        )

        return Response(
            self.get_serializer(category).data,
            status=status.HTTP_201_CREATED,
        )

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        instance: MailCategory = self.get_object()
        static_segment = instance.static_segment
        instance.delete()
        static_segment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
