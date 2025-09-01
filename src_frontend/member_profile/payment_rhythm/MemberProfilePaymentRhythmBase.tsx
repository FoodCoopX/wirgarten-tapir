import React, { useEffect, useState } from "react";
import "dayjs/locale/de";
import { SubscriptionsApi } from "../../api-client";
import { useApi } from "../../hooks/useApi.ts";
import TapirToastContainer from "../../components/TapirToastContainer.tsx";
import { ToastData } from "../../types/ToastData.ts";
import TapirButton from "../../components/TapirButton.tsx";
import MemberProfilePaymentRhythmModal from "./MemberProfilePaymentRhythmModal.tsx";

interface MemberProfilePaymentRhythmBaseProps {
  memberId: string;
  csrfToken: string;
}

const MemberProfilePaymentRhythmBase: React.FC<
  MemberProfilePaymentRhythmBaseProps
> = ({ memberId, csrfToken }) => {
  const api = useApi(SubscriptionsApi, csrfToken);
  const [showModal, setShowModal] = useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  useEffect(() => {}, []);

  return (
    <>
      <TapirButton
        variant={"outline-primary"}
        icon={"edit"}
        size={"sm"}
        onClick={() => setShowModal(true)}
      />
      <MemberProfilePaymentRhythmModal
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

export default MemberProfilePaymentRhythmBase;
