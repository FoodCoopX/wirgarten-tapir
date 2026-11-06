import { useEffect, useState } from "react";
import { Alert, Card, Form, Modal, Table } from "react-bootstrap";
import {
  AssociationDepositDetails,
  AssociationDepositIncreasePreview,
  AssociationsApi,
} from "../../api-client";
import TapirButton from "../../components/TapirButton.tsx";
import TapirToastContainer from "../../components/TapirToastContainer.tsx";
import { useApi } from "../../hooks/useApi.ts";
import { ToastData } from "../../types/ToastData.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { formatDateNumeric } from "../../utils/formatDateNumeric.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { isValidDepositAmount } from "../../utils/isValidDepositAmount.ts";

interface Props {
  onDepositChanged: () => void;
  memberId: string;
  csrfToken: string;
}

function getDepositPaymentStatus(status: string): string {
  if (status === "STOPPED") return "Gestoppt";
  if (status === "PAID") return "Verbucht / exportiert";
  return "Offen";
}

function getDepositCollectionNotice(
  details: AssociationDepositDetails,
): string {
  if (details.refundRequiresAgreement)
    return "Rückzahlung erfasst. Neue Einzüge benötigen eine neue dokumentierte Verwaltungsvereinbarung.";
  if (details.state === "agreement_required")
    return "Neue Einlagenvereinbarung erforderlich.";
  return "Einzug außerhalb der Mitgliedschaft gestoppt.";
}

