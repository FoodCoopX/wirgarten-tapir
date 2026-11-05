import dayjs from "dayjs";
import React, { useEffect, useRef, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Form,
  Modal,
  Spinner,
  Table,
} from "react-bootstrap";
import { v4 as uuidv4 } from "uuid";
import {
  AssociationsApi,
  DepositChangeRequest,
  DepositDetails,
} from "../../api-client";
import { useApi } from "../../hooks/useApi.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";

const labels: Record<string, string> = {
  increase: "Einlage erhöhen",
  agreement: "Individuelle Vereinbarung dokumentieren",
  receipt: "Externen Zahlungseingang erfassen",
  refund: "Externe Rückzahlung bestätigen",
  reversal: "Rücklastschrift / Korrektur erfassen",
  import: "Historische Einzahlung",
};

export default function AssociationDepositCard({
  memberId,
  csrfToken,
}: {
  memberId: string;
  csrfToken: string;
}) {
  const api = useApi(AssociationsApi, csrfToken);
  const [data, setData] = useState<DepositDetails>();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [action, setAction] = useState<DepositChangeRequest["action"]>();
  const [amount, setAmount] = useState("");
  const [count, setCount] = useState("1");
  const [date, setDate] = useState(dayjs().format("YYYY-MM-DD"));
  const [note, setNote] = useState("");
  const pendingRequest = useRef<
    { body: string; requestId: string } | undefined
  >(undefined);

  async function readError(error: unknown) {
    const response = (error as { response?: Response }).response;
    if (response) {
      try {
        const details = await response.json();
        setError(
          typeof details === "string"
            ? details
            : Object.values(details).flat().join(" "),
        );
        return;
      } catch {
        /* Show the fallback for unreadable responses. */
      }
    }
    setError(
      "Die Anfrage konnte nicht abgeschlossen werden. Bitte erneut versuchen.",
    );
  }
  useEffect(() => {
    api
      .associationsApiMembersDepositRetrieve({ memberId })
      .then(setData)
      .catch(readError);
  }, [memberId, api]);

  function open(next: DepositChangeRequest["action"]) {
    setAction(next);
    setError("");
    setCount("1");
    setNote("");
    setDate(dayjs().format("YYYY-MM-DD"));
    const minimumCents = Math.round(Number(data?._configuration.minimum) * 100);
    const stepCents = Math.round(Number(data?._configuration.increment) * 100);
    const currentCents = Math.round(Number(data?.agreedAmount ?? 0) * 100);
    const nextCents =
      minimumCents +
      Math.max(0, Math.floor((currentCents - minimumCents) / stepCents) + 1) *
        stepCents;
    setAmount(
      next === "increase"
        ? (nextCents / 100).toFixed(2)
        : (data?.agreedAmount ?? data?._configuration.minimum ?? "200.00"),
    );
    pendingRequest.current = undefined;
  }

  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (!data || !action || busy) return;
    // The generated client serializes date-only fields through toISOString().
    const calendarDate = new Date(`${date}T00:00:00.000Z`);
    const body = {
      action,
      amount,
      instalments: action === "agreement" ? Number(count) : 1,
      expectedRevision: data.revision,
      note,
      ...(action === "agreement"
        ? { startDate: calendarDate }
        : action === "increase"
          ? {}
          : { date: calendarDate }),
    };
    const fingerprint = JSON.stringify(body);
    if (pendingRequest.current?.body !== fingerprint)
      pendingRequest.current = {
        body: fingerprint,
        requestId: uuidv4(),
      };
    setBusy(true);
    setError("");
    try {
      const result = await api.associationsApiMembersDepositCreate({
        memberId,
        depositChangeRequest: {
          ...body,
          requestId: pendingRequest.current.requestId,
        },
      });
      setData(result);
      setAction(undefined);
      pendingRequest.current = undefined;
    } catch (error) {
      await readError(error);
    } finally {
      setBusy(false);
    }
  }

  if (!data)
    return error ? (
      <Alert variant="danger">{error}</Alert>
    ) : (
      <Spinner size="sm" />
    );
  if (!data._configuration.enabled && !data._exists) return null;
  const agreementPending =
    data._exists && data.agreedAmount === null && !data.cancellationDate;
  const status = data.cancellationDate
    ? "Gekündigt"
    : agreementPending
      ? "Individuelle Vereinbarung offen"
      : data.agreedAmount === null
        ? "Keine Einlage vereinbart"
        : Number(data.agreedAmount) === 0 && data.exceptionAuthorized
          ? "Befreiung vereinbart – abgeschlossen"
          : data.exceptionAuthorized
            ? "Individuelle Vereinbarung dokumentiert"
            : "Einlage vereinbart";
  return (
    <>
      <Card className="mt-3">
        <Card.Header>
          <Card.Title className="mb-0">{data._configuration.name}</Card.Title>
        </Card.Header>
        <Card.Body>
          <Alert variant={agreementPending ? "warning" : "info"}>
            {status}
            {agreementPending && (
              <p className="mb-0">
                Noch kein Gesamtbetrag und kein Zahlungsplan vereinbart. Es wird
                keine Einlage eingezogen. Bitte stimme die Vereinbarung mit der
                Verwaltung ab.
              </p>
            )}
          </Alert>
          <dl className="row">
            <dt className="col-sm-7">Vereinbarter Gesamtbetrag</dt>
            <dd className="col-sm-5">
              {data.agreedAmount === null
                ? "Offen"
                : formatCurrency(Number(data.agreedAmount))}
            </dd>
            <dt className="col-sm-7">Gebuchtes Guthaben</dt>
            <dd className="col-sm-5">{formatCurrency(Number(data.balance))}</dd>
            <dt className="col-sm-7">Offene, vereinbarte Einzüge</dt>
            <dd className="col-sm-5">{formatCurrency(Number(data.pending))}</dd>
            <dt className="col-sm-7">Extern zurückgezahlt</dt>
            <dd className="col-sm-5">
              {formatCurrency(Number(data.refunded))}
            </dd>
            <dt className="col-sm-7">Zur Rückzahlung zu prüfen</dt>
            <dd className="col-sm-5">
              {formatCurrency(Number(data.refundable))}
            </dd>
          </dl>
          {data.agreedAmount !== null &&
            Number(data.agreedAmount) < Number(data._configuration.minimum) &&
            data.exceptionAuthorized && (
              <p>
                Reduzierter Gesamtbetrag genehmigt. Aus der Differenz zur
                Mindesteinlage entsteht keine zusätzliche Forderung.
              </p>
            )}
          <p className="small text-muted">
            SEPA-Zahlungen zählen ab dem vorgesehenen Einzugstag zum gebuchten
            Guthaben. Der Export bestätigt keinen Bankeingang. Rücklastschriften
            werden separat erfasst. Rückzahlungen prüft die Verwaltung nach den
            geltenden Vereinbarungen und der Liquidität; Tapir führt sie nicht
            aus.
          </p>
          {data.payments.length > 0 && (
            <Table responsive size="sm">
              <thead>
                <tr>
                  <th>Fälligkeit</th>
                  <th>Betrag</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.payments.map((p) => (
                  <tr key={p.id}>
                    <td>{dayjs(p.dueDate).format("DD.MM.YYYY")}</td>
                    <td>{formatCurrency(Number(p.amount))}</td>
                    <td>
                      {p.exported ? "SEPA exportiert" : "Einzug offen"}
                      {p.instalmentNumber && ` · Rate ${p.instalmentNumber}`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
          {data.bookings.length > 0 && (
            <details>
              <summary>Externe Buchungen</summary>
              <Table responsive size="sm">
                <thead>
                  <tr>
                    <th>Datum</th>
                    <th>Buchung</th>
                    <th>Betrag</th>
                    <th>Beleg / Grund</th>
                  </tr>
                </thead>
                <tbody>
                  {data.bookings.map((b) => (
                    <tr key={b.id}>
                      <td>{dayjs(b.date).format("DD.MM.YYYY")}</td>
                      <td>{labels[b.kind]}</td>
                      <td>{formatCurrency(Number(b.amount))}</td>
                      <td>{b.note}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </details>
          )}
        </Card.Body>
        <Card.Footer className="d-flex flex-wrap gap-2">
          {data.canIncrease && (
            <Button variant="outline-primary" onClick={() => open("increase")}>
              {labels.increase}
            </Button>
          )}
          {data.canManage && (
            <>
              {data._configuration.enabled && !data.cancellationDate && (
                <Button
                  variant="outline-primary"
                  onClick={() => open("agreement")}
                >
                  {labels.agreement}
                </Button>
              )}
              {(["receipt", "refund", "reversal"] as const).map((kind) => (
                <Button
                  variant="outline-secondary"
                  key={kind}
                  onClick={() => open(kind)}
                >
                  {labels[kind]}
                </Button>
              ))}
            </>
          )}
        </Card.Footer>
      </Card>
      <Modal
        show={action !== undefined}
        onHide={() => {
          if (!busy) setAction(undefined);
        }}
      >
        <Form onSubmit={save}>
          <Modal.Header closeButton={!busy}>
            <Modal.Title>{action && labels[action]}</Modal.Title>
          </Modal.Header>
          <Modal.Body>
            {error && (
              <Alert variant="danger">
                {error}
                <Button
                  variant="link"
                  onClick={() => {
                    api
                      .associationsApiMembersDepositRetrieve({ memberId })
                      .then(setData)
                      .catch(readError);
                  }}
                >
                  Aktuellen Stand laden
                </Button>
              </Alert>
            )}
            <Form.Group controlId="deposit-total">
              <Form.Label>
                {action === "agreement" || action === "increase"
                  ? "Neuer Gesamtbetrag (€)"
                  : "Buchungsbetrag (€)"}
              </Form.Label>
              <Form.Control
                required
                type="number"
                min={action === "agreement" ? 0 : 0.01}
                step="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
              />
            </Form.Group>
            {action === "agreement" && (
              <>
                <Form.Group controlId="deposit-rates" className="mt-2">
                  <Form.Label>
                    Monatliche Raten für den noch zu zahlenden Betrag
                  </Form.Label>
                  <Form.Control
                    required
                    type="number"
                    min="1"
                    max="120"
                    value={count}
                    onChange={(e) => setCount(e.target.value)}
                  />
                </Form.Group>
                <p className="small">
                  0 € bedeutet ausdrücklich vereinbarte Befreiung. Vorhandene
                  Einzahlungen bleiben erhalten. Nur noch nicht exportierte
                  Einzüge werden ersetzt; bereits gezahlte Beträge werden
                  angerechnet.
                </p>
              </>
            )}
            {action !== "increase" && (
              <>
                <Form.Group controlId="deposit-date" className="mt-2">
                  <Form.Label>
                    {action === "agreement"
                      ? "Vereinbarter Beginn (Einzug nach SEPA-Regeln)"
                      : "Datum der tatsächlichen Buchung"}
                  </Form.Label>
                  <Form.Control
                    required
                    type="date"
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                  />
                </Form.Group>
                <Form.Group controlId="deposit-note" className="mt-2">
                  <Form.Label>
                    {action === "agreement"
                      ? "Dokumentierte Zustimmung des Mitglieds (Datum, Vereinbarung, Beleg)"
                      : "Beleg und Buchungsgrund"}
                  </Form.Label>
                  <Form.Control
                    required
                    as="textarea"
                    maxLength={2000}
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                  />
                </Form.Group>
              </>
            )}
            {action === "refund" && (
              <p>
                Hier nur eine bereits außerhalb von Tapir ausgeführte
                Rückzahlung bestätigen. Es wird keine Überweisung ausgelöst.
              </p>
            )}
          </Modal.Body>
          <Modal.Footer>
            <Button
              variant="secondary"
              disabled={busy}
              onClick={() => setAction(undefined)}
            >
              Abbrechen
            </Button>
            <Button type="submit" disabled={busy}>
              {busy
                ? "Wird gespeichert …"
                : action === "agreement"
                  ? "Vereinbarung bestätigen"
                  : "Bestätigen"}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>
    </>
  );
}
