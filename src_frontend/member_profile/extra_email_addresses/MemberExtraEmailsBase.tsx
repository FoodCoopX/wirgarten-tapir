import React, { useState } from "react";
import "dayjs/locale/de";
import { ToastData } from "../../types/ToastData.ts";
import TapirButton from "../../components/TapirButton.tsx";
import MemberExtraEmailsModal from "./MemberExtraEmailsModal.tsx";
import TapirToastContainer from "../../components/TapirToastContainer.tsx";

interface MemberExtraEmailsBaseProps {
  memberId: string;
  csrfToken: string;
}

const MemberExtraEmailsBase: React.FC<MemberExtraEmailsBaseProps> = ({
  memberId,
  csrfToken,
}) => {
  const [showModal, setShowModal] = useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  return (
    <>
      <TapirButton
        text={"Zusätzliche Mails"}
        onClick={() => setShowModal(true)}
        icon={"edit"}
        variant={"outline-primary"}
      />
      <MemberExtraEmailsModal
        memberId={memberId}
        csrfToken={csrfToken}
        setToastDatas={setToastDatas}
        show={showModal}
        onHide={() => setShowModal(false)}
      />
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default MemberExtraEmailsBase;
