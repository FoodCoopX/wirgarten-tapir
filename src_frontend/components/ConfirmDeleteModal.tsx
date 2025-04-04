import React, { ReactNode } from "react";
import ConfirmModal from "./ConfirmModal";

interface ConfirmDeleteModalProps {
  message: ReactNode;
  open: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

const ConfirmDeleteModal: React.FC<ConfirmDeleteModalProps> = ({
  message,
  open,
  onConfirm,
  onCancel,
}) => {
  return (
    <ConfirmModal
      message={message}
      title={"Löschen bestätigen"}
      open={open}
      confirmButtonText={"Löschen"}
      confirmButtonIcon={"delete"}
      confirmButtonVariant="danger"
      onConfirm={onConfirm}
      onCancel={onCancel}
    />
  );
};

export default ConfirmDeleteModal;
