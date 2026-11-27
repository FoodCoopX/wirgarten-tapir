import uuid
from functools import partial

from django.contrib.postgres.fields import ArrayField
from django.db import models, transaction
from django.db.models import Q, ManyToManyField
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from nanoid import generate

ID_LENGTH = 10


def generate_id():
    return generate(size=ID_LENGTH)


class BaseModel(models.Model):
    """
    Provides a base model for all models in the project. This model is abstract and should not be used directly.
    """

    id = models.CharField(
        "ID",
        max_length=ID_LENGTH,
        unique=True,
        primary_key=True,
        default=partial(generate_id),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class EmailTemplateType(models.TextChoices):
    START = "start", _("Start-Vorlage")
    LAYOUT = "layout", _("Layout-Vorlage")


class EmailTemplate(BaseModel):
    """
    This represents the email content that is referenced by the EmailConfiguration.

    A template is either a "start" template (used to prefill the editor) or a "layout"
    template (a reusable MJML frame around the email body containing a ``{{Body}}``
    placeholder). One layout template can be marked as the global default.
    """

    name = models.CharField(max_length=255, unique=True)
    content = models.TextField()
    template_type = models.CharField(
        max_length=16,
        choices=EmailTemplateType.choices,
        default=EmailTemplateType.START,
    )
    is_default_layout = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["is_default_layout"],
                condition=Q(is_default_layout=True),
                name="unique_default_layout_template",
            )
        ]

    def __str__(self):
        return self.name


class EmailConfiguration(BaseModel):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(null=True, blank=True)


class ReleaseStatus:
    DRAFT = "draft"
    RELEASED = "released"
    ARCHIVED = "archived"
    ERROR = "error"


RELEASE_STATUS_CHOICES = [
    (ReleaseStatus.DRAFT, "Draft"),
    (ReleaseStatus.RELEASED, "Released"),
    (ReleaseStatus.ARCHIVED, "Archived"),
    (ReleaseStatus.ERROR, "Error"),
]


class StaticSegment(BaseModel):
    name = models.CharField(max_length=255, unique=True)


class MailCategoryMode(models.TextChoices):
    OPTIONAL_DEFAULT_ON = "optional_default_on", _("Optional (Standard: ON)")
    OPTIONAL_DEFAULT_OFF = "optional_default_off", _("Optional (Standard: OFF)")
    ALWAYS_ON = "always_on", _("Pflicht")


class MailCategory(BaseModel):
    name = models.CharField(max_length=255, unique=True)
    mode = models.CharField(max_length=30, choices=MailCategoryMode)
    available_for_external_recipients = models.BooleanField()
    static_segment = models.OneToOneField(StaticSegment, on_delete=models.PROTECT)
    dynamic_segment_name = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.name} - Mode:{self.mode} - External:{self.available_for_external_recipients}"


