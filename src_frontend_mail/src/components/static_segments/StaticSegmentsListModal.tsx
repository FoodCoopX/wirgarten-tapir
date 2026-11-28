import { PlusCircleIcon, TrashIcon } from "@heroicons/react/24/outline";
import React, { useEffect, useState } from "react";
import { Modal, Table } from "react-bootstrap";
import { StaticSegment, TapirmailApi } from "tapir-api-client";
import { useAlert } from "../../contexts/alerts";
import { useApi } from "../../hooks/useApi";
import ConfirmDeleteModal from "../ConfirmDeleteModal";
import TapirButton from "../TapirButton";
import Loading from "./../loading";
import SegmentDetailsModal from "./SegmentDetailsModal";
import StaticSegmentsCreateModal from "./StaticSegmentsCreateModal";

interface StaticSegmentsListModalProps {
  open: boolean;
  onClose: () => void;
}

const StaticSegmentsListModal: React.FC<StaticSegmentsListModalProps> = ({
  open,
  onClose,
}) => {
  const [staticSegments, setStaticSegments] = useState<StaticSegment[]>([]);
  const [loading, setLoading] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [selectedSegment, setSelectedSegment] = useState<StaticSegment>();
  const [segmentToDelete, setSegmentToDelete] = useState<StaticSegment>();
  const staticSegmentApi = useApi(TapirmailApi);
  const showAlert = useAlert();

  useEffect(() => {
    if (open) {
      loadData();
    }
  }, [open]);

  function loadData() {
    if (!open) return;

    setLoading(true);

    staticSegmentApi
      .tapirmailApiStaticSegmentList()
      .then(setStaticSegments)
      .catch((error) => {
        console.error(error);
        showAlert("Fehler beim Laden der Segmente", "danger");
      })
      .finally(() => setLoading(false));
  }

  function onConfirmDeleteSegment() {
    if (!segmentToDelete) return;

    staticSegmentApi
      .tapirmailApiStaticSegmentDestroy({ id: segmentToDelete.id! })
      .then(() => {
        showAlert("Segment gelöscht " + segmentToDelete.name, "success");
      })
      .catch(() => {
        showAlert(
          "Fehler beim löschen des Segments " + segmentToDelete.name,
          "danger",
        );
      })
      .finally(() => {
        setSegmentToDelete(undefined);
        loadData();
      });
  }

  return (
    <>
      <Modal
        show={open && !createModalOpen && !selectedSegment && !segmentToDelete}
        onHide={onClose}
        size={"lg"}
        centered={true}
      >
        <Modal.Header closeButton>
          <Modal.Title>Statische Segmente</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {loading ? (
            <Loading />
          ) : (
            <Table striped hover style={{ margin: "0" }}>
              <thead>
                <tr>
                  <th>Segment-Name</th>
                  <th>Anzahl an Adressen</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {staticSegments.map((segment: StaticSegment) => (
                  <tr
                    key={segment.id}
                    onClick={() => {
                      setSelectedSegment(segment);
                    }}
                    style={{ cursor: "pointer" }}
                  >
                    <td>{segment.name}</td>
                    <td>{segment.recipients.length}</td>
                    <td>
                      {segment.belongsToACategory ? (
                        "Segmente die aus Kategorien stemmen können nicht gelöscht werden"
                      ) : (
                        <TapirButton
                          variant={"outline-danger"}
                          icon={TrashIcon}
                          size={"sm"}
                          onClick={(event) => {
                            event.stopPropagation();
                            setSegmentToDelete(segment);
                          }}
                          disabled={segment.belongsToACategory}
                        />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Modal.Body>
        <Modal.Footer className="d-flex justify-content-end align-items-center">
          <TapirButton
            variant={"outline-primary"}
            text={"Segment hinzufügen"}
            icon={PlusCircleIcon}
            onClick={() => setCreateModalOpen(true)}
          />
        </Modal.Footer>
      </Modal>
      <StaticSegmentsCreateModal
        open={createModalOpen}
        onClose={() => {
          setCreateModalOpen(false);
          loadData();
        }}
      />
      {selectedSegment && (
        <SegmentDetailsModal
          open={!!selectedSegment}
          onClose={() => {
            setSelectedSegment(undefined);
            loadData();
          }}
          segment={selectedSegment}
        />
      )}
      <ConfirmDeleteModal
        open={!!segmentToDelete}
        message={"Segment löschen bestätigen: " + segmentToDelete?.name}
        onConfirm={() => onConfirmDeleteSegment()}
        onCancel={() => setSegmentToDelete(undefined)}
      />
    </>
  );
};

export default StaticSegmentsListModal;
