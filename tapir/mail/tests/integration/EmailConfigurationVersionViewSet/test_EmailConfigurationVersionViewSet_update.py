from tapir.wirgarten.parameters import ParameterDefinitions
from django.urls import reverse
from tapir.mail.models import (
    EmailConfigurationVersion,
    EmailTemplateType,
    ReleaseStatus,
    EmailConfigurationDispatch,
)

from tapir.mail.tests.factories import (
    EmailTemplateFactory,
    MailSegmentFactory,
    EmailConfigurationVersionFactory,
    EmailConfigurationDispatchFactory,
)
from tapir.mail.tests.test_utils import build_time_trigger_dict
from tapir.mail.tests.test_utils import add_mail_segment_provider
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.models import Member


class TestEmailConfigurationVersionViewSetUpdate(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    TEST_SEGMENT = "Test segment"

    def setUp(self) -> None:
        super().setUp()
        self._login_as_admin()
        add_mail_segment_provider(
            self,
            lambda: {
                self.TEST_SEGMENT: MailSegmentFactory.build(
                    get_queryset=Member.objects.all
                )
            },
        )

    def test_invalidData_returns400(self):
        version = EmailConfigurationVersionFactory.create()
        response = self._send_request(version.id, {"invalid_parameter": "aaa"})

        self.assertStatusCode(response, 400)

    def test_default_emailConfigurationVersionGetsUpdated(self):
        version = EmailConfigurationVersionFactory.create(
            email_configuration__name="Name before",
            email_configuration__description="Description before",
            content="Content before",
            subject="Subject before",
            status="Status before",
            dynamic_segments_additive=[self.TEST_SEGMENT],
            triggers=None,
        )

        trigger = build_time_trigger_dict()
        put_data = {
            "name": "Name after",
            "description": "Description after",
            "content": "Content after",
            "subject": "Subject after",
            "release_status": "Status after",
            "triggers": [trigger],
            "segment_data": {
                "dynamic_segment_names_additive": [],
                "dynamic_segment_names_subtractive": [self.TEST_SEGMENT],
                "static_segment_ids_additive": [],
                "static_segment_ids_subtractive": [],
                "mail_category_ids_additive": [],
            },
        }
        response = self._send_request(version.id, put_data)

        self.assertStatusCode(response, 200)
        version.refresh_from_db()
        self.assertEqual("Name after", version.email_configuration.name)
        self.assertEqual("Description after", version.email_configuration.description)
        self.assertEqual("Content after", version.content)
        self.assertEqual("Subject after", version.subject)
        self.assertEqual("Status after", version.status)
        self.assertEqual([trigger], version.triggers)
        self.assertEqual([], version.dynamic_segments_additive)
        self.assertEqual([self.TEST_SEGMENT], version.dynamic_segments_subtractive)

    def test_creatingReleaseVersion_olderReleaseGetsArchived(self):
        older_release: EmailConfigurationVersion = (
            EmailConfigurationVersionFactory.create(status=ReleaseStatus.RELEASED)
        )
        new_version = EmailConfigurationVersionFactory.create(
            email_configuration=older_release.email_configuration,
            status=ReleaseStatus.DRAFT,
        )
        put_data = {
            "name": older_release.email_configuration.name,
            "content": older_release.content,
            "subject": "test subject",
            "release_status": ReleaseStatus.RELEASED,
            "triggers": [build_time_trigger_dict()],
            "segment_data": {
                "dynamic_segment_names_additive": [self.TEST_SEGMENT],
                "dynamic_segment_names_subtractive": [],
                "static_segment_ids_additive": [],
                "static_segment_ids_subtractive": [],
                "mail_category_ids_additive": [],
            },
        }
        response = self._send_request(new_version.id, put_data)

        self.assertStatusCode(response, 200)
        older_release.refresh_from_db()
        self.assertEqual(ReleaseStatus.ARCHIVED, older_release.status)

    def test_archiving_emailDispatchesGetDeleted(self):
        version: EmailConfigurationVersion = EmailConfigurationVersionFactory.create(
            status=ReleaseStatus.RELEASED
        )
        sent_dispatch = EmailConfigurationDispatchFactory.create(
            email_configuration_version=version, is_sent=True
        )
        EmailConfigurationDispatchFactory.create(
            email_configuration_version=version, is_sent=False
        )
        put_data = {
            "name": version.email_configuration.name,
            "content": version.content,
            "release_status": ReleaseStatus.ARCHIVED,
            "triggers": [build_time_trigger_dict()],
            "segment_data": {
                "dynamic_segment_names_additive": [self.TEST_SEGMENT],
                "dynamic_segment_names_subtractive": [],
                "static_segment_ids_additive": [],
                "static_segment_ids_subtractive": [],
                "mail_category_ids_additive": [],
            },
        }
        response = self._send_request(version.id, put_data)
        self.assertStatusCode(response, 200)
        version.refresh_from_db()
        self.assertEqual(ReleaseStatus.ARCHIVED, version.status)
        self.assertEqual(1, EmailConfigurationDispatch.objects.count())
        self.assertEqual(
            sent_dispatch.id, EmailConfigurationDispatch.objects.first().id
        )

    def test_updateEmailConfigurationVersion_layoutDisabled_clearsLayout(self):
        layout = EmailTemplateFactory.create(
            template_type=EmailTemplateType.LAYOUT,
            content="<mjml><mj-body><mj-text>{{Body}}</mj-text></mj-body></mjml>",
        )
        version = EmailConfigurationVersionFactory.create(
            layout_enabled=True,
            layout_template=layout,
        )
        put_data = {
            "name": "Name after",
            "content": "Content after",
            "subject": "Subject after",
            "release_status": ReleaseStatus.DRAFT,
            "triggers": [],
            "segment_data": {
                "dynamic_segment_names_additive": [],
                "dynamic_segment_names_subtractive": [],
                "static_segment_ids_additive": [],
                "static_segment_ids_subtractive": [],
                "mail_category_ids_additive": [],
            },
            "layout_enabled": False,
        }

        response = self._send_request(version.id, put_data)

        self.assertStatusCode(response, 200)
        version.refresh_from_db()
        self.assertFalse(version.layout_enabled)
        self.assertIsNone(version.layout_template_id)

    def _send_request(self, email_configuration_version_id: str, put_data: dict | None):
        return self.client.put(
            reverse(
                "emailconfigurationversion-detail",
                args=[email_configuration_version_id],
            ),
            data=put_data,
            content_type="application/json",
        )
