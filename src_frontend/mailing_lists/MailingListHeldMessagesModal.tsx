import React, { useEffect, useState } from "react";
import { ListGroup, Modal, Spinner } from "react-bootstrap";
import {
  CoreApi,
  MailingListHeldMessage,
  ModerationActionEnum,
} from "../api-client";
import ConfirmModal from "../components/ConfirmModal.tsx";
import TapirHelpButton from "../components/TapirHelpButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import MailingListHeldMessageItem from "./MailingListHeldMessageItem.tsx";

type PendingConfirmation = {
  heldMessage: MailingListHeldMessage;
  moderationAction: ModerationActionEnum;
};

const HELP_TEXT = (
  <>
    <p>
      Diese E-Mails wurden an die Liste geschickt, aber zurückgehalten. Sie
      werden erst an die Empfänger:innen der Liste weitergeleitet, wenn du sie
      freigibst.
    </p>
    <ul className={"mb-0"}>
      <li>
        <strong>Freigeben</strong>: Die E-Mail wird an alle Empfänger:innen der
        Liste weitergeleitet.
      </li>
      <li>
        <strong>Ablehnen</strong>: Die E-Mail wird nicht weitergeleitet. Der
        Absender bekommt eine E-Mail, dass seine Nachricht abgelehnt wurde.
      </li>
      <li>
        <strong>Verwerfen</strong>: Die E-Mail wird nicht weitergeleitet und
        still gelöscht. Der Absender wird nicht informiert.
      </li>
    </ul>
  </>
);

interface MailingListHeldMessagesModalProps {
  show: boolean;
  onHide: () => void;
  loadData: () => void;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
  listName: string;
}

const MailingListHeldMessagesModal: React.FC<
  MailingListHeldMessagesModalProps
> = ({ show, onHide, loadData, setToastDatas, listName }) => {
  const api = useApi(CoreApi, getCsrfToken());
  const [heldMessages, setHeldMessages] = useState<MailingListHeldMessage[]>(
    [],
  );
  const [loading, setLoading] = useState(false);
  const [messageBeingModerated, setMessageBeingModerated] =
    useState<MailingListHeldMessage>();
  const [pendingConfirmation, setPendingConfirmation] =
    useState<PendingConfirmation>();
  const [changesApplied, setChangesApplied] = useState(false);

  useEffect(() => {
    if (!show) {
      return;
    }

    setLoading(true);
    api
      .coreApiMailingListHeldMessagesList({ listName: listName })
      .then(setHeldMessages)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der zurückgehaltenen E-Mails",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }, [show, listName]);

  function onModerate(
    heldMessage: MailingListHeldMessage,
    moderationAction: ModerationActionEnum,
  ) {
    setMessageBeingModerated(heldMessage);

    api
      .coreApiMailingListModerateHeldMessageCreate({
        mailingListModerateHeldMessageRequestRequest: {
          listName: listName,
          requestId: heldMessage.requestId,
          moderationAction: moderationAction,
        },
      })
      .then(() => {
        setHeldMessages(
          heldMessages.filter((message) => message !== heldMessage),
        );
        setPendingConfirmation(undefined);
        setChangesApplied(true);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Moderieren der E-Mail",
          setToastDatas,
        ),
      )
      .finally(() => setMessageBeingModerated(undefined));
  }

  function buildConfirmationMessage(confirmation: PendingConfirmation) {
    if (confirmation.moderationAction === ModerationActionEnum.Reject) {
      return (
        "Bist du sicher, dass du die E-Mail von " +
        confirmation.heldMessage.sender +
        " ablehnen willst? Die E-Mail wird nicht an die Liste weitergeleitet und der Absender wird darüber informiert."
      );
    }

    return (
      "Bist du sicher, dass du die E-Mail von " +
      confirmation.heldMessage.sender +
      " verwerfen willst? Die E-Mail wird nicht an die Liste weitergeleitet und der Absender wird nicht informiert."
    );
  }

  function buildContent() {
    if (loading) {
      return (
        <Modal.Body>
          <Spinner />
        </Modal.Body>
      );
    }

    if (heldMessages.length === 0) {
      return <Modal.Body>Keine E-Mails zur Freigabe</Modal.Body>;
    }

    return (
      <ListGroup variant={"flush"}>
        {heldMessages.map((heldMessage) => (
          <MailingListHeldMessageItem
            key={heldMessage.requestId}
            heldMessage={heldMessage}
            loading={messageBeingModerated === heldMessage}
            disabled={messageBeingModerated !== undefined}
            onAccept={() =>
              onModerate(heldMessage, ModerationActionEnum.Accept)
            }
            onReject={() =>
              setPendingConfirmation({
                heldMessage: heldMessage,
                moderationAction: ModerationActionEnum.Reject,
              })
            }
            onDiscard={() =>
              setPendingConfirmation({
                heldMessage: heldMessage,
                moderationAction: ModerationActionEnum.Discard,
              })
            }
          />
        ))}
      </ListGroup>
    );
  }

  return (
    <>
      <Modal
        centered={true}
        show={show && !pendingConfirmation}
        onHide={() => {
          if (changesApplied) {
            loadData();
          }
          onHide();
        }}
        size={"xl"}
      >
        <Modal.Header closeButton={true}>
          <span className={"d-flex gap-2 align-items-center"}>
            <Modal.Title className={"mb-0"}>
              E-Mails zur Freigabe: {listName}
            </Modal.Title>
            <TapirHelpButton text={HELP_TEXT} />
          </span>
        </Modal.Header>
        {buildContent()}
        <Modal.Footer />
      </Modal>
      {pendingConfirmation && (
        <ConfirmModal
          message={buildConfirmationMessage(pendingConfirmation)}
          title={
            pendingConfirmation.moderationAction === ModerationActionEnum.Reject
              ? "Ablehnen bestätigen"
              : "Verwerfen bestätigen"
          }
          open={true}
          onConfirm={() =>
            onModerate(
              pendingConfirmation.heldMessage,
              pendingConfirmation.moderationAction,
            )
          }
          onCancel={() => setPendingConfirmation(undefined)}
          loading={messageBeingModerated === pendingConfirmation.heldMessage}
          confirmButtonText={
            pendingConfirmation.moderationAction === ModerationActionEnum.Reject
              ? "Ablehnen"
              : "Verwerfen"
          }
          confirmButtonIcon={
            pendingConfirmation.moderationAction === ModerationActionEnum.Reject
              ? "block"
              : "delete"
          }
          confirmButtonVariant={"danger"}
        />
      )}
    </>
  );
};

export default MailingListHeldMessagesModal;
