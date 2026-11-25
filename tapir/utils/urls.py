from django.conf import settings
from django.urls import path

from tapir.utils.views_member_import import (
    MemberImportView,
    MemberImportPreviewView,
    MemberImportApplyView,
    MemberImportTemplateView,
)

app_name = "utils"
if settings.DEBUG:
    from tapir.utils import views

    urlpatterns = [
        path(
            "reset_test_data",
            views.ResetTestData.as_view(),
            name="reset_test_data",
        ),
    ]
else:
    urlpatterns = []

urlpatterns += [
    path("member_import", MemberImportView.as_view(), name="member_import"),
    path(
        "api/member_import/preview",
        MemberImportPreviewView.as_view(),
        name="member_import_preview",
    ),
    path(
        "api/member_import/apply",
        MemberImportApplyView.as_view(),
        name="member_import_apply",
    ),
    path(
        "member_import/template",
        MemberImportTemplateView.as_view(),
        name="member_import_template",
    ),
]
