import "dayjs/locale/de";
import React, { useEffect, useState } from "react";
import { PaymentsApi } from "../../api-client";
import TapirButton from "../../components/TapirButton.tsx";
import TapirToastContainer from "../../components/TapirToastContainer.tsx";
import { useApi } from "../../hooks/useApi.ts";
import { ToastData } from "../../types/ToastData.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import MemberProfilePaymentRhythmModal from "./MemberProfilePaymentRhythmModal.tsx";

interface MemberProfilePaymentRhythmBaseProps {
  memberId: string;
}

const MemberProfilePaymentRhythmBase: React.FC<
  MemberProfilePaymentRhythmBaseProps
> = ({ memberId }) => {
  const api = useApi(PaymentsApi);
  const [showModal, setShowModal] = useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);
  const [allowedRhythms, setAllowedRhythms] = useState<{
    [key: string]: string;
  }>({});

  useEffect(() => {
    api
      .paymentsApiMemberPaymentRhythmDataRetrieve({ memberId: memberId })
      .then((response) => {
        setAllowedRhythms(response.allowedRhythms);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Zahlungsintervall-Daten",
          setToastDatas,
        ),
      );
  }, []);

  return (
    Object.keys(allowedRhythms).length > 1 && (
      <>
        <TapirButton
          variant={"outline-primary"}
          icon={"edit"}
          size={"sm"}
          onClick={() => setShowModal(true)}
        />
        <MemberProfilePaymentRhythmModal
          memberId={memberId}
          setToastDatas={setToastDatas}
          show={showModal}
          onHide={() => setShowModal(false)}
          allowedRhythms={allowedRhythms}
        />
        <TapirToastContainer
          toastDatas={toastDatas}
          setToastDatas={setToastDatas}
        />
      </>
    )
  );
};

export default MemberProfilePaymentRhythmBase;