class EmailConfigurationVersion(BaseModel):
    """
    This represents the configuration for an email that will be sent to a user or segment.
    """

    content = models.TextField(null=True)
    subject = models.CharField(max_length=255, null=True, blank=True)
    email_configuration = models.ForeignKey(
        EmailConfiguration, on_delete=models.CASCADE, related_name="versions"
    )
    status = models.CharField(
        max_length=255,
        choices=RELEASE_STATUS_CHOICES,
        default=ReleaseStatus.DRAFT,
    )
    # See TriggerSerializationMixin for the expected content of this field
    triggers = models.JSONField(null=True, blank=True)

    dynamic_segments_additive = ArrayField(
        base_field=models.CharField(max_length=100), default=list
    )
    dynamic_segments_subtractive = ArrayField(
        base_field=models.CharField(max_length=100), default=list
    )
    static_segments_additive = ManyToManyField(
        StaticSegment, related_name="versions_with_additive"
    )
    static_segments_subtractive = ManyToManyField(
        StaticSegment, related_name="versions_with_subtractive"
    )
    mail_categories_additive = ManyToManyField(MailCategory)
    # Layout handling. layout_enabled is False for versions that existed before the
    # layout feature, so already existing emails keep their behaviour until they are
    # saved again. When layout_enabled is True and layout_template is None, the global
    # default layout is used at send time.
    layout_template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="versions_using_layout",
    )
    layout_enabled = models.BooleanField(default=False)

    @transaction.atomic
    def release(self):
        from tapir.mail.services.email_configuration_version_release_validator import (
            EmailConfigurationVersionReleaseValidator,
        )

        EmailConfigurationVersionReleaseValidator.validate_version_can_be_released(
            version=self
        )
        self.status = ReleaseStatus.RELEASED
        self.save()

        # Archive current released version
        for version in self.email_configuration.versions.exclude(id=self.id).filter(
            status=ReleaseStatus.RELEASED
        ):
            version.archive()

    def archive(self):
        # Use update() instead of save() so that updated_at doesn't get set
        EmailConfigurationVersion.objects.filter(id=self.id).update(
            status=ReleaseStatus.ARCHIVED
        )

    def __str__(self):
        return f"{self.email_configuration.name} ({self.status}) ({self.updated_at})"


class EmailConfigurationDispatch(BaseModel):
    """
    This represents an email that has been scheduled to be sent to a list of recipients.
    """

    email_configuration_version = models.ForeignKey(
        EmailConfigurationVersion, on_delete=models.CASCADE
    )
    scheduled_time = models.DateTimeField(default=timezone.now)
    is_sent = models.BooleanField(default=False)
    override_recipients = models.JSONField(null=True)
    additional_tokens = models.JSONField(null=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["is_sent", "scheduled_time"],
                name="emailconfigdispatch_sched_idx",
            ),
        ]

    def __str__(self):
        return f"{self.email_configuration_version} - {self.scheduled_time} - {self.is_sent}"


