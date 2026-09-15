import React, { useEffect, useState } from "react";
import { MemberNeedingBankingData, PaymentsApi } from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import MembersNeedingBankingDataModal from "./MembersNeedingBankingDataModal.tsx";

interface MembersNeedingBankingDataButtonProps {
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

const MembersNeedingBankingDataButton: React.FC<
  MembersNeedingBankingDataButtonProps
> = ({ setToastDatas }) => {
  const api = useApi(PaymentsApi, "unused");
  const [members, setMembers] = useState<
    MemberNeedingBankingData[] | undefined
  >(undefined);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    api
      .paymentsApiMembersNeedingBankingDataList()
      .then(setMembers)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Benutzer:innen mit unvollständigen Bankdaten",
          setToastDatas,
        ),
      );
  }, []);

  if (members === undefined) {
    return null;
  }

  const count = members.length;

  return (
    <>
      <TapirButton
        variant={count > 0 ? "outline-danger" : "outline-success"}
        text={
          count > 0
            ? `${count} Benutzer:in mit unvollständigen Bankdaten`
            : "alle Bankdaten vollständig"
        }
        icon={count > 0 ? "warning" : "check_circle"}
        disabled={count === 0}
        onClick={() => setShowModal(true)}
      />
      <MembersNeedingBankingDataModal
        show={showModal}
        onHide={() => setShowModal(false)}
        members={members}
      />
    </>
  );
};

export default MembersNeedingBankingDataButton;
