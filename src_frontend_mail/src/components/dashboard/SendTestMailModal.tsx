import { useEffect, useState } from "react";
import { Button, Form, Modal } from "react-bootstrap";
import {
  EmailConfigurationVersion,
  SegmentOption,
  TapirmailApi,
  TypeEnum,
} from "tapir-api-client";
import { useAlert } from "../../contexts/alerts";
import { useApi } from "../../hooks/useApi";
import EmailInput from "../emailInput";

const SendTestMailModal = ({
  emailConfigurationVersion,
  open,
  onClose,
}: {
  emailConfigurationVersion: EmailConfigurationVersion;
  open: boolean;
  onClose: () => void;
}) => {
  const versionApi = useApi(TapirmailApi);
  const segmentApi = useApi(TapirmailApi);
  const showAlert = useAlert();

  const [staticSegments, setStaticSegments] = useState<SegmentOption[]>([]);
  const [selectedSegment, setSelectedSegment] = useState<string | undefined>(
    undefined,
  );
  const [recipients, setRecipients] = useState<string[]>([]);
  const handleRecipientsChange = (emails: string[]) => {
    setRecipients(emails);
  };

  useEffect(() => {
    segmentApi
      .tapirmailApiSegmentAvailableSegmentsRetrieve()
      .then(({ segments }) => {
        setStaticSegments(
          segments.filter((segment) => segment.type === TypeEnum.Static),
        );
      });
  }, []);

  const handleSendEmail = () => {
    onClose();
    versionApi
      .emailConfigurationVersionSendTestEmail({
        id: emailConfigurationVersion.id!,
        recipientRequest: { recipients: recipients },
      })
      .then(() => {
        showAlert("Test-Email wurde versendet!", "success");
      })
      .catch((err) => {
        console.error(err);
        showAlert("Beim Versenden ist ein Fehler aufgetreten.", "danger");
      });
  };

  const handleAddSegment = () => {
    if (!selectedSegment) return;

    segmentApi
      .tapirmailApiSegmentCombineCreate({
        segmentDataRequest: {
          staticSegmentIdsAdditive: [selectedSegment],
          staticSegmentIdsSubtractive: [],
          dynamicSegmentNamesAdditive: [],
          dynamicSegmentNamesSubtractive: [],
          mailCategoryIdsAdditive: [],
        },
      })
      .then((data) => {
        if (!data.recipients) throw new Error("No recipients returned");

        const newEmails = data.recipients.map((r) => r.email!);
        if (recipients) {
          newEmails.push(...recipients);
        }

        handleRecipientsChange(newEmails);
      })
      .catch((err) => {
        console.error(err);
        showAlert(
          "Beim Auflösen des Segments ist ein Fehler aufgetreten.",
          "danger",
        );
      });
    setRecipients([...recipients, selectedSegment]);
    setSelectedSegment(undefined);
  };

  return (
    <Modal
      show={Boolean(open)}
      onHide={onClose}
      dialogClassName="preview-modal"
      centered={true}
    >
      <Modal.Header closeButton>
        <Modal.Title>Testmail senden</Modal.Title>
      </Modal.Header>
      {emailConfigurationVersion && (
        <Modal.Body>
          Möchtest du die Email&nbsp;
          <strong>{emailConfigurationVersion?.emailConfiguration?.name}</strong>
          &nbsp;als Testmail versenden?
          <br />
          <EmailInput
            initialValue={recipients}
            onEmailListChange={handleRecipientsChange}
          />
          <span style={{ display: "flex", marginTop: "1em" }}>
            <Form.Select
              onChange={(e) => setSelectedSegment(e.target.value)}
              style={{ marginRight: "0.5em" }}
            >
              <option value="">Segment auswählen</option>
              {staticSegments.map((segment) => (
                <option key={segment.id} value={segment.id}>
                  {segment.label}
                </option>
              ))}
            </Form.Select>
            <Button onClick={handleAddSegment} disabled={!selectedSegment}>
              +
            </Button>
          </span>
        </Modal.Body>
      )}
      <Modal.Footer
        style={{ display: "flex", justifyContent: "space-between" }}
      >
        <Button variant="success" onClick={onClose}>
          Abbrechen
        </Button>
        <Button
          variant={recipients.length > 0 ? "primary" : "disabled"}
          onClick={handleSendEmail}
          disabled={recipients.length === 0}
        >
          Email senden
        </Button>
      </Modal.Footer>
    </Modal>
  );
};

export default SendTestMailModal;
