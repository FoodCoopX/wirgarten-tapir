import { type Dispatch, type SetStateAction, useState } from "react";
import { Form, Modal } from "react-bootstrap";
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

interface Props {
  memberId: string;
  details: AssociationDepositDetails;
  onHide: () => void;
  onSaved: (details: AssociationDepositDetails) => void;
  setToastDatas: Dispatch<SetStateAction<ToastData[]>>;
}

export default function AssociationDepositIncreaseModal({
  memberId,
  details,
  onHide,
  onSaved,
  setToastDatas,
}: Readonly<Props>) {
  const api = useApi(AssociationsApi);
  const [total, setTotal] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const newTotal = Number(total);
  const difference = newTotal - details.amount;
  const valid =
    difference > 0 &&
    isValidDepositAmount(newTotal, details.minimum, details.increment);

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || !valid || !confirmed) return;
    setBusy(true);
    api
      .associationsApiMemberAssociationDepositCreate({
        memberId,
        increaseAssociationDepositRequestRequest: {
          totalAmount: total,
          confirmation: confirmed,
        },
      })
      .then(onSaved)
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
    <Modal show onHide={busy ? undefined : onHide} centered>
      <Modal.Header closeButton={!busy}>
        <Modal.Title>{details.name} erhöhen</Modal.Title>
      </Modal.Header>
      <Form onSubmit={submit}>
        <Modal.Body>
          <p>
            Die Einlage beträgt aktuell {formatCurrency(details.amount)}. Gib
            den gewünschten neuen Gesamtbetrag an. Die Differenz wird einmalig
            per SEPA-Lastschrift eingezogen.
          </p>
          <Form.Group controlId="association-deposit-total" className="mb-3">
            <Form.Label>Neuer Gesamtbetrag (€)</Form.Label>
            <Form.Control
              type="number"
              inputMode="decimal"
              value={total}
              min={details.minimum}
              step={details.increment}
              disabled={busy}
              onChange={(event) => {
                setTotal(event.target.value);
                setConfirmed(false);
              }}
            />
          </Form.Group>
          {valid && (
            <Form.Check
              id="association-deposit-confirmation"
              label={`Einmalige Lastschrift über ${formatCurrency(difference)} bestätigen`}
              checked={confirmed}
              disabled={busy}
              onChange={(event) => setConfirmed(event.target.checked)}
            />
          )}
        </Modal.Body>
        <Modal.Footer>
          <TapirButton
            variant="outline-secondary"
            text="Abbrechen"
            onClick={onHide}
            disabled={busy}
          />
          <TapirButton
            variant="primary"
            type="submit"
            text="Einlage erhöhen"
            disabled={busy || !valid || !confirmed}
            loading={busy}
          />
        </Modal.Footer>
      </Form>
    </Modal>
  );
}