export default function AssociationDepositCard({
  memberId,
  csrfToken,
  onDepositChanged,
}: Readonly<Props>) {
  const api = useApi(AssociationsApi, csrfToken);
  const [details, setDetails] = useState<AssociationDepositDetails>();
  const [amount, setAmount] = useState("");
  const [preview, setPreview] = useState<AssociationDepositIncreasePreview>();
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
    setPreview(undefined);
  }

  async function loadData() {
    update(await api.associationsApiMemberDepositRetrieve({ memberId }));
  }

  useEffect(() => {
    loadData().catch((error) =>
      handleRequestError(error, "Fehler beim Laden der Einlage", setToastDatas),
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
      setPreview(
        await api.associationsApiDepositIncreasePreviewCreate({
          previewAssociationDepositIncreaseRequestRequest: {
            memberId,
            totalAmount: Number(amount),
          },
        }),
      );
    } catch (error) {
      await handleRequestError(
        error,
        "Die Erhöhung konnte nicht vorbereitet werden",
        setToastDatas,
      );
    } finally {
      setSaving(false);
    }
  }

  async function confirmIncrease() {
    if (!preview) return;
    setSaving(true);
    try {
      update(
        await api.associationsApiMemberDepositCreate({
          increaseAssociationDepositRequestRequest: {
            memberId,
            totalAmount: preview.totalAmount,
            confirmation: preview.confirmation,
          },
        }),
      );
      onDepositChanged();
    } catch (error) {
      setPreview(undefined);
      await handleRequestError(
        error,
        "Bitte den aktuellen Zahlungsplan neu prüfen und bestätigen",
        setToastDatas,
      );
      await loadData().catch((reloadError) =>
        handleRequestError(
          reloadError,
          "Fehler beim Aktualisieren der Einlage",
          setToastDatas,
        ),
      );
      onDepositChanged();
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
            {(details.refundRequiresAgreement ||
              ["agreement_required", "collection_stopped"].includes(
                details.state,
              )) && (
              <Alert variant="info">
                {getDepositCollectionNotice(details)} Bisherige Vereinbarung und
                Zahlungen bleiben erhalten. Es entsteht weder ein automatischer
                Erlass noch eine Rückzahlung.
              </Alert>
            )}
            {details.state === "pending" && (
              <Alert variant="info">
                <strong>Individuelle Vereinbarung offen</strong>
                <p className="mb-0">
                  Gesamtbetrag und Zahlungsplan sind noch nicht vereinbart. Bis
                  zu einer ausdrücklichen Vereinbarung wird kein Einlagenbetrag
                  eingezogen. Dies ist keine automatische Befreiung.
                </p>
              </Alert>
            )}
            {details.state === "waived" && (
              <Alert variant="success">
                Vollständiger Verzicht vereinbart. Es besteht keine offene
                Einlagenforderung.
              </Alert>
            )}
            {details.state === "individual" && (
              <p>
                Individuelle Vereinbarung. Änderungen werden persönlich mit der
                Verwaltung vereinbart und dokumentiert.
              </p>
            )}
            {details.state === "regular" && <p>Reguläre Vereinbarung.</p>}
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
              <dt>Extern zurückgezahlt</dt>
              <dd>{formatCurrency(details.refundedAmount)}</dd>
              <dt>Rechnerisch verbleibender Betrag</dt>
              <dd>{formatCurrency(details.retainedAmount)}</dd>
              <dt>Gestoppte Raten</dt>
              <dd>{formatCurrency(details.stoppedAmount)}</dd>
              <dt>Offener Einzug</dt>
              <dd>{formatCurrency(details.pendingAmount)}</dd>
            </dl>
            <small>
              Ein Bankexport bestätigt keinen tatsächlichen Zahlungseingang. Der
              rechnerische Betrag berücksichtigt externe Eingänge, verbuchte
              SEPA-Beträge und erfasste Rückzahlungen.
            </small>
            {(details.overpaymentCredit ?? 0) > 0 && (
              <Alert variant="info">
                Guthaben über dem vereinbarten Betrag:{" "}
                <strong>{formatCurrency(details.overpaymentCredit!)}</strong>.
                Eine Rückzahlung wird dadurch nicht automatisch ausgelöst.
              </Alert>
            )}
            {details.payments.length > 0 && (
              <Table size="sm" responsive>
                <caption>Zahlungen: {details.settings.name}</caption>
                <thead>
                  <tr>
                    <th scope="col">Termin</th>
                    <th scope="col">Betrag</th>
                    <th scope="col">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {details.payments.map((payment) => (
                    <tr key={payment.id}>
                      <td>{formatDateNumeric(payment.dueDate)}</td>
                      <td>{formatCurrency(payment.amount)}</td>
                      <td>{getDepositPaymentStatus(payment.status)}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
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
                  text="Erhöhung und Zahlungsplan prüfen"
                />
              </Form.Group>
            )}
          </Card.Body>
        </Card>
      )}
      {preview && details && (
        <Modal
          show
          onHide={() => {
            if (!saving) setPreview(undefined);
          }}
        >
          <Modal.Header closeButton>
            <Modal.Title>
              {details.settings.name}: Erhöhung bestätigen
            </Modal.Title>
          </Modal.Header>
          <Modal.Body>
            <p>
              Neuer Gesamtbetrag:{" "}
              <strong>{formatCurrency(preview.totalAmount)}</strong>.
            </p>
            <p>
              Extern eingegangen: {formatCurrency(preview.receivedAmount)}.
              Bereits verbucht / exportiert:{" "}
              {formatCurrency(preview.committedAmount)}.
            </p>
            <p>
              Verbleibender Einzug:{" "}
              <strong>{formatCurrency(preview.pendingAmount)}</strong>. Bitte
              prüfe diese Zahlungen; erst nach deiner Bestätigung wird die
              Erhöhung vereinbart.
            </p>
            <Table size="sm">
              <thead>
                <tr>
                  <th scope="col">Termin</th>
                  <th scope="col">Betrag</th>
                </tr>
              </thead>
              <tbody>
                {preview.payments.map((payment) => (
                  <tr
                    key={`${payment.dueDate.getTime()}-${payment.instalmentNumber ?? "single"}`}
                  >
                    <td>{formatDateNumeric(payment.dueDate)}</td>
                    <td>{formatCurrency(payment.amount)}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </Modal.Body>
          <Modal.Footer>
            <TapirButton
              variant="secondary"
              text="Abbrechen"
              disabled={saving}
              onClick={() => setPreview(undefined)}
            />
            <TapirButton
              variant="primary"
              text={`Gesamtbetrag verbindlich auf ${formatCurrency(preview.totalAmount)} erhöhen`}
              loading={saving}
              disabled={saving}
              onClick={confirmIncrease}
            />
          </Modal.Footer>
        </Modal>
      )}
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
}
