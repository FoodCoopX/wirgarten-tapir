import {
  DocumentDuplicateIcon,
  PencilIcon,
  PlusCircleIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import React, { useEffect, useState } from "react";
import { Modal, Table } from "react-bootstrap";
import {
  MailCategory,
  SegmentOption,
  TapirmailApi,
  TypeEnum,
} from "tapir-api-client";
import { useAlert } from "../../contexts/alerts";
import { useApi } from "../../hooks/useApi";
import { getModeDisplay } from "../../utils/getModeDisplay";
import ConfirmDeleteModal from "../ConfirmDeleteModal";
import TapirButton from "../TapirButton";
import Loading from "./../loading";
import MailCategoriesCreateModal from "./MailCategoryCreateModal";
import MailCategoryEditModal from "./MailCategoryEditModal";

interface MailCategoryListModalProps {
  open: boolean;
  onClose: () => void;
}

const MailCategoryListModal: React.FC<MailCategoryListModalProps> = ({
  open,
  onClose,
}) => {
  const [mailCategories, setMailCategories] = useState<MailCategory[]>([]);
  const [loading, setLoading] = useState(false);
  const [categorySelectedForDeletion, setCategorySelectedForDeletion] =
    useState<MailCategory>();
  const [categorySelectedForEdition, setCategorySelectedForEdition] =
    useState<MailCategory>();
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [segmentOptions, setSegmentOptions] = useState<SegmentOption[]>([]);
  const mailCategoryApi = useApi(TapirmailApi);
  const segmentApi = useApi(TapirmailApi);
  const showAlert = useAlert();

  useEffect(() => {
    if (open) {
      loadData();
    }
  }, [open]);

  function loadData() {
    if (!open) return;

    setLoading(true);

    Promise.all([
      mailCategoryApi.tapirmailApiMailCategoryList(),
      segmentApi.tapirmailApiSegmentAvailableSegmentsRetrieve(),
    ])
      .then(([mailCategories, availableSegments]) => {
        setMailCategories(mailCategories);
        setSegmentOptions(
          availableSegments.segments.filter(
            (segment) => segment.type === TypeEnum.Dynamic,
          ),
        );
      })
      .catch((error) => {
        console.error(error);
        showAlert("Fehler beim Laden der Mail-Kategorien", "danger");
      })
      .finally(() => setLoading(false));
  }

  function onDelete() {
    if (categorySelectedForDeletion === undefined) {
      alert("Keine Kategorie ausgewählt");
      return;
    }

    setLoading(true);
    mailCategoryApi
      .tapirmailApiMailCategoryDestroy({
        id: categorySelectedForDeletion.id!,
      })
      .catch((error) => {
        console.error(error);
        showAlert("Fehler beim Laden der Mail-Kategorien", "danger");
      })
      .finally(() => {
        loadData();
      });
  }

  return (
    <>
      <Modal
        show={
          open &&
          !createModalOpen &&
          !categorySelectedForDeletion &&
          !categorySelectedForEdition
        }
        onHide={onClose}
        size={"xl"}
        fullscreen={"xl-down"}
        centered={true}
      >
        <Modal.Header closeButton>
          <Modal.Title>Mail-Kategorien</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {loading ? (
            <Loading />
          ) : (
            <Table striped hover style={{ margin: "0" }}>
              <thead>
                <tr>
                  <th>Kategorie-Name</th>
                  <th>Modus für Mitglieder</th>
                  <th>Für Externe sichtbar</th>
                  <th>Anzahl an Empfänger*innen</th>
                  <th>Basis-Segment</th>
                  <th>URL zu Intergration in externe Seiten</th>
                  <th>Aktionen</th>
                </tr>
              </thead>
              <tbody>
                {mailCategories.length === 0 && (
                  <tr>
                    <td colSpan={7}>Noch keine Kategorien</td>
                  </tr>
                )}
                {mailCategories.map((category: MailCategory) => (
                  <tr key={category.id}>
                    <td>{category.name}</td>
                    <td>{getModeDisplay(category.mode, false)}</td>
                    <td>
                      {category.availableForExternalRecipients ? "Ja" : "Nein"}
                    </td>
                    <td>{category.nbRecipients}</td>
                    <td>
                      {category.dynamicSegmentName
                        ? category.dynamicSegmentName
                        : "Kein"}
                    </td>
                    <td>
                      {category.availableForExternalRecipients && (
                        <a href={category.registrationFormLink}>
                          {category.registrationFormLink}
                        </a>
                      )}
                    </td>
                    <td>
                      <div className={"d-flex flex-row gap-2"}>
                        {category.availableForExternalRecipients && (
                          <TapirButton
                            variant={"outline-primary"}
                            icon={DocumentDuplicateIcon}
                            size={"sm"}
                            onClick={() => {
                              navigator.clipboard.writeText(
                                category.registrationFormLink,
                              );
                              showAlert("URL kopiert", "primary");
                            }}
                          />
                        )}
                        <TapirButton
                          variant={"outline-primary"}
                          icon={PencilIcon}
                          size={"sm"}
                          onClick={() => {
                            setCategorySelectedForEdition(category);
                          }}
                        />
                        <TapirButton
                          variant={"outline-danger"}
                          icon={TrashIcon}
                          size={"sm"}
                          onClick={() => {
                            setCategorySelectedForDeletion(category);
                          }}
                        />
                      </div>
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
            text={"Kategorie hinzufügen"}
            icon={PlusCircleIcon}
            onClick={() => setCreateModalOpen(true)}
          />
        </Modal.Footer>
      </Modal>
      <MailCategoriesCreateModal
        open={createModalOpen}
        onClose={() => {
          setCreateModalOpen(false);
          loadData();
        }}
        segmentOptions={segmentOptions}
      />
      <ConfirmDeleteModal
        message={
          "Kategorie löschen bestätigen: " + categorySelectedForDeletion?.name
        }
        open={categorySelectedForDeletion !== undefined}
        onConfirm={() => {
          onDelete();
          setCategorySelectedForDeletion(undefined);
        }}
        onCancel={() => setCategorySelectedForDeletion(undefined)}
      />
      {categorySelectedForEdition && (
        <MailCategoryEditModal
          open={true}
          onClose={() => {
            setCategorySelectedForEdition(undefined);
            loadData();
          }}
          category={categorySelectedForEdition}
          segmentOptions={segmentOptions}
        />
      )}
    </>
  );
};

export default MailCategoryListModal;
