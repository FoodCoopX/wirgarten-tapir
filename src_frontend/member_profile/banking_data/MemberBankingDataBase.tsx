import React, { useState } from "react";
import "dayjs/locale/de";
import TapirToastContainer from "../../components/TapirToastContainer.tsx";
import { ToastData } from "../../types/ToastData.ts";
import TapirButton from "../../components/TapirButton.tsx";
import MemberBankingDataModal from "./MemberBankingDataModal.tsx";

interface MemberBankingDataBaseProps {
  memberId: string;
  csrfToken: string;
}

const MemberBankingDataBase: React.FC<MemberBankingDataBaseProps> = ({
  memberId,
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
