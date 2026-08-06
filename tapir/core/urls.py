from django.urls import path

from tapir.core.views import general
from tapir.core.views import mailing_lists
from tapir.core.views import member_extra_emails

app_name = "core"
urlpatterns = [
    path(
        "api/get_theme",
        general.GetThemeView.as_view(),
        name="get_theme",
    ),
    path(
        "api/member_mail_category_data",
        general.MemberMailCategoryDataApiView.as_view(),
        name="member_mail_category_data",
    ),
    path(
        "api/member_extra_emails",
        member_extra_emails.MemberExtraEmailApiView.as_view(),
        name="member_extra_emails",
    ),
    path(
        "member_extra_email_confirm/<uuid:secret>",
        member_extra_emails.ConfirmMemberExtraEmailApiView.as_view(),
        name="member_extra_email_confirm",
    ),
    path(
        "member_extra_email_confirmed/<uuid:secret>",
        member_extra_emails.MemberExtraEmailConfirmedView.as_view(),
        name="member_extra_email_confirmed",
    ),
    path(
        "mailing_lists",
        mailing_lists.MailingListsBaseView.as_view(),
        name="mailing_lists",
    ),
    path(
        "api/mailing_list_list",
        mailing_lists.MailingListsListView.as_view(),
        name="mailing_list_list",
    ),
    path(
        "api/mailing_list_create",
        mailing_lists.MailingListCreateView.as_view(),
        name="mailing_list_create",
    ),
    path(
        "api/mailing_list_edit",
        mailing_lists.MailingListEditView.as_view(),
        name="mailing_list_edit",
    ),
    path(
        "api/mailing_list_delete",
        mailing_lists.MailingListDeleteView.as_view(),
        name="mailing_list_delete",
    ),
    path(
        "api/mailing_list_recipient_list",
        mailing_lists.MailingListRecipientListView.as_view(),
        name="mailing_list_recipient_list",
    ),
    path(
        "api/mailing_list_subscribe_external",
        mailing_lists.MailingListSubscribeExternalRecipientView.as_view(),
        name="mailing_list_subscribe_external",
    ),
    path(
        "api/mailing_list_unsubscribe",
        mailing_lists.MailingListUnsubscribeRecipientView.as_view(),
        name="mailing_list_unsubscribe",
    ),
    path(
        "api/mailing_list_subscribe_internal",
        mailing_lists.MailingListSubscribeInternalRecipientView.as_view(),
        name="mailing_list_subscribe_internal",
    ),
    path(
        "api/member_mailing_list_data",
        mailing_lists.MemberMailingListDataView.as_view(),
        name="member_mailing_list_data",
    ),
]
