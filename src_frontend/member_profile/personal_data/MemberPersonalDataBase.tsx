import React, { useState } from "react";
import "dayjs/locale/de";
import TapirToastContainer from "../../components/TapirToastContainer.tsx";
import { ToastData } from "../../types/ToastData.ts";
import TapirButton from "../../components/TapirButton.tsx";
import MemberPersonalDataModal from "./MemberPersonalDataModal.tsx";

interface MemberPersonalDataBaseProps {
  memberId: string;
  csrfToken: string;
}

const MemberPersonalDataBase: React.FC<MemberPersonalDataBaseProps> = ({
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
      <MemberPersonalDataModal
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

export default MemberPersonalDataBase;
