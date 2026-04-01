import React, { useEffect, useState } from "react";
import "dayjs/locale/de";
import { PaymentsApi } from "../../api-client";
import { useApi } from "../../hooks/useApi.ts";
import TapirToastContainer from "../../components/TapirToastContainer.tsx";
import { ToastData } from "../../types/ToastData.ts";
import TapirButton from "../../components/TapirButton.tsx";
import MemberProfilePaymentRhythmModal from "./MemberProfilePaymentRhythmModal.tsx";
import { handleRequestError } from "../../utils/handleRequestError.ts";

interface MemberProfilePaymentRhythmBaseProps {
  memberId: string;
  csrfToken: string;
}

const MemberProfilePaymentRhythmBase: React.FC<
  MemberProfilePaymentRhythmBaseProps
> = ({ memberId, csrfToken }) => {
  const api = useApi(PaymentsApi, csrfToken);
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
          csrfToken={csrfToken}
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
