import { type Dispatch, type SetStateAction, useEffect, useState } from "react";
import { Form } from "react-bootstrap";
import {
  type AssociationDepositDetails,
  AssociationsApi,
} from "../../api-client";
import TapirButton from "../../components/TapirButton";
import { useApi } from "../../hooks/useApi";
import { ToastData } from "../../types/ToastData";
import { formatCurrency } from "../../utils/formatCurrency";
import { handleRequestError } from "../../utils/handleRequestError";
import { isValidDepositAmount } from "../../utils/isValidDepositAmount";

interface AssociationDepositProps {
  memberId: string;
  csrfToken: string;
  setToastDatas: Dispatch<SetStateAction<ToastData[]>>;
}

export function AssociationDeposit({
  memberId,
  csrfToken,
  setToastDatas,
}: AssociationDepositProps) {
  const api = useApi(AssociationsApi, csrfToken);
  const [details, setDetails] = useState<AssociationDepositDetails>();
  const [total, setTotal] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
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

  if (!details?.visible) {
    return null;
  }

  const newTotal = Number(total);
  const difference = newTotal - details.amount;
  const valid =
    difference > 0 &&
    isValidDepositAmount(newTotal, details.minimum, details.increment);

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    api
      .associationsApiMemberAssociationDepositCreate({
        memberId,
        increaseAssociationDepositRequestRequest: {
          totalAmount: total,
          previousAmount: details!.amount.toFixed(2),
          confirmation: confirmed,
        },
      })
      .then((updated) => {
        setDetails(updated);
        setTotal("");
        setConfirmed(false);
        setMessage("Die Erhöhung wurde für den nächsten Einzug vorgemerkt.");
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Die Einlage konnte nicht erhöht werden.",
          setToastDatas,
        ),
      )
      .finally(() => setBusy(false));
  }

  return (
    <section className="mt-3">
      <h3 className="h6">{details.name}</h3>
      <p>
        {details.agreementRequested
          ? "Individuelle Vereinbarung erbeten"
          : formatCurrency(details.amount)}
      </p>
      {details.canIncrease && (
        <Form onSubmit={submit}>
          <Form.Group controlId="association-deposit-total" className="mb-2">
            <Form.Label>Neuer Gesamtbetrag (€)</Form.Label>
            <Form.Control
              type="number"
              inputMode="decimal"
              value={total}
              min={details.minimum}
              step={details.increment}
              onChange={(event) => {
                setTotal(event.target.value);
                setConfirmed(false);
              }}
            />
          </Form.Group>
          {valid && (
            <Form.Check
              id="association-deposit-confirmation"
              className="mb-2"
              label={`Ich bestätige die einmalige Lastschrift über ${formatCurrency(difference)}.`}
              checked={confirmed}
              onChange={(event) => setConfirmed(event.target.checked)}
            />
          )}
          <TapirButton
            variant="primary"
            type="submit"
            text="Einlage erhöhen"
            disabled={!valid || !confirmed}
            loading={busy}
          />
        </Form>
      )}
      {message && <p role="status">{message}</p>}
    </section>
  );
}