class EmailDispatch(BaseModel):
    """
    This represents an email that has been sent to a single recipient.
    Here we can track bounces, errors, opening, etc.
    """

    class BounceTypes(models.TextChoices):
        SOFT = "soft", "Soft"
        HARD = "hard", "Hard"
        UNKNOWN = "unknown", "Unknown"
        NOT_ANALYZED = "not_analyzed", "Not analyzed"

    class DispatchStatus(models.TextChoices):
        ERROR = "error", "Fehler beim Versand"
        BOUNCED = "bounced", "Bounce"
        OPENED = "opened", "Geöffnet"
        DELIVERED = "delivered", "Zugestellt"
        UNKNOWN = "unknown", "Nicht geöffnet"
        SENDING = "sending", "Wird versendet"

    class EmailDispatchQuerySet(models.QuerySet):
        def with_error(self, failed: bool):
            filters = Q(error_message__isnull=False) | Q(bounce_message__isnull=False)
            if failed:
                result = self.filter(filters)
            else:
                result = self.exclude(filters)
            return result.distinct()

    objects = EmailDispatchQuerySet.as_manager()

    email_configuration_dispatch = models.ForeignKey(
        EmailConfigurationDispatch, on_delete=models.CASCADE
    )
    recipient = models.EmailField()
    recipient_tokens = models.JSONField(null=True)
    additional_tokens = models.JSONField(null=True)
    sent_time = models.DateTimeField(null=True, blank=True)
    opened_time = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    bounce_message = models.TextField(null=True, blank=True)
    bounce_type = models.CharField(
        max_length=16,
        choices=BounceTypes.choices,
        default=BounceTypes.NOT_ANALYZED,
    )
    smtp_response_code = models.SmallIntegerField(null=True, blank=True)
    smtp_response_message = models.TextField(null=True, blank=True)
    dsn_delivered_time = models.DateTimeField(null=True, blank=True)
    next_retry = models.OneToOneField(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="previous_retry",
    )
    # Overrides the version of email_configuration_dispatch, set on retries
    email_configuration_version = models.ForeignKey(
        EmailConfigurationVersion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    not_before = models.DateTimeField(null=True, blank=True)
    is_automatic_retry = models.BooleanField(default=False)

    class Meta:
        indexes = [
            # Speeds up the batch query of SendEmailBatch.send_email_dispatches
            models.Index(
                fields=["created_at"],
                condition=Q(sent_time=None, error_message=None),
                name="emaildispatch_pending_idx",
            ),
            # Matches the ordering of EmailDispatchViewSet.list
            models.Index(
                fields=["-created_at", "-sent_time", "-opened_time", "recipient"],
                name="emaildispatch_list_idx",
            ),
        ]

    def get_email_configuration_version(self):
        return (
            self.email_configuration_version
            or self.email_configuration_dispatch.email_configuration_version
        )

    def get_consecutive_automatic_retry_count(self):
        count = 0
        current_dispatch = self
        while current_dispatch is not None and current_dispatch.is_automatic_retry:
            count += 1
            current_dispatch = getattr(current_dispatch, "previous_retry", None)
        return count

    def get_previous_retries(self):
        retries = []
        current_dispatch = getattr(self, "previous_retry", None)
        while current_dispatch is not None:
            retries.append(current_dispatch)
            current_dispatch = getattr(current_dispatch, "previous_retry", None)
        return list(retries)

    def __str__(self):
        return (
            f"{self.email_configuration_dispatch} - {self.recipient} - {self.sent_time}"
        )

    def get_dispatch_status(self):
        if self.error_message:
            return self.DispatchStatus.ERROR
        if self.bounce_message:
            return self.DispatchStatus.BOUNCED
        if not self.sent_time:
            return self.DispatchStatus.SENDING
        if self.opened_time:
            return self.DispatchStatus.OPENED
        if self.dsn_delivered_time:
            return self.DispatchStatus.DELIVERED
        return self.DispatchStatus.UNKNOWN


class StaticSegmentRecipient(BaseModel):
    segment = models.ForeignKey(
        StaticSegment, related_name="recipients", on_delete=models.CASCADE
    )
    first_name = models.CharField(max_length=255, null=True)
    last_name = models.CharField(max_length=255, null=True)
    email = models.EmailField()
    custom_data = models.JSONField(null=True)  # For additional fields, tokens etc.

    def __str__(self):
        return f"{self.first_name} {self.last_name} <{self.email}>"


class ExternalRecipient(BaseModel):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["email"], name="unique_external_recipient_email"
            ),
        ]

    email = models.EmailField()
    first_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.first_name} - {self.email}"


class ExternalRecipientConfirmation(BaseModel):
    external_recipient = models.ForeignKey(ExternalRecipient, on_delete=models.CASCADE)
    mail_category = models.ForeignKey(MailCategory, on_delete=models.CASCADE)
    confirmed_at = models.DateTimeField(null=True)
    confirmation_secret = models.UUIDField(default=uuid.uuid4)


class InternalRecipientCategoryRegistration(BaseModel):
    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(member__isnull=False, member_extra_email__isnull=True)
                | Q(member__isnull=True, member_extra_email__isnull=False),
                name="registration_has_exactly_one_recipient",
            ),
            models.UniqueConstraint(
                fields=["mail_category", "member"],
                name="unique_member_registration_per_category",
            ),
            models.UniqueConstraint(
                fields=["mail_category", "member_extra_email"],
                name="unique_member_extra_email_registration_per_category",
            ),
        ]

    member = models.ForeignKey("wirgarten.Member", on_delete=models.CASCADE, null=True)
    member_extra_email = models.ForeignKey(
        "wirgarten.MemberExtraEmail", on_delete=models.CASCADE, null=True
    )
    mail_category = models.ForeignKey(MailCategory, on_delete=models.CASCADE)
    is_registered = models.BooleanField()
