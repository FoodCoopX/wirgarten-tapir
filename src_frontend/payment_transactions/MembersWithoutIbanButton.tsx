import React, { useEffect, useState } from "react";
import { MemberWithoutIban, PaymentsApi } from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import MembersWithoutIbanModal from "./MembersWithoutIbanModal.tsx";

interface MembersWithoutIbanButtonProps {
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

const MembersWithoutIbanButton: React.FC<MembersWithoutIbanButtonProps> = ({
  setToastDatas,
}) => {
  const api = useApi(PaymentsApi, "unused");
  const [members, setMembers] = useState<MemberWithoutIban[] | undefined>(
    undefined,
  );
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    api
      .paymentsApiMembersWithoutIbanList()
      .then(setMembers)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Benutzer:innen ohne IBAN",
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
        text={count > 0 ? `${count} Benutzer:in ohne IBAN` : "0 fehlende IBANs"}
        icon={count > 0 ? "warning" : "check_circle"}
        disabled={count === 0}
        onClick={() => setShowModal(true)}
      />
      <MembersWithoutIbanModal
        show={showModal}
        onHide={() => setShowModal(false)}
        members={members}
      />
    </>
  );
};

export default MembersWithoutIbanButton;
