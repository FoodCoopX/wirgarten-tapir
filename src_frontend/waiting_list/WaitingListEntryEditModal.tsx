import React, { useState } from "react";
import { useApi } from "../hooks/useApi.ts";
import {
  WaitingListApi,
  WaitingListEntry,
  WaitingListEntryDetails,
} from "../api-client";
import "./waiting_list_card.css";
import { Modal } from "react-bootstrap";
import TapirButton from "../components/TapirButton.tsx";
import ConfirmDeleteModal from "../components/ConfirmDeleteModal.tsx";
import { handleRequestError } from "../utils/handleRequestError.ts";

interface WaitingListEntryEditModalProps {
  csrfToken: string;
  entryDetails: WaitingListEntryDetails;
  show: boolean;
  onClose: () => void;
  reloadEntries: () => void;
}

const WaitingListEntryEditModal: React.FC<WaitingListEntryEditModalProps> = ({
  csrfToken,
  entryDetails,
  show,
  onClose,
  reloadEntries,
}) => {
  const api = useApi(WaitingListApi, csrfToken);
  const [loading, setLoading] = useState(true);
  const [entry, setEntry] = useState<WaitingListEntry>();
  const [showConfirmDeleteModal, setShowConfirmDeleteModal] = useState(false);
  const [deletionLoading, setDeletionLoading] = useState(false);

  function onConfirmDelete() {
    setDeletionLoading(true);
    api
      .waitingListWaitingListEntriesDestroy({ id: entryDetails.id })
      .then(() => reloadEntries())
      .catch(handleRequestError)
      .finally(() => setDeletionLoading(false));
  }

  return (
    <>
      <Modal
        show={show && !showConfirmDeleteModal}
        onHide={onClose}
        centered={true}
      >
        <Modal.Header closeButton>
          <h5 className={"mb-0"}>
            Warteliste-Eintrag bearbeiten: {entryDetails.firstName}{" "}
            {entryDetails.lastName}
          </h5>
        </Modal.Header>
        <Modal.Body>TODO</Modal.Body>
        <Modal.Footer>
          <TapirButton
            variant={"danger"}
            icon={"delete"}
            text={"Löschen"}
            onClick={() => setShowConfirmDeleteModal(true)}
          />
          <TapirButton
            variant={"primary"}
            icon={"save"}
            text={"Speichern"}
            onClick={() => alert("TODO")}
          />
        </Modal.Footer>
      </Modal>
      <ConfirmDeleteModal
        onConfirm={onConfirmDelete}
        message={
          "Möchtest du wirklich der Eintrag von " +
          entryDetails.firstName +
          " " +
          entryDetails.lastName +
          " aus der Warteliste löschen?"
        }
        open={showConfirmDeleteModal}
        onCancel={() => setShowConfirmDeleteModal(false)}
        loading={deletionLoading}
      />
    </>
  );
};

export default WaitingListEntryEditModal;
