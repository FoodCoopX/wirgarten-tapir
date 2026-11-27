import "dayjs/locale/de";
import React, { useEffect, useState } from "react";
import { Badge, Form, ListGroup, Modal, Spinner } from "react-bootstrap";
import { v4 as uuidv4 } from "uuid";
import { CoreApi, MemberExtraEmail } from "../../api-client";
import TapirButton from "../../components/TapirButton.tsx";
import { useApi } from "../../hooks/useApi.ts";
import { ToastData } from "../../types/ToastData.ts";
import { addToast } from "../../utils/addToast.ts";
import { formatDateNumeric } from "../../utils/formatDateNumeric.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";

const RECEIVES_DIRECT_MAILS_LABEL =
  "Erhält auch persönliche Mails (Verträge, Abholung, Rundmails an alle Mitglieder)";

interface MemberExtraEmailsModalProps {
  memberId: string;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
  show: boolean;
  onHide: () => void;
}

const MemberExtraEmailsModal: React.FC<MemberExtraEmailsModalProps> = ({
  memberId,
  setToastDatas,
  show,
  onHide,
}) => {
  const api = useApi(CoreApi);
  const [extraEmails, setExtraEmails] = useState<MemberExtraEmail[]>([]);
  const [explanationText, setExplanationText] = useState("");
  const [newAddress, setNewAddress] = useState("");
  const [newFirstName, setNewFirstName] = useState("");
  const [newLastName, setNewLastName] = useState("");
  const [newReceivesDirectMails, setNewReceivesDirectMails] = useState(true);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [sendingLinkId, setSendingLinkId] = useState<string>();
  const [selectedForEdit, setSelectedForEdit] = useState<MemberExtraEmail>();
  const [editFirstName, setEditFirstName] = useState("");
  const [editLastName, setEditLastName] = useState("");
  const [editReceivesDirectMails, setEditReceivesDirectMails] = useState(true);

  useEffect(() => {
    if (!show) return;

    setNewAddress("");
    loadData();
  }, [show]);

  function loadData() {
    setLoading(true);

    api
      .coreApiMemberExtraEmailsRetrieve({ memberId: memberId })
      .then((response) => {
        setExtraEmails(response.extraMails);
        setExplanationText(response.explanationText);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der zusätzlichen Adressen",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }

  function onSave() {
    setSaving(true);

    api
      .coreApiMemberExtraEmailsCreate({
        memberExtraEmailCreateRequestRequest: {
          memberId: memberId,
          extraEmail: newAddress,
          firstName: newFirstName,
          lastName: newLastName,
          receivesDirectMails: newReceivesDirectMails,
        },
      })
      .then(() => setNewAddress(""))
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Speichern einer zusätzlichen Adresse",
          setToastDatas,
        ),
      )
      .finally(() => {
        loadData();
        setSaving(false);
      });
  }

  function onDelete(id: string) {
    setDeleting(true);

    api
      .coreApiMemberExtraEmailsDestroy({ extraEmailId: id })
      .then(loadData)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Löschen einer zusätzlichen Adresse",
          setToastDatas,
        ),
      )
      .finally(() => setDeleting(false));
  }

  function onSendManagementLink(extraEmail: MemberExtraEmail) {
    setSendingLinkId(extraEmail.id);

    api
      .coreApiMemberExtraEmailSendManagementLinkCreate({
        memberExtraEmailSendManagementLinkRequestRequest: {
          extraEmailId: extraEmail.id!,
        },
      })
      .then(() =>
        addToast(
          {
            id: uuidv4(),
            variant: "success",
            title: "Link gesendet",
            message: `${extraEmail.email} hat einen Link zur Verwaltung der Abos bekommen.`,
          },
          setToastDatas,
        ),
      )
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Senden des Links",
          setToastDatas,
        ),
      )
      .finally(() => setSendingLinkId(undefined));
  }

  function onUpdate(extraEmail: MemberExtraEmail) {
    setSaving(true);

    api
      .coreApiMemberExtraEmailsPartialUpdate({
        patchedMemberExtraEmailUpdateRequestRequest: {
          extraEmailId: extraEmail.id,
          firstName: editFirstName,
          lastName: editLastName,
          receivesDirectMails: editReceivesDirectMails,
        },
      })
      .then(loadData)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Bearbeiten einer zusätzlichen Adresse",
          setToastDatas,
        ),
      )
      .finally(() => setSaving(false));
  }

  function getTable() {
    if (loading) {
      return <Spinner />;
    }

    if (extraEmails.length === 0) {
      return <p>Keine zusätzliche Adresse eingetragen</p>;
    }

    return (
      <ListGroup variant={"flush"}>
        {extraEmails.map((extraEmail) => (
          <ListGroup.Item key={extraEmail.id} className={"px-0"}>
            <div className={"d-flex justify-content-between gap-2"}>
              <div className={"fw-bold text-break"}>{extraEmail.email}</div>
              <div>
                <Badge
                  bg={extraEmail.receivesDirectMails ? "primary" : "secondary"}
                >
                  {extraEmail.receivesDirectMails
                    ? "Persönliche Mails"
                    : "Nur Abos"}
                </Badge>
              </div>
            </div>
            {selectedForEdit == extraEmail ? (
              <div className={"d-flex flex-column gap-2 my-2"}>
                <Form.Control
                  placeholder={"Vorname"}
                  aria-label={"Vorname"}
                  value={editFirstName}
                  onChange={(event) => {
                    setEditFirstName(event.target.value);
                  }}
                />
                <Form.Control
                  placeholder={"Nachname"}
                  aria-label={"Nachname"}
                  value={editLastName}
                  onChange={(event) => {
                    setEditLastName(event.target.value);
                  }}
                />
                <Form.Check
                  id={`edit_extra_receives_direct_mails_${extraEmail.id}`}
                  label={RECEIVES_DIRECT_MAILS_LABEL}
                  checked={editReceivesDirectMails}
                  onChange={(event) =>
                    setEditReceivesDirectMails(event.target.checked)
                  }
                />
              </div>
            ) : (
              <div>
                {extraEmail.firstName} {extraEmail.lastName}
              </div>
            )}
            <div
              className={
                "d-flex flex-wrap justify-content-between align-items-center gap-2"
              }
            >
              <small className={"text-muted"}>
                {extraEmail.confirmedOn
                  ? "Bestätigt am " + formatDateNumeric(extraEmail.confirmedOn)
                  : "Nicht bestätigt"}
              </small>
              <div className={"d-flex gap-2"}>
                {extraEmail.confirmedOn && (
                  <TapirButton
                    variant={"outline-secondary"}
                    icon={"send"}
                    text={"Link senden"}
                    size={"sm"}
                    onClick={() => onSendManagementLink(extraEmail)}
                    loading={sendingLinkId === extraEmail.id}
                  />
                )}
                {selectedForEdit == extraEmail ? (
                  <TapirButton
                    variant={"primary"}
                    icon={"save"}
                    size={"sm"}
                    loading={saving}
                    onClick={() => onUpdate(extraEmail)}
                  />
                ) : (
                  <TapirButton
                    variant={"outline-primary"}
                    icon={"edit"}
                    size={"sm"}
                    onClick={() => {
                      setEditFirstName(extraEmail.firstName);
                      setEditLastName(extraEmail.lastName);
                      setEditReceivesDirectMails(
                        extraEmail.receivesDirectMails ?? true,
                      );
                      setSelectedForEdit(extraEmail);
                    }}
                    loading={saving}
                  />
                )}
                <TapirButton
                  variant={"outline-danger"}
                  icon={"delete"}
                  size={"sm"}
                  onClick={() => onDelete(extraEmail.id!)}
                  loading={deleting}
                />
              </div>
            </div>
          </ListGroup.Item>
        ))}
      </ListGroup>
    );
  }

  return (
    <Modal show={show} onHide={onHide} centered>
      <Modal.Header closeButton>
        <h5 className={"mb-0"}>Zusätzliche Mail-Adressen verwalten</h5>
      </Modal.Header>
      <ListGroup>
        <>
          <ListGroup.Item>
            <div dangerouslySetInnerHTML={{ __html: explanationText }}></div>
          </ListGroup.Item>
          <ListGroup.Item>{getTable()}</ListGroup.Item>
          <ListGroup.Item>
            <Form>
              <h5>Zusätzliche Adresse hinzufügen</h5>
              <div className={"d-flex flex-column gap-2"}>
                <Form.Group controlId={"new_extra_email"}>
                  <Form.Label>E-Mail</Form.Label>
                  <Form.Control
                    placeholder={"E-Mail"}
                    type={"email"}
                    value={newAddress}
                    onChange={(event) => setNewAddress(event.target.value)}
                  />
                </Form.Group>
                <Form.Group controlId={"new_extra_first_name"}>
                  <Form.Label>Vorname</Form.Label>
                  <Form.Control
                    placeholder={"Vorname"}
                    value={newFirstName}
                    onChange={(event) => setNewFirstName(event.target.value)}
                  />
                </Form.Group>
                <Form.Group controlId={"new_extra_last_name"}>
                  <Form.Label>Nachname</Form.Label>
                  <Form.Control
                    placeholder={"Nachname"}
                    value={newLastName}
                    onChange={(event) => setNewLastName(event.target.value)}
                  />
                </Form.Group>
                <Form.Check
                  id={"new_extra_receives_direct_mails"}
                  label={RECEIVES_DIRECT_MAILS_LABEL}
                  checked={newReceivesDirectMails}
                  onChange={(event) =>
                    setNewReceivesDirectMails(event.target.checked)
                  }
                />
                <TapirButton
                  variant={"primary"}
                  icon={"add_circle"}
                  text={"Hinzufügen"}
                  className={"align-self-end"}
                  onClick={onSave}
                  loading={saving}
                />
              </div>
            </Form>
          </ListGroup.Item>
        </>
      </ListGroup>
    </Modal>
  );
};

export default MemberExtraEmailsModal;
