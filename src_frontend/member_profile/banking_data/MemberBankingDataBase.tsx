import "dayjs/locale/de";
import React, { useState } from "react";
import TapirButton from "../../components/TapirButton.tsx";
import TapirToastContainer from "../../components/TapirToastContainer.tsx";
import { ToastData } from "../../types/ToastData.ts";
import MemberBankingDataModal from "./MemberBankingDataModal.tsx";

interface MemberBankingDataBaseProps {
  memberId: string;
}

const MemberBankingDataBase: React.FC<MemberBankingDataBaseProps> = ({
  memberId,
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
