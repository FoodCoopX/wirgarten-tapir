import "dayjs/locale/de";
import React, { useState } from "react";
import TapirButton from "../../components/TapirButton.tsx";
import TapirToastContainer from "../../components/TapirToastContainer.tsx";
import { ToastData } from "../../types/ToastData.ts";
import MemberBankingDataModal from "./MemberBankingDataModal.tsx";

interface MemberBankingDataBaseProps {
  memberId: string;
  sepaConsentLabel: string;
  csrfToken: string;
}

const MemberBankingDataBase: React.FC<MemberBankingDataBaseProps> = ({
  memberId,
  sepaConsentLabel,
  csrfToken,
}) => {
  const [showModal, setShowModal] = useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  return (
    <>
      <TapirButton
        variant={"outline-primary"}
        icon={"edit"}
        onClick={() => setShowModal(true)}
        text={"Bearbeiten"}
      />
      <MemberBankingDataModal
        memberId={memberId}
        sepaConsentLabel={sepaConsentLabel}
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

export default MemberBankingDataBase;
