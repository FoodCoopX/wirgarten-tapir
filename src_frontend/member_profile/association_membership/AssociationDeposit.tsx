import { useEffect, useState } from "react";
import { Button, Form } from "react-bootstrap";
import {
  type AssociationDepositDetails,
  AssociationsApi,
} from "../../api-client";
import { useApi } from "../../hooks/useApi";
import { isValidDepositAmount } from "../../utils/isValidDepositAmount";

interface AssociationDepositProps {
  memberId: string;
  csrfToken: string;
}

export function AssociationDeposit({
  memberId,
  csrfToken,
}: AssociationDepositProps) {
  const api = useApi(AssociationsApi, csrfToken);
  const [details, setDetails] = useState<AssociationDepositDetails>();
  const [total, setTotal] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState(false);
  const money = new Intl.NumberFormat("de-DE", {
    style: "currency",
    currency: "EUR",
  });

  useEffect(() => {
    api
      .associationsApiMemberAssociationDepositRetrieve({ memberId })
      .then(setDetails)
      .catch(() => {
        setError(true);
        setMessage("Die Vereinseinlage konnte nicht geladen werden.");
      });
  }, [memberId]);

  if (!details?.visible) {
    return error ? <p role="alert">{message}</p> : null;
  }

  const newTotal = Number(total);
  const difference = newTotal - details.amount;
  const valid =
    difference > 0 &&
    isValidDepositAmount(newTotal, details.minimum, details.increment);

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(false);
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
      .catch(() => {
        setError(true);
        setMessage("Die Einlage konnte nicht erhöht werden.");
      })
      .finally(() => setBusy(false));
  }

  return (
    <section className="mt-3">
      <h3 className="h6">{details.name}</h3>
      <p>
        {details.agreementRequested
          ? "Individuelle Vereinbarung erbeten"
          : money.format(details.amount)}
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
              label={`Ich bestätige die einmalige Lastschrift über ${money.format(difference)}.`}
              checked={confirmed}
              onChange={(event) => setConfirmed(event.target.checked)}
            />
          )}
          <Button type="submit" disabled={!valid || !confirmed || busy}>
            Einlage erhöhen
          </Button>
        </Form>
      )}
      {message && <p role={error ? "alert" : "status"}>{message}</p>}
    </section>
  );
}
