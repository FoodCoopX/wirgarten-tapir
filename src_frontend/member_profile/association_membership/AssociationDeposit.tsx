import { type Dispatch, type SetStateAction, useEffect, useState } from "react";
import {
  type AssociationDepositDetails,
  AssociationsApi,
} from "../../api-client";
import TapirButton from "../../components/TapirButton";
import { useApi } from "../../hooks/useApi";
import { ToastData } from "../../types/ToastData";
import { formatCurrency } from "../../utils/formatCurrency";
import { handleRequestError } from "../../utils/handleRequestError";
import AssociationDepositIncreaseModal from "./AssociationDepositIncreaseModal";

interface AssociationDepositProps {
  memberId: string;
  setToastDatas: Dispatch<SetStateAction<ToastData[]>>;
}

export function AssociationDeposit({
  memberId,
  setToastDatas,
}: Readonly<AssociationDepositProps>) {
  const api = useApi(AssociationsApi);
  const [details, setDetails] = useState<AssociationDepositDetails>();
  const [showIncrease, setShowIncrease] = useState(false);
  const [message, setMessage] = useState("");
  useEffect(() => {
    setDetails(undefined);
    setShowIncrease(false);
    setMessage("");
    api
      .associationsApiMemberAssociationDepositRetrieve({ memberId })
      .then(setDetails)
      .catch((error) =>
        handleRequestError(
          error,
          "Die Vereinseinlage konnte nicht geladen werden.",
          setToastDatas,
        ),
      );
  }, [memberId]);
  if (!details) return null;
  return (
    <section className="mt-3">
      <h3 className="h6">{details.name}</h3>
      <p>{formatCurrency(details.amount)}</p>
      {details.agreementRequested && <p>Individuelle Vereinbarung erbeten</p>}
      {details.canIncrease && (
        <TapirButton
          variant="outline-primary"
          text="Einlage erhöhen"
          onClick={() => setShowIncrease(true)}
        />
      )}
      {showIncrease && (
        <AssociationDepositIncreaseModal
          memberId={memberId}
          details={details}
          setToastDatas={setToastDatas}
          onHide={() => setShowIncrease(false)}
          onSaved={(updated) => {
            setDetails(updated);
            setShowIncrease(false);
            setMessage(
              "Die Erhöhung wurde für den nächsten Einzug vorgemerkt.",
            );
          }}
        />
      )}
      {message && <p role="status">{message}</p>}
    </section>
  );
}
