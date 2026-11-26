from tapir.wirgarten.parameters import ParameterDefinitions
from django.urls import reverse
import datetime
import json

from tapir.mail.models import (
    EmailConfigurationVersion,
    EmailTemplateType,
    ReleaseStatus,
    EmailConfiguration,
    EmailConfigurationDispatch,
)
from tapir.mail.tests.factories import (
    EmailTemplateFactory,
    MailSegmentFactory,
    EmailConfigurationFactory,
    EmailConfigurationVersionFactory,
)
from tapir.mail.tests.test_utils import build_time_trigger_dict
from tapir.mail.tests.test_utils import add_mail_segment_provider
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.models import Member


class TestEmailConfigurationVersionViewSetCreate(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    CONFIG_NAME = "Test name"
    VERSION_CONTENT = "Test content"
    VERSION_SUBJECT = "Test subject"

    def setUp(self) -> None:
        super().setUp()
        self._login_as_admin()
        add_mail_segment_provider(
            self,
            lambda: {
                "test_segment": MailSegmentFactory.build(
                    get_queryset=Member.objects.all
                )
            },
        )

    def test_invalidData_returns400(self):
        response = self._send_request({"invalid_parameter": "aaa"})

        self.assertStatusCode(response, 400)
        self.assertEqual(0, EmailConfigurationVersion.objects.count())

    def test_emailConfigurationDoesntExist_emailConfigurationGetsCreated(self):
        response = self._send_request(self.get_minimal_post_data())

        self.assertStatusCode(response, 201)
        self.assertEqual(1, EmailConfiguration.objects.count())
        config = EmailConfiguration.objects.get()
        self.assertEqual(self.CONFIG_NAME, config.name)

    def test_emailConfigurationAlreadyExists_emailConfigurationGetsUpdated(self):
        EmailConfigurationFactory.create(
            name=self.CONFIG_NAME, description="Description before"
        )
        post_data = self.get_minimal_post_data()
        post_data["description"] = "Description after"
        response = self._send_request(post_data)

        self.assertStatusCode(response, 201)
        self.assertEqual(1, EmailConfiguration.objects.count())
        config = EmailConfiguration.objects.get()
        self.assertEqual(self.CONFIG_NAME, config.name)
        self.assertIn("Description after", config.description)

    def test_default_emailConfigurationVersionGetsCreated(self):
        config = EmailConfigurationFactory.create()
        trigger = build_time_trigger_dict()
        post_data = {
            "name": config.name,
            "content": self.VERSION_CONTENT,
            "subject": self.VERSION_SUBJECT,
            "release_status": "Test status",
            "triggers": [trigger],
            "segment_data": {
                "dynamic_segment_names_additive": [],
                "dynamic_segment_names_subtractive": [],
                "static_segment_ids_additive": [],
                "static_segment_ids_subtractive": [],
                "mail_category_ids_additive": [],
            },
        }
        response = self._send_request(post_data)

        self.assertStatusCode(response, 201)
        self.assertEqual(1, EmailConfigurationVersion.objects.count())
        version = EmailConfigurationVersion.objects.get()
        self.assertEqual(self.VERSION_CONTENT, version.content)
        self.assertEqual(self.VERSION_SUBJECT, version.subject)
        self.assertEqual("Test status", version.status)
        self.assertEqual([trigger], version.triggers)
        self.assertEqual([], version.dynamic_segments_additive)
        self.assertEqual([], version.dynamic_segments_subtractive)
        self.assertEqual(0, version.static_segments_additive.count())
        self.assertEqual(0, version.static_segments_subtractive.count())
        self.assertEqual(0, version.mail_categories_additive.count())
        self.assertEqual({"id": version.id}, json.loads(response.content))

    def test_creatingDraftVersion_triggerNotExecuted(self):
        post_data = self.get_minimal_post_data()
        post_data["release_status"] = ReleaseStatus.DRAFT
        post_data["triggers"] = [build_time_trigger_dict()]
        response = self._send_request(post_data)

        self.assertStatusCode(response, 201)
        self.assertFalse(EmailConfigurationDispatch.objects.exists())

    def test_creatingReleaseVersion_triggerExecuted(self):
        post_data = self.get_minimal_post_data()
        post_data["release_status"] = ReleaseStatus.RELEASED
        trigger = build_time_trigger_dict()
        post_data["triggers"] = [trigger]
        response = self._send_request(post_data)

        self.assertStatusCode(response, 201)
        self.assertEqual(1, EmailConfigurationDispatch.objects.count())
        config_dispatch = EmailConfigurationDispatch.objects.get()
        self.assertEqual(
            [trigger], config_dispatch.email_configuration_version.triggers
        )

    def test_creatingReleaseVersionWithMultipleTriggers_allTriggersExecuted(self):
        post_data = self.get_minimal_post_data()
        post_data["release_status"] = ReleaseStatus.RELEASED
        triggers = [build_time_trigger_dict(), build_time_trigger_dict()]
        post_data["triggers"] = triggers
        response = self._send_request(post_data)

        self.assertStatusCode(response, 201)
        self.assertEqual(2, EmailConfigurationDispatch.objects.count())
        email_configuration_version = EmailConfigurationVersion.objects.get()
        self.assertEqual(triggers, email_configuration_version.triggers)

    def test_creatingReleaseVersion_olderReleaseGetsArchived(self):
        older_release = EmailConfigurationVersionFactory.create(
            status=ReleaseStatus.RELEASED
        )
        EmailConfigurationVersion.objects.filter(id=older_release.id).update(
            updated_at=datetime.datetime(
                year=2021, month=1, day=17, hour=12, minute=34, tzinfo=datetime.UTC
            )
        )
        post_data = self.get_minimal_post_data()
        post_data["name"] = older_release.email_configuration.name
        post_data["release_status"] = ReleaseStatus.RELEASED
        response = self._send_request(post_data)

        self.assertStatusCode(response, 201)
        older_release.refresh_from_db()
        self.assertEqual(ReleaseStatus.ARCHIVED, older_release.status)
        self.assertEqual(
            datetime.datetime(
                year=2021, month=1, day=17, hour=12, minute=34, tzinfo=datetime.UTC
            ),
            older_release.updated_at,
            "The updated_at field should not get updated on archive",
        )

    def test_createEmailConfigurationVersion_layoutDisabled_savesVersionWithoutLayout(
        self,
    ):
        layout = EmailTemplateFactory.create(
            template_type=EmailTemplateType.LAYOUT,
            content="<mjml><mj-body><mj-text>{{Body}}</mj-text></mj-body></mjml>",
        )
        post_data = self.get_minimal_post_data()
        post_data["layout_template_id"] = layout.id
        post_data["layout_enabled"] = False

        response = self._send_request(post_data)

        self.assertStatusCode(response, 201)
        version = EmailConfigurationVersion.objects.get()
        self.assertFalse(version.layout_enabled)
        self.assertIsNone(version.layout_template_id)

    def get_minimal_post_data(self):
        return {
            "name": self.CONFIG_NAME,
            "subject": self.VERSION_SUBJECT,
            "content": self.VERSION_CONTENT,
            "release_status": ReleaseStatus.DRAFT,
            "triggers": [build_time_trigger_dict()],
            "segment_data": {
                "dynamic_segment_names_additive": ["test_segment"],
                "dynamic_segment_names_subtractive": [],
                "static_segment_ids_additive": [],
                "static_segment_ids_subtractive": [],
                "mail_category_ids_additive": [],
            },
        }

    def _send_request(self, post_data: dict | None):
        return self.client.post(
            reverse("emailconfigurationversion-list"),
            data=post_data,
            content_type="application/json",
        )
