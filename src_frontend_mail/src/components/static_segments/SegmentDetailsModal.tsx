import { PlusCircleIcon, TrashIcon } from "@heroicons/react/24/outline";
import React, { useEffect, useState } from "react";
import { Modal, Table } from "react-bootstrap";
import {
  StaticSegment,
  StaticSegmentRecipient,
  TapirmailApi,
} from "tapir-api-client";
import { useAlert } from "../../contexts/alerts";
import { useApi } from "../../hooks/useApi";
import ConfirmDeleteModal from "../ConfirmDeleteModal";
import TapirButton from "../TapirButton";
import CreateRecipientModal from "./CreateRecipientModal";

interface SegmentDetailsModalProps {
  open: boolean;
  onClose: () => void;
  segment: StaticSegment;
}

const SegmentDetailsModal: React.FC<SegmentDetailsModalProps> = ({
  open,
  onClose,
  segment,
}) => {
  const [createRecipientModalOpen, setCreateRecipientModalOpen] =
    useState(false);
  const staticSegmentApi = useApi(TapirmailApi);
  const recipientApi = useApi(TapirmailApi);
  const showAlert = useAlert();
  const [recipients, setRecipients] = useState<StaticSegmentRecipient[]>([]);
  const [recipientToDelete, setRecipientToDelete] =
    useState<StaticSegmentRecipient>();

  useEffect(() => {
    if (!open) return;

    loadData();
  }, [open, segment]);

  function loadData() {
    if (!segment.id) return;

    staticSegmentApi
      .tapirmailApiStaticSegmentRetrieve({ id: segment.id })
      .then((updatedSegment) => {
        setRecipients(updatedSegment.recipients);
      });
  }

  function buildRecipientToDeleteString() {
    if (!recipientToDelete) return "";

    return [
      recipientToDelete.firstName,
      recipientToDelete.lastName,
      recipientToDelete.email,
    ].join(" ");
  }

  function onConfirmDeleteRecipient() {
    if (!recipientToDelete) return;

    recipientApi
      .tapirmailApiStaticSegmentRecipientDestroy({ id: recipientToDelete.id! })
      .then(() => {
        showAlert(
          "Empfänger gelöscht " + buildRecipientToDeleteString(),
          "success",
        );
      })
      .catch(() => {
        showAlert(
          "Fehler beim löschen des Empfängers " +
            buildRecipientToDeleteString(),
          "danger",
        );
      })
      .finally(() => {
        setRecipientToDelete(undefined);
        loadData();
      });
  }

  return (
    <>
      <Modal
        show={open && !createRecipientModalOpen && !recipientToDelete}
        onHide={onClose}
        centered={true}
      >
        <Modal.Header closeButton>
          <Modal.Title>Segment details: {segment.name}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Table striped hover style={{ margin: "0" }}>
            <thead>
              <tr>
                <th>Name</th>
                <th>Adresse</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {(recipients || segment.recipients).map(
                (recipient: StaticSegmentRecipient) => (
                  <tr key={recipient.id}>
                    <td>
                      {recipient.firstName} {recipient.lastName}
                    </td>
                    <td>{recipient.email}</td>
                    <td>
                      <TapirButton
                        variant={"outline-danger"}
                        icon={TrashIcon}
                        size={"sm"}
                        onClick={() => setRecipientToDelete(recipient)}
                      />
                    </td>
                  </tr>
                ),
              )}
            </tbody>
          </Table>
        </Modal.Body>
        <Modal.Footer className="d-flex justify-content-end align-items-center">
          <TapirButton
            variant={"outline-primary"}
            text={"Empfänger hinzufügen"}
            icon={PlusCircleIcon}
            onClick={() => setCreateRecipientModalOpen(true)}
          />
        </Modal.Footer>
      </Modal>
      <CreateRecipientModal
        open={createRecipientModalOpen}
        onClose={() => {
          setCreateRecipientModalOpen(false);
          loadData();
        }}
        segment={segment}
      />
      <ConfirmDeleteModal
        open={!!recipientToDelete}
        message={
          "Empfänger löschen bestätigen: " + buildRecipientToDeleteString()
        }
        onConfirm={() => onConfirmDeleteRecipient()}
        onCancel={() => setRecipientToDelete(undefined)}
      />
    </>
  );
};

export default SegmentDetailsModal;
