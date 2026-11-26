import { PlusCircleIcon } from "@heroicons/react/24/outline";
import React, { useEffect, useRef, useState } from "react";
import { Modal } from "react-bootstrap";
import { ModeEnum, SegmentOption, TapirmailApi } from "tapir-api-client";
import { useAlert } from "../../contexts/alerts";
import { useApi } from "../../hooks/useApi";
import SegmentPickerModal from "../segments/SegmentPickerModal";
import TapirButton from "../TapirButton";
import MailCategoryForm from "./MailCategoryForm";

interface MailCategoriesCreateModalProps {
  open: boolean;
  onClose: () => void;
  segmentOptions: SegmentOption[];
}

const MailCategoriesCreateModal: React.FC<MailCategoriesCreateModalProps> = ({
  open,
  onClose,
  segmentOptions,
}) => {
  const [loading, setLoading] = useState(false);
  const mailCategoryApi = useApi(TapirmailApi);
  const showAlert = useAlert();
  const [categoryName, setCategoryName] = useState("");
  const [categoryMode, setCategoryMode] = useState<ModeEnum>(
    ModeEnum.OptionalDefaultOn,
  );
  const [externalsEnabled, setExternalsEnabled] = useState(false);
  const [segmentName, setSegmentName] = useState("");
  const [segmentPickerOpen, setSegmentPickerOpen] = useState(false);
  const nameRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (open) {
      nameRef.current?.focus();
    }
  }, [open]);

  function onCreateClicked() {
    setLoading(true);

    mailCategoryApi
      .tapirmailApiMailCategoryCreate({
        mailCategoryRequest: {
          name: categoryName,
          mode: categoryMode,
          availableForExternalRecipients: externalsEnabled,
          dynamicSegmentName: segmentName,
        },
      })
      .then(() => {
        onClose();
        setCategoryName("");
      })
      .catch(async (err) => {
        console.error(err);
        showAlert(
          "Fehler beim erzeugen der Kategorie: " +
            JSON.stringify(await err.response.json()),
          "danger",
        );
      })
      .finally(() => setLoading(false));
  }

  return (
    <>
      <Modal
        show={open && !segmentPickerOpen}
        onHide={onClose}
        size={"lg"}
        centered={true}
      >
        <Modal.Header closeButton>
          <Modal.Title>Mail Kategorie erzeugen</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <MailCategoryForm
            open={open}
            categoryName={categoryName}
            setCategoryName={setCategoryName}
            categoryMode={categoryMode}
            setCategoryMode={setCategoryMode}
            segmentName={segmentName}
            setSegmentName={setSegmentName}
            externalsEnabled={externalsEnabled}
            setExternalsEnabled={setExternalsEnabled}
            segmentOptions={segmentOptions}
            onOpenSegmentPicker={() => setSegmentPickerOpen(true)}
          />
        </Modal.Body>
        <Modal.Footer className="d-flex justify-content-end align-items-center">
          <TapirButton
            variant={"primary"}
            text={loading ? "Loading..." : "Erzeugen"}
            icon={PlusCircleIcon}
            disabled={loading}
            onClick={() => onCreateClicked()}
          />
        </Modal.Footer>
      </Modal>
      <SegmentPickerModal
        show={open && segmentPickerOpen}
        onHide={() => setSegmentPickerOpen(false)}
        options={segmentOptions}
        onAdd={(option) => setSegmentName(option.id)}
        title="Segment auswählen"
      />
    </>
  );
};

export default MailCategoriesCreateModal;
