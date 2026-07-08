import "dayjs/locale/de";
import React, { useState } from "react";
import TapirButton from "../components/TapirButton.tsx";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { getParameterFromUrl } from "../product_config/get_parameter_from_url.ts";
import { ToastData } from "../types/ToastData.ts";
import AssociationMembershipUpdateModal from "./AssociationMembershipUpdateModal.tsx";

interface AssociationMembershipUpdateButtonProps {
  csrfToken: string;
}

const AssociationMembershipUpdateButton: React.FC<
  AssociationMembershipUpdateButtonProps
> = ({ csrfToken }) => {
  const [showModal, setShowModal] = useState(false);
  const [memberId, setMemberId] = useState();
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  return (
    <>
      <TapirButton
        icon={"contract_edit"}
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
        <AssociationMembershipUpdateModal
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

export default AssociationMembershipUpdateButton;
