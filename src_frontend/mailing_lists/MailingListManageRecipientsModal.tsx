import React, { useEffect, useRef, useState } from "react";
import { Form, ListGroup, Modal, Table } from "react-bootstrap";
import Select from "react-select";
import { CoopApi, CoreApi, MailingListRecipient, Member } from "../api-client";
import ConfirmDeleteModal from "../components/ConfirmDeleteModal.tsx";
import PlaceholderTableRows from "../components/PlaceholderTableRows.tsx";
import TapirButton from "../components/TapirButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

interface MailingListManageRecipientsModalProps {
  show: boolean;
  onHide: () => void;
  loadData: () => void;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
  listName: string;
}

const MailingListManageRecipientsModal: React.FC<
  MailingListManageRecipientsModalProps
> = ({ show, onHide, loadData, setToastDatas, listName }) => {
  const coreApi = useApi(CoreApi, getCsrfToken());
  const coopApi = useApi(CoopApi, getCsrfToken());
  const [recipients, setRecipients] = useState<MailingListRecipient[]>([]);
  const [loadingRecipients, setLoadingRecipients] = useState(false);
  const [unsubscribeLoading, setUnsubscribeLoading] = useState(false);
  const [recipientSelectedForUnsubscribe, setRecipientSelectedForUnsubscribe] =
    useState<MailingListRecipient>();
  const [changesApplied, setChangesApplied] = useState(false);
  const [externalRecipientAddress, setExternalRecipientAddress] = useState("");
  const [externalRecipientAddLoading, setExternalRecipientAddLoading] =
    useState(false);
  const externalRecipientFormRef = useRef<HTMLFormElement>(null);
  const [membersLoading, setMembersLoading] = useState(true);
  const [allMembers, setAllMembers] = useState<Member[]>([]);
  const [selectedMember, setSelectedMember] = useState<Member>();
  const internalRecipientFormRef = useRef<HTMLFormElement>(null);
  const [internalRecipientAddLoading, setInternalRecipientAddLoading] =
    useState(false);

  useEffect(() => {
    if (!show) {
      return;
    }
    setExternalRecipientAddress("");

    loadRecipients();

    setMembersLoading(true);
    coopApi
      .coopMembersList()
      .then(setAllMembers)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Mitgliederliste",
          setToastDatas,
        ),
      )
      .finally(() => setMembersLoading(false));
  }, [show, listName]);

  function loadRecipients() {
    setLoadingRecipients(true);

    coreApi
      .coreApiMailingListRecipientListList({ listName: listName })
      .then(setRecipients)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Empfänger",
          setToastDatas,
        ),
      )
      .finally(() => setLoadingRecipients(false));
  }

  function onUnsubscribe() {
    if (!recipientSelectedForUnsubscribe) {
      alert("Kein Empfänger ausgewählt");
      return;
    }
    setUnsubscribeLoading(true);

    coreApi
      .coreApiMailingListUnsubscribeCreate({
        mailingListSubscribeExternalRecipientRequestRequest: {
          address: recipientSelectedForUnsubscribe.address,
          listName: listName,
        },
      })
      .then(() => {
        setRecipients(
          recipients.filter(
            (recipient) => recipient !== recipientSelectedForUnsubscribe,
          ),
        );
        setRecipientSelectedForUnsubscribe(undefined);
        setChangesApplied(true);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Abmelden des Empfängers",
          setToastDatas,
        ),
      )
      .finally(() => setUnsubscribeLoading(false));
  }

  function buildMemberOptions() {
    return allMembers.map((member) => {
      return {
        value: member.id,
        label:
          member.firstName + " " + member.lastName + " #" + member.memberNo,
      };
    });
  }

  function onAddExternalRecipient() {
    if (!externalRecipientFormRef.current) {
      return;
    }

    if (!externalRecipientFormRef.current.reportValidity()) {
      return;
    }

    setExternalRecipientAddLoading(true);

    coreApi
      .coreApiMailingListSubscribeExternalCreate({
        mailingListSubscribeExternalRecipientRequestRequest: {
          listName: listName,
          address: externalRecipientAddress,
        },
      })
      .then(loadRecipients)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Anmelden des externes Empfängers",
          setToastDatas,
        ),
      )
      .finally(() => setExternalRecipientAddLoading(false));
  }

  function onAddInternalRecipient() {
    if (!internalRecipientFormRef.current) {
      return;
    }

    if (!internalRecipientFormRef.current.reportValidity()) {
      return;
    }

    setInternalRecipientAddLoading(true);

    coreApi
      .coreApiMailingListSubscribeInternalCreate({
        mailingListSubscribeInternalRecipientRequestRequest: {
          listName: listName,
          memberId: selectedMember!.id!,
        },
      })
      .then(loadRecipients)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Anmelden des internes Empfängers",
          setToastDatas,
        ),
      )
      .finally(() => setInternalRecipientAddLoading(false));
  }

  function buildRecipientsTable() {
    if (loadingRecipients) {
      return (
        <Table striped hover responsive>
          <tbody>
            <PlaceholderTableRows size={"sm"} nbColumns={3} nbRows={10} />
          </tbody>
        </Table>
      );
    }

    if (recipients.length === 0) {
      return "Keine Empfänger";
    }

    return (
      <Table striped hover responsive>
        <thead>
          <tr>
            <th>Adresse</th>
            <th>Bestätigt</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {recipients.map((recipient) => (
            <tr key={recipient.address}>
              <td>
                {recipient.linkToMemberProfile ? (
                  <a href={recipient.linkToMemberProfile}>
                    {recipient.address}
                  </a>
                ) : (
                  recipient.address
                )}
              </td>
              <td>{recipient.userConfirmed ? "Ja" : "Nein"}</td>
              <td>
                <TapirButton
                  variant={"outline-danger"}
                  size={"sm"}
                  icon={"delete"}
                  onClick={() => setRecipientSelectedForUnsubscribe(recipient)}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    );
  }

  return (
    <>
      <Modal
        show={show && !recipientSelectedForUnsubscribe}
        onHide={() => {
          if (changesApplied) {
            loadData();
          }
          onHide();
        }}
        size={"lg"}
      >
        <Modal.Header closeButton={true}>
          <Modal.Title className={"mb-0"}>
            Mailing-List Empfänger verwalten: {listName}
          </Modal.Title>
        </Modal.Header>
        <ListGroup variant="flush">
          <ListGroup.Item>
            <h5 className={"mt-2"}>Bestehende Empfänger</h5>
            {buildRecipientsTable()}
          </ListGroup.Item>
          <ListGroup.Item>
            <h5 className={"mt-2"}>Externer Empfänger hinzufügen</h5>
            <Form
              onSubmit={(event) => {
                event.preventDefault();
                onAddExternalRecipient();
              }}
              ref={externalRecipientFormRef}
            >
              <span className={"d-flex flex-row gap-2"}>
                <Form.Group>
                  <Form.Control
                    value={externalRecipientAddress}
                    onChange={(event) =>
                      setExternalRecipientAddress(event.target.value)
                    }
                    placeholder={"E-Mail Adresse"}
                    type={"email"}
                    required={true}
                  />
                </Form.Group>
                <TapirButton
                  type={"submit"}
                  onClick={onAddExternalRecipient}
                  variant={"primary"}
                  icon={"save"}
                  loading={externalRecipientAddLoading}
                  text={"Hinzufügen"}
                />
              </span>
            </Form>
          </ListGroup.Item>
          <ListGroup.Item>
            <h5 className={"mt-2"}>Mitglieder als Empfänger hinzufügen</h5>
            <Form
              ref={internalRecipientFormRef}
              onSubmit={(event) => {
                event.preventDefault();
                onAddInternalRecipient();
              }}
            >
              <span className={"d-flex flex-row gap-2"}>
                <div style={{ minWidth: "300px" }}>
                  <Select
                    isSearchable={true}
                    options={buildMemberOptions()}
                    onChange={(newValue) => {
                      setSelectedMember(
                        allMembers.find(
                          (member) => member.id === newValue?.value,
                        ),
                      );
                    }}
                    required={true}
                    isLoading={membersLoading}
                  />
                </div>
                <TapirButton
                  type={"submit"}
                  variant={"primary"}
                  icon={"save"}
                  loading={internalRecipientAddLoading}
                  text={"Hinzufügen"}
                />
              </span>
            </Form>
          </ListGroup.Item>
        </ListGroup>
        <Modal.Footer />
      </Modal>
      {recipientSelectedForUnsubscribe && (
        <ConfirmDeleteModal
          message={
            "Bist du sicher das du die Adresse " +
            recipientSelectedForUnsubscribe.address +
            " aus der Liste " +
            listName +
            " abmelden willst?"
          }
          open={true}
          onConfirm={onUnsubscribe}
          onCancel={() => setRecipientSelectedForUnsubscribe(undefined)}
          loading={unsubscribeLoading}
          confirmButtonText={"Abmelden"}
        />
      )}
    </>
  );
};

export default MailingListManageRecipientsModal;
