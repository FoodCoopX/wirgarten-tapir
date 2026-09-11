import React, { ReactNode } from "react";
import ConfirmModal from "./ConfirmModal";

interface ConfirmDeleteModalProps {
  message: ReactNode;
  open: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
  confirmButtonText?: string;
}

const ConfirmDeleteModal: React.FC<ConfirmDeleteModalProps> = ({
  message,
  open,
  onConfirm,
  onCancel,
  loading,
  confirmButtonText,
}) => {
  return (
    <ConfirmModal
      message={message}
      title={"Löschen bestätigen"}
      open={open}
      confirmButtonText={confirmButtonText ?? "Löschen"}
      confirmButtonIcon={"delete"}
      confirmButtonVariant="danger"
      onConfirm={onConfirm}
      onCancel={onCancel}
      loading={loading}
    />
  );
};

export default ConfirmDeleteModal;
