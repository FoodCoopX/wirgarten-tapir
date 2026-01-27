import React, { useState } from "react";
import "dayjs/locale/de";
import TapirButton from "../../components/TapirButton.tsx";
import MemberMailCategoryModal from "./MemberMailCategoryModal.tsx";

interface MemberMailCategoryBaseProps {
  memberId: string;
  csrfToken: string;
}

const MemberMailCategoryBase: React.FC<MemberMailCategoryBaseProps> = ({
  memberId,
  csrfToken,
}) => {
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <>
      <TapirButton
        variant={"outline-primary"}
        text={"Mail-Abos verwalten"}
        icon={"mail"}
        onClick={() => setModalOpen(true)}
      />
      <MemberMailCategoryModal
        memberId={memberId}
        csrfToken={csrfToken}
        open={modalOpen}
        onClose={() => setModalOpen(false)}
      />
    </>
  );
};

export default MemberMailCategoryBase;
