import "dayjs/locale/de";
import React, { useState } from "react";
import TapirButton from "../components/TapirButton.tsx";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { getParameterFromUrl } from "../product_config/get_parameter_from_url.ts";
import { ToastData } from "../types/ToastData.ts";
import AssociationMembershipCancelModal from "./AssociationMembershipCancelModal.tsx";

interface AssociationMembershipCancelButtonProps {
  csrfToken: string;
}

const AssociationMembershipCancelButton: React.FC<
  AssociationMembershipCancelButtonProps
> = ({ csrfToken }) => {
  const [showModal, setShowModal] = useState(false);
  const [memberId, setMemberId] = useState();
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  return (
    <>
      <TapirButton
        icon={"contract_delete"}
        variant={"outline-primary"}
        onClick={() => {
          const memberId = getParameterFromUrl("member");
          if (!memberId) {
            alert("Du musst erst das Mitglied auswählen.");
            return;
          }
          setMemberId(memberId);
          setShowModal(true);
        }}
        tooltip={"Vereinsmitgliedschaft anpassen"}
        tootlipPosition={"bottom"}
      />
      {memberId && (
        <AssociationMembershipCancelModal
          memberId={memberId}
          csrfToken={csrfToken}
          show={showModal}
          onHide={() => setShowModal(false)}
          reloadData={() => location.reload()}
          setToastDatas={setToastDatas}
        />
      )}
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default AssociationMembershipCancelButton;
