import React, { useEffect, useRef, useState } from "react";
import { Form, Modal, Spinner, Table } from "react-bootstrap";
import {
  PickupLocationDeliveryChargeEntry,
  PickupLocationsApi,
} from "../api-client";
import { useApi } from "../hooks/useApi.ts";
import TapirButton from "../components/TapirButton.tsx";
import { handleRequestError } from "../utils/handleRequestError.ts";
import { ToastData } from "../types/ToastData.ts";
import { formatCurrency } from "../utils/formatCurrency.ts";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";

interface PickupLocationDeliveryChargeModalProps {
  show: boolean;
  onHide: () => void;
  csrfToken: string;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
  pickupLocationId: string;
}

function parseAmountInput(input: string): string {
  return input.replace(",", ".").trim();
}

function formatAmount(amountAsString: string): string {
  return formatCurrency(Number.parseFloat(amountAsString));
}

const PickupLocationDeliveryChargeModal: React.FC<
  PickupLocationDeliveryChargeModalProps
> = ({ show, onHide, csrfToken, setToastDatas, pickupLocationId }) => {
  const api = useApi(PickupLocationsApi, csrfToken);

  const [dataLoading, setDataLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [locationName, setLocationName] = useState("");
  const [entries, setEntries] = useState<PickupLocationDeliveryChargeEntry[]>(
    [],
  );
  const [amountInput, setAmountInput] = useState("");
  const [validFromInput, setValidFromInput] = useState("");
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    if (!show) return;

    setDataLoading(true);
    setAmountInput("");
    setValidFromInput("");

    api
      .pickupLocationsApiPickupLocationDeliveryChargesRetrieve({
        pickupLocationId: pickupLocationId,
      })
      .then((response) => {
        setLocationName(response.pickupLocationName);
        setEntries(
          response.entries.toSorted(
            (a, b) =>
              new Date(b.validFrom).getTime() -
              new Date(a.validFrom).getTime(),
          ),
        );
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Lieferzuschläge",
          setToastDatas,
        ),
      )
      .finally(() => setDataLoading(false));
  }, [show]);

  function getCurrentEntry(): PickupLocationDeliveryChargeEntry | undefined {
    const today = new Date();
    return entries.find((entry) => new Date(entry.validFrom) <= today);
  }

  function onSave() {
    if (!formRef.current?.reportValidity()) return;

    setSaving(true);

    api
      .pickupLocationsApiPickupLocationDeliveryChargesCreate({
        pickupLocationDeliveryChargeCreateRequestRequest: {
          pickupLocationId: pickupLocationId,
          amount: parseAmountInput(amountInput),
          validFrom: new Date(validFromInput),
        },
      })
      .then(() => location.reload())
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Speichern des Lieferzuschlags",
          setToastDatas,
        ),
      )
      .finally(() => setSaving(false));
  }

  function buildCurrentSection() {
    const currentEntry = getCurrentEntry();
    if (!currentEntry) {
      return <span>Kein Zuschlag konfiguriert (0,00 €)</span>;
    }
    return (
      <span>
        {formatAmount(currentEntry.amount)} - gültig seit{" "}
        {formatDateNumeric(new Date(currentEntry.validFrom))}
      </span>
    );
  }

  function buildHistoryTable() {
    if (entries.length === 0) {
      return <span>Keine Einträge vorhanden.</span>;
    }
    return (
      <Table size={"sm"} striped>
        <thead>
          <tr>
            <th>Betrag</th>
            <th>Gültig ab</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <tr key={entry.id}>
              <td>{formatAmount(entry.amount)}</td>
              <td>{formatDateNumeric(new Date(entry.validFrom))}</td>
            </tr>
          ))}
        </tbody>
      </Table>
    );
  }

  function getModalBody() {
    if (dataLoading) {
      return (
        <Modal.Body>
          <Spinner />
        </Modal.Body>
      );
    }

    return (
      <Modal.Body>
        <div className={"d-flex flex-column gap-3"}>
          <div>
            <h6>Aktueller Zuschlag</h6>
            {buildCurrentSection()}
          </div>
          <div>
            <h6>Neuen Zuschlag planen</h6>
            <Form ref={formRef}>
              <Form.Group>
                <Form.Label>Betrag (€)</Form.Label>
                <Form.Control
                  type={"text"}
                  inputMode={"decimal"}
                  pattern={"^\\d+([.,]\\d{1,2})?$"}
                  placeholder={"0,00"}
                  value={amountInput}
                  required={true}
                  onChange={(event) => setAmountInput(event.target.value)}
                />
              </Form.Group>
              <Form.Group>
                <Form.Label>Gültig ab</Form.Label>
                <Form.Control
                  type={"date"}
                  value={validFromInput}
                  required={true}
                  onChange={(event) => setValidFromInput(event.target.value)}
                />
              </Form.Group>
            </Form>
          </div>
          <div>
            <h6>Verlauf</h6>
            {buildHistoryTable()}
          </div>
        </div>
      </Modal.Body>
    );
  }

  return (
    <Modal show={show} onHide={onHide} centered={true} size={"lg"}>
      <Modal.Header closeButton>
        <Modal.Title>Lieferzuschlag: {locationName}</Modal.Title>
      </Modal.Header>
      {getModalBody()}
      <Modal.Footer>
        <TapirButton
          text={"Speichern"}
          icon={"save"}
          variant={"primary"}
          loading={saving}
          onClick={onSave}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default PickupLocationDeliveryChargeModal;
