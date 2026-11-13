import React, { ReactNode, useState } from "react";
import { Alert, Modal, Table } from "react-bootstrap";
import {
  AccountsApi,
  SendVerificationEmailsResponse,
  UnverifiedMembersResponse,
} from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

interface SendVerificationEmailsButtonProps {
  csrfToken: string;
}

type Step = "list" | "confirm" | "sent";

const SendVerificationEmailsButton: React.FC<
  SendVerificationEmailsButtonProps
> = ({ csrfToken }) => {
  const accountsApi = useApi(AccountsApi, csrfToken);
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<Step>("list");
  const [unverifiedMembers, setUnverifiedMembers] =
    useState<UnverifiedMembersResponse>();
  const [sendResult, setSendResult] =
    useState<SendVerificationEmailsResponse>();
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  const members = unverifiedMembers?.members ?? [];
  const sendingInProgress = unverifiedMembers?.sendingInProgress ?? false;

  function openModal() {
    setShowModal(true);
    setStep("list");
    setLoading(true);
    setUnverifiedMembers(undefined);
    setSendResult(undefined);
    accountsApi
      .accountsApiUnverifiedMembersRetrieve()
      .then(setUnverifiedMembers)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der nicht verifizierten Mitglieder",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }

  function send() {
    setLoading(true);
    accountsApi
      .accountsApiUnverifiedMembersCreate()
      .then((result) => {
        setSendResult(result);
        setStep("sent");
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Versenden der Verifizierungs-Emails",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }

  function formatDuration(seconds: number) {
    if (seconds < 60) {
      return "weniger als eine Minute";
    }
    const minutes = Math.ceil(seconds / 60);
    return minutes === 1 ? "ca. eine Minute" : `ca. ${minutes} Minuten`;
  }

  function buildListMessage() {
    if (loading) {
      return "Laden...";
    }
    if (sendingInProgress) {
      return (
        <Alert variant={"info"} className={"mb-0"}>
          Es läuft gerade ein Versand der Verifizierungs-Emails. Du kannst einen
          neuen Versand starten, sobald du die Zusammenfassung per Mail bekommen
          hast.
        </Alert>
      );
    }
    if (members.length === 0) {
      return "Alle aktiven Mitglieder haben ihre E-Mail-Adresse bereits verifiziert.";
    }
    const membersWithoutAccount = members.filter(
      (member) => !member.hasKeycloakAccount,
    ).length;
    return (
      <>
        <p>
          Alle {members.length} aktiven Mitglieder, deren E-Mail-Adresse nicht
          verifiziert ist, erhalten eine E-Mail mit einem Verifizierungslink.
        </p>
        {membersWithoutAccount > 0 && (
          <Alert variant={"warning"}>
            {membersWithoutAccount} dieser Mitglieder haben noch kein
            Benutzerkonto. Für sie wird jetzt ein Konto angelegt, und sie
            erhalten die Mail zum ersten Mal.
          </Alert>
        )}
        <div style={{ maxHeight: "50vh", overflowY: "auto" }}>
          <Table striped size={"sm"} className={"mb-0"}>
            <thead className={"sticky-top"}>
              <tr>
                <th>#</th>
                <th>Name</th>
                <th>E-Mail-Adresse</th>
                <th>Benutzerkonto</th>
              </tr>
            </thead>
            <tbody>
              {members.map((member) => (
                <tr key={member.id}>
                  <td>
                    <a
                      href={member.profileUrl}
                      target={"_blank"}
                      rel={"noreferrer"}
                    >
                      {member.memberNo ?? "-"}
                    </a>
                  </td>
                  <td>
                    {member.firstName} {member.lastName}
                  </td>
                  <td>{member.email}</td>
                  <td>{member.hasKeycloakAccount ? "Ja" : "Nein, neu"}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      </>
    );
  }

  function buildConfirmMessage() {
    const membersWithoutAccount = members.filter(
      (member) => !member.hasKeycloakAccount,
    ).length;
    return (
      <>
        <p>
          Bist du sicher, dass du die Verifizierungs-Email jetzt an{" "}
          {members.length} Mitglieder senden möchtest?
          {membersWithoutAccount > 0 &&
            ` Für ${membersWithoutAccount} von ihnen wird dabei ein neues Benutzerkonto angelegt.`}
        </p>
        <p className={"mb-0"}>
          Die Mails werden nacheinander verschickt, der Versand dauert{" "}
          {formatDuration(unverifiedMembers?.estimatedDurationSeconds ?? 0)}.
          Einmal gestartet, kann der Versand nicht abgebrochen werden.
        </p>
      </>
    );
  }

  function buildSentMessage(result: SendVerificationEmailsResponse) {
    return (
      <>
        <p>
          Die Verifizierungs-Email wird jetzt im Hintergrund an{" "}
          {result.memberCount} Mitglieder versendet. Um die Mailserver nicht zu
          überlasten, werden die Mails nacheinander verschickt. Das dauert{" "}
          {formatDuration(result.estimatedDurationSeconds)}.
        </p>
        <p className={"mb-0"}>
          Sobald der Versand abgeschlossen ist, bekommst du eine Zusammenfassung
          per Mail, inklusive der Mitglieder, an die die Mail nicht gesendet
          werden konnte. Du kannst dieses Fenster schließen.
        </p>
      </>
    );
  }

  function buildCloseButton() {
    return (
      <TapirButton
        variant={"outline-secondary"}
        text={"Schließen"}
        icon={"close"}
        onClick={() => setShowModal(false)}
        disabled={loading}
        style={{ marginLeft: "auto" }}
      />
    );
  }

  let title: string;
  let body: ReactNode;
  let footer: ReactNode;
  if (step === "sent" && sendResult) {
    title = "Versand gestartet";
    body = buildSentMessage(sendResult);
    footer = buildCloseButton();
  } else if (step === "confirm") {
    title = "Versand bestätigen";
    body = buildConfirmMessage();
    footer = (
      <>
        <TapirButton
          variant={"outline-secondary"}
          text={"Zurück"}
          icon={"arrow_back"}
          onClick={() => setStep("list")}
          disabled={loading}
        />
        <TapirButton
          variant={"primary"}
          text={"Ja, jetzt senden"}
          icon={"send"}
          onClick={send}
          loading={loading}
        />
      </>
    );
  } else {
    title = "Verifizierungs-Emails an alle senden";
    body = buildListMessage();
    footer =
      loading || sendingInProgress || members.length === 0 ? (
        buildCloseButton()
      ) : (
        <>
          <TapirButton
            variant={"outline-secondary"}
            text={"Abbrechen"}
            icon={"close"}
            onClick={() => setShowModal(false)}
          />
          <TapirButton
            variant={"outline-primary"}
            text={`An ${members.length} Mitglieder senden`}
            icon={"arrow_forward"}
            onClick={() => setStep("confirm")}
          />
        </>
      );
  }

  return (
    <>
      <TapirButton
        icon={"forward_to_inbox"}
        variant={"outline-primary"}
        onClick={openModal}
        tooltip={
          "Verifizierungs-Email an alle nicht verifizierten Mitglieder senden"
        }
        tootlipPosition={"bottom"}
      />
      <Modal
        show={showModal}
        onHide={() => setShowModal(false)}
        centered={true}
        size={"lg"}
      >
        <Modal.Header closeButton>
          <Modal.Title>
            <h5>{title}</h5>
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>{body}</Modal.Body>
        <Modal.Footer
          style={{ display: "flex", justifyContent: "space-between" }}
        >
          {footer}
        </Modal.Footer>
      </Modal>
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default SendVerificationEmailsButton;
