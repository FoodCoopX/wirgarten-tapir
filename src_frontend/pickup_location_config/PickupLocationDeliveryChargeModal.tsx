import React, { useEffect, useState } from "react";
import { Form, Modal, Spinner, Table } from "react-bootstrap";
import {
  PickupLocationDeliveryChargeEntry,
  PickupLocationsApi,
} from "../api-client";
import { useApi } from "../hooks/useApi.ts";
import TapirButton from "../components/TapirButton.tsx";
import { getParameterFromUrl } from "../product_config/get_parameter_from_url.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import { ToastData } from "../types/ToastData.ts";
import { formatCurrency } from "../utils/formatCurrency.ts";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";

interface PickupLocationDeliveryChargeModalProps {
  show: boolean;
  onHide: () => void;
  csrfToken: string;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

const URL_PARAMETER_PICKUP_LOCATION_ID = "selected";

function parseAmountInput(input: string): string {
  return input.replace(",", ".").trim();
}

function formatAmount(amountAsString: string): string {
  return formatCurrency(Number.parseFloat(amountAsString));
}

const PickupLocationDeliveryChargeModal: React.FC<
  PickupLocationDeliveryChargeModalProps
> = ({ show, onHide, csrfToken, setToastDatas }) => {
  const api = useApi(PickupLocationsApi, csrfToken);

  const [dataLoading, setDataLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [locationName, setLocationName] = useState("");
  const [entries, setEntries] = useState<PickupLocationDeliveryChargeEntry[]>(
    [],
  );
  const [amountInput, setAmountInput] = useState("");
  const [validFromInput, setValidFromInput] = useState("");

  useEffect(() => {
    if (!show) return;

    setDataLoading(true);
    setAmountInput("");
    setValidFromInput("");

    const pickupLocationId = getParameterFromUrl(
      URL_PARAMETER_PICKUP_LOCATION_ID,
    );
    if (!pickupLocationId) return;

    api
      .pickupLocationsApiPickupLocationDeliveryChargesRetrieve({
        pickupLocationId: pickupLocationId,
      })
      .then((response) => {
        setLocationName(response.pickupLocationName);
        setEntries(response.entries);
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

  function sortEntriesByValidFromDesc(
    entries: PickupLocationDeliveryChargeEntry[],
  ): PickupLocationDeliveryChargeEntry[] {
    return [...entries].sort(
      (a, b) =>
        new Date(b.validFrom).getTime() - new Date(a.validFrom).getTime(),
    );
  }

  function getCurrentEntry(): PickupLocationDeliveryChargeEntry | undefined {
    const today = new Date();
    const sorted = sortEntriesByValidFromDesc(entries);
    return sorted.find((entry) => new Date(entry.validFrom) <= today);
  }

  function onSave() {
    const form = document.getElementById(
      "pickupLocationDeliveryChargeForm",
    ) as HTMLFormElement;
    if (!form.reportValidity()) return;

    setSaving(true);

    const pickupLocationId = getParameterFromUrl(
      URL_PARAMETER_PICKUP_LOCATION_ID,
    );

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
        {formatAmount(currentEntry.amount)} — gültig seit{" "}
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
          {sortEntriesByValidFromDesc(entries).map((entry) => (
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
            <Form id={"pickupLocationDeliveryChargeForm"}>
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
          <details>
            <summary>Verlauf</summary>
            <div className={"mt-2"}>{buildHistoryTable()}</div>
          </details>
        </div>
      </Modal.Body>
    );
  }

  return (
    <Modal show={show} onHide={onHide} centered={true} size={"lg"}>
      <Modal.Header closeButton>
        <h5 className={"mb-0"}>Lieferzuschlag: {locationName}</h5>
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
