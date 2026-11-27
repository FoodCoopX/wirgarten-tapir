from rest_framework import serializers

from tapir.mail.models import MailCategory
from tapir.wirgarten.serializers import MemberExtraEmailSerializer


class MemberMailCategoryRequestSerializer(serializers.Serializer):
    categories_registered_to = serializers.DictField(child=serializers.BooleanField())
    member_id = serializers.CharField()


class MemberExtraMailDataSerializer(serializers.Serializer):
    extra_mails = MemberExtraEmailSerializer(many=True)
    explanation_text = serializers.CharField()


class MemberExtraEmailCreateRequest(serializers.Serializer):
    member_id = serializers.CharField()
    extra_email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    receives_direct_mails = serializers.BooleanField()


class MemberExtraEmailUpdateRequest(serializers.Serializer):
    extra_email_id = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    receives_direct_mails = serializers.BooleanField()


class MemberExtraEmailSendManagementLinkRequest(serializers.Serializer):
    extra_email_id = serializers.CharField()


class MailingListSerializer(serializers.Serializer):
    name = serializers.CharField()
    nb_recipients = serializers.IntegerField()
    advertised = serializers.BooleanField()
    moderated = serializers.BooleanField()
    description = serializers.CharField()


class MailingListAdminSerializer(MailingListSerializer):
    nb_held_messages = serializers.IntegerField()


class MailingListCreateSerializer(serializers.Serializer):
    name = serializers.CharField()
    advertised = serializers.BooleanField()
    moderated = serializers.BooleanField()
    description = serializers.CharField()


class MailingListRecipientExtraEmailMemberSerializer(serializers.Serializer):
    display_name = serializers.CharField()
    email = serializers.EmailField()


class MailingListRecipientSerializer(serializers.Serializer):
    address = serializers.EmailField()
    user_confirmed = serializers.BooleanField()
    link_to_member_profile = serializers.CharField(allow_null=True)
    extra_email_member = MailingListRecipientExtraEmailMemberSerializer(allow_null=True)


class MailingListHeldMessageSerializer(serializers.Serializer):
    request_id = serializers.IntegerField()
    sender = serializers.CharField()
    sender_name = serializers.CharField(allow_null=True)
    formatted_member_number = serializers.CharField(allow_null=True)
    link_to_member_profile = serializers.CharField(allow_null=True)
    subject = serializers.CharField(allow_blank=True)
    reason = serializers.CharField(allow_blank=True)
    hold_date = serializers.DateTimeField()
    body = serializers.CharField(allow_blank=True)


class MailingListModerateHeldMessageRequestSerializer(serializers.Serializer):
    list_name = serializers.CharField()
    request_id = serializers.IntegerField()
    moderation_action = serializers.ChoiceField(choices=["accept", "reject", "discard"])


class MailingListSubscribeExternalRecipientRequestSerializer(serializers.Serializer):
    address = serializers.EmailField()
    list_name = serializers.CharField()


class MailingListSubscribeInternalRecipientRequestSerializer(serializers.Serializer):
    member_id = serializers.CharField()
    list_name = serializers.CharField()


class MemberMailingListDataResponseSerializer(serializers.Serializer):
    belongs_to_former_member = serializers.BooleanField()
    available_lists = MailingListSerializer(many=True)
    subscribed_lists = serializers.ListField(child=serializers.CharField())
    waiting_for_confirmation_lists = serializers.ListField(
        child=serializers.CharField()
    )


class MemberDataFieldSerializer(serializers.Serializer):
    name = serializers.CharField()
    label = serializers.CharField()
    value = serializers.CharField(allow_null=True)


class MemberDataSectionSerializer(serializers.Serializer):
    key = serializers.CharField()
    title = serializers.CharField()
    purpose = serializers.CharField()
    retention = serializers.CharField()
    records = serializers.ListField(child=MemberDataFieldSerializer(many=True))


class MemberDataLogOverviewSerializer(serializers.Serializer):
    type = serializers.CharField()
    count = serializers.IntegerField()
    first = serializers.DateTimeField()
    last = serializers.DateTimeField()


class MemberDataMailOverviewSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    first = serializers.DateTimeField(allow_null=True)
    last = serializers.DateTimeField(allow_null=True)


class MemberDataMemberSerializer(serializers.Serializer):
    id = serializers.CharField()
    member_no = serializers.IntegerField(allow_null=True)
    name = serializers.CharField()


class MemberDataDisclosureSerializer(serializers.Serializer):
    generated_at = serializers.DateTimeField()
    member = MemberDataMemberSerializer()
    sections = MemberDataSectionSerializer(many=True)
    log_overview = MemberDataLogOverviewSerializer(many=True)
    mail_overview = MemberDataMailOverviewSerializer()
    pdf_url = serializers.CharField()


class SubscriptionManagementCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MailCategory
        fields = ["id", "name", "mode"]


class SubscriptionManagementCategoriesSerializer(serializers.Serializer):
    categories = SubscriptionManagementCategorySerializer(many=True)
    categories_registered_to = serializers.DictField(child=serializers.BooleanField())


class SubscriptionManagementExtraPartSerializer(
    SubscriptionManagementCategoriesSerializer
):
    member_first_name = serializers.CharField()
    receives_direct_mails = serializers.BooleanField()


class SubscriptionManagementExternalPartSerializer(
    SubscriptionManagementCategoriesSerializer
):
    first_name = serializers.CharField()


class SubscriptionManagementDataSerializer(serializers.Serializer):
    address = serializers.CharField()
    extra = SubscriptionManagementExtraPartSerializer(allow_null=True)
    external = SubscriptionManagementExternalPartSerializer(allow_null=True)
    mailing_lists = MemberMailingListDataResponseSerializer(allow_null=True)


class SubscriptionManagementCategoriesRequest(serializers.Serializer):
    token = serializers.CharField()
    categories_registered_to = serializers.DictField(child=serializers.BooleanField())


class SubscriptionManagementExternalRequest(SubscriptionManagementCategoriesRequest):
    first_name = serializers.CharField()


class SubscriptionManagementMailingListRequest(serializers.Serializer):
    token = serializers.CharField()
    list_name = serializers.CharField()
