import React, { useState } from "react";
import { Form, Modal } from "react-bootstrap";
import { PaymentsApi } from "../api-client";
import ConfirmModal from "../components/ConfirmModal.tsx";
import TapirButton from "../components/TapirButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

interface RebuildSubscriptionPaymentsModalProps {
  show: boolean;
  onHide: () => void;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
  afterRebuild: () => void;
}

function getMonthDisplay(index: number) {
  const options: Intl.DateTimeFormatOptions = {
    month: "long",
  };
  const date = new Date();
  date.setMonth(index);

  return date.toLocaleDateString("de-DE", options);
}
const RebuildSubscriptionPaymentsModal: React.FC<
  RebuildSubscriptionPaymentsModalProps
> = ({ show, onHide, setToastDatas, afterRebuild }) => {
  const api = useApi(PaymentsApi, getCsrfToken());
  const [loading, setLoading] = useState(false);
  const [month, setMonth] = useState(new Date().getMonth());
  const [year, setYear] = useState(new Date().getFullYear());
  const [showConfirmationModal, setShowConfirmationModal] = useState(false);

  function onConfirmRebuild() {
    setLoading(true);

    const from = new Date();
    from.setFullYear(year);
    from.setMonth(month);

    api
      .paymentsApiRebuildSubscriptionPaymentsCreate({ from: from })
      .then(() => {
        setShowConfirmationModal(false);
        afterRebuild();
      })
      .catch((error) =>
        handleRequestError(error, "Fehler beim neu erzeugen", setToastDatas),
      )
      .finally(() => setLoading(false));
  }

  return (
    <>
      <Modal
        show={show && !showConfirmationModal}
        onHide={onHide}
        centered={true}
        size={"xl"}
      >
        <Modal.Header closeButton>
          <Modal.Title>Vertragszahlungen neu exportieren</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <p>
            Vertragszahlungsdaten ab dem angegebenen Monat werden gelöscht und
            neu erzeugt.
          </p>
          <p>
            Zahlungsdaten relativ zu Genossenschaftsanteilen sind nicht
            betroffen.
          </p>
          <p>
            Dieses Aktion kann nicht rückgängig gemacht werden. Es ist empfohlen
            die alte Dateien zu sichern vor sie gelöscht werden.
          </p>
          <Form className={"d-flex flex-row gap-2"}>
            <Form.Group>
              <Form.Label>Monat</Form.Label>
              <Form.Select
                onChange={(event) =>
                  setMonth(Number.parseInt(event.target.value))
                }
                value={month}
              >
                {Array.from(new Array(12).keys()).map((index) => (
                  <option key={index} value={index}>
                    {getMonthDisplay(index)}
                  </option>
                ))}
              </Form.Select>
            </Form.Group>
            <Form.Group>
              <Form.Label>Jahr</Form.Label>
              <Form.Control
                value={year}
                onChange={(event) =>
                  setYear(Number.parseInt(event.target.value))
                }
                type={"number"}
                step={1}
                min={2020}
                max={2050}
              />
            </Form.Group>
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <TapirButton
            text={"Neu erzeugen"}
            variant={"primary"}
            icon={"redo"}
            onClick={() => setShowConfirmationModal(true)}
            loading={loading}
          />
        </Modal.Footer>
      </Modal>
      <ConfirmModal
        message={
          "Bist du sicher das du die Lastschrift-Dateien ab " +
          getMonthDisplay(month) +
          " " +
          year +
          " neu erzeugen willst?"
        }
        title={"Bitte bestätigen"}
        open={showConfirmationModal}
        confirmButtonText={"Neu erzeugen bestätigen"}
        confirmButtonVariant={"primary"}
        confirmButtonIcon={"redo"}
        onConfirm={() => onConfirmRebuild()}
        onCancel={() => setShowConfirmationModal(false)}
        loading={loading}
      />
    </>
  );
};

export default RebuildSubscriptionPaymentsModal;
