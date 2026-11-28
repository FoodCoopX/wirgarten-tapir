import { PlusCircleIcon } from "@heroicons/react/24/outline";
import React, { useEffect, useRef, useState } from "react";
import { Modal } from "react-bootstrap";
import {
  MailCategory,
  ModeEnum,
  SegmentOption,
  TapirmailApi,
} from "tapir-api-client";
import { useAlert } from "../../contexts/alerts";
import { useApi } from "../../hooks/useApi";
import SegmentPickerModal from "../segments/SegmentPickerModal";
import TapirButton from "../TapirButton";
import MailCategoryForm from "./MailCategoryForm";

interface MailCategoryEditModalProps {
  open: boolean;
  onClose: () => void;
  category: MailCategory;
  segmentOptions: SegmentOption[];
}

const MailCategoryEditModal: React.FC<MailCategoryEditModalProps> = ({
  open,
  onClose,
  category,
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

  useEffect(() => {
    setCategoryName(category.name);
    setCategoryMode(category.mode);
    setExternalsEnabled(category.availableForExternalRecipients);
    setSegmentName(category.dynamicSegmentName ?? "");
  }, [category]);

  function onSaveClicked() {
    setLoading(true);

    mailCategoryApi
      .tapirmailApiMailCategoryUpdate({
        id: category.id!,
        mailCategoryRequest: {
          name: categoryName,
          mode: categoryMode,
          availableForExternalRecipients: externalsEnabled,
          dynamicSegmentName: segmentName,
        },
      })
      .then(() => {
        onClose();
      })
      .catch((err) => {
        console.error(err);
        showAlert("Fehler beim Speichern der Kategorie", "danger");
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
            text={loading ? "Loading..." : "Speichern"}
            icon={PlusCircleIcon}
            disabled={loading}
            onClick={() => onSaveClicked()}
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

export default MailCategoryEditModal;
