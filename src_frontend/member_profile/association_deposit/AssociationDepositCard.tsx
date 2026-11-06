import { useEffect, useState } from "react";
import { Alert, Card, Form } from "react-bootstrap";
import { AssociationDepositDetails, AssociationsApi } from "../../api-client";
import TapirButton from "../../components/TapirButton.tsx";
import TapirToastContainer from "../../components/TapirToastContainer.tsx";
import { useApi } from "../../hooks/useApi.ts";
import { ToastData } from "../../types/ToastData.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { isValidDepositAmount } from "../../utils/isValidDepositAmount.ts";

interface Props {
  onDepositChanged: () => void;
  memberId: string;
  csrfToken: string;
}

export default function AssociationDepositCard({
  memberId,
  csrfToken,
  onDepositChanged,
}: Readonly<Props>) {
  const api = useApi(AssociationsApi, csrfToken);
  const [details, setDetails] = useState<AssociationDepositDetails>();
  const [amount, setAmount] = useState("");
  const [saving, setSaving] = useState(false);
  const [showError, setShowError] = useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  function update(data: AssociationDepositDetails) {
    setDetails(data);
    const minimum = Math.round(data.settings.minimum * 100);
    const step = Math.round(data.settings.increment * 100);
    const current = Math.round((data.agreedAmount ?? 0) * 100);
    setAmount(
      String(
        (minimum +
          Math.ceil((Math.max(minimum, current + 1) - minimum) / step) * step) /
          100,
      ),
    );
    setShowError(false);
  }

  useEffect(() => {
    api
      .associationsApiMemberDepositRetrieve({ memberId })
      .then(update)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Einlage",
          setToastDatas,
        ),
      );
  }, [memberId]);

  async function increase() {
    if (
      !details ||
      !isValidDepositAmount(
        Number(amount),
        details.settings.minimum,
        details.settings.increment,
      ) ||
      Number(amount) <= (details.agreedAmount ?? 0)
    ) {
      setShowError(true);
      return;
    }
    setSaving(true);
    try {
      update(
        await api.associationsApiMemberDepositCreate({
          increaseAssociationDepositRequestRequest: {
            memberId,
            totalAmount: Number(amount),
          },
        }),
      );
      onDepositChanged();
    } catch (error) {
      await handleRequestError(
        error,
        "Die Einlage konnte nicht erhöht werden",
        setToastDatas,
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      {details?.visible && (
        <Card className="mt-3">
          <Card.Header>
            <Card.Title className="mb-0">{details.settings.name}</Card.Title>
          </Card.Header>
          <Card.Body>
            {details.agreedAmount === null ? (
              <p>Es ist keine Einlage vereinbart.</p>
            ) : (
              <p>
                Vereinbarter Gesamtbetrag:{" "}
                <strong>{formatCurrency(details.agreedAmount)}</strong>
              </p>
            )}
            <dl>
              <dt>Extern eingegangen</dt>
              <dd>{formatCurrency(details.receivedAmount)}</dd>
              <dt>Für SEPA verbucht</dt>
              <dd>{formatCurrency(details.committedAmount)}</dd>
              <dt>Offener Einzug</dt>
              <dd>{formatCurrency(details.pendingAmount)}</dd>
            </dl>
            <small>
              Rückzahlbare Einlage pro Mitglied, unabhängig von Vereins- und
              Erntebeiträgen.
            </small>
            {details.canIncrease && (
              <Form.Group controlId="increase-deposit-total" className="mt-3">
                <Form.Label>Neuer Gesamtbetrag (€)</Form.Label>
                <Form.Control
                  type="number"
                  value={amount}
                  min={details.settings.minimum}
                  step={details.settings.increment}
                  disabled={saving}
                  onChange={(event) => {
                    setAmount(event.target.value);
                    setShowError(false);
                  }}
                  isInvalid={showError}
                />
                <Form.Text>
                  Mindestens {formatCurrency(details.settings.minimum)},
                  Schritte von {formatCurrency(details.settings.increment)}. Die
                  Erhöhung wird über das SEPA-Mandat eingezogen.
                </Form.Text>
                {showError && (
                  <Alert variant="danger">
                    Bitte einen höheren Gesamtbetrag in den angegebenen
                    Schritten wählen.
                  </Alert>
                )}
                <TapirButton
                  variant="outline-primary"
                  className="mt-2"
                  onClick={increase}
                  loading={saving}
                  disabled={saving}
                  text={`Gesamtbetrag verbindlich auf ${formatCurrency(Number(amount) || 0)} erhöhen`}
                />
              </Form.Group>
            )}
          </Card.Body>
        </Card>
      )}
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
}
