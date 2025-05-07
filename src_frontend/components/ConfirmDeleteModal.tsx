import React, { ReactNode } from "react";
import ConfirmModal from "./ConfirmModal";

interface ConfirmDeleteModalProps {
  message: ReactNode;
  open: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
}

const ConfirmDeleteModal: React.FC<ConfirmDeleteModalProps> = ({
  message,
  open,
  onConfirm,
  onCancel,
  loading,
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
      loading={loading}
    />
  );
};

export default ConfirmDeleteModal;
