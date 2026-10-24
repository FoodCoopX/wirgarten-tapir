from rest_framework import serializers

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


class MemberExtraEmailUpdateRequest(serializers.Serializer):
    extra_email_id = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()


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


class MailingListRecipientSerializer(serializers.Serializer):
    address = serializers.EmailField()
    user_confirmed = serializers.BooleanField()
    link_to_member_profile = serializers.CharField(allow_null=True)


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
    available_lists = MailingListSerializer(many=True)
    subscribed_lists = serializers.ListField(child=serializers.CharField())
    waiting_for_confirmation_lists = serializers.ListField(
        child=serializers.CharField()
    )
