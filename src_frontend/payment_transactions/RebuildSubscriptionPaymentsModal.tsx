import React, { useEffect, useState } from "react";
import { Alert, Form, Modal } from "react-bootstrap";
import { MemberNeedingBankingData, PaymentsApi } from "../api-client";
import ConfirmModal from "../components/ConfirmModal.tsx";
import TapirButton from "../components/TapirButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import MembersNeedingBankingDataDetails from "./MembersNeedingBankingDataDetails.tsx";
import MembersNeedingBankingDataRebuildWarningModal from "./MembersNeedingBankingDataRebuildWarningModal.tsx";

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
  const [checkingBankingData, setCheckingBankingData] = useState(false);
  const [month, setMonth] = useState(new Date().getMonth());
  const [year, setYear] = useState(new Date().getFullYear());
  const [showConfirmationModal, setShowConfirmationModal] = useState(false);
  const [showBankingDataWarningModal, setShowBankingDataWarningModal] =
    useState(false);
  const [membersNeedingBankingData, setMembersNeedingBankingData] = useState<
    MemberNeedingBankingData[]
  >([]);
  const [error, setError] = useState("");

  function getSelectedMonthDate() {
    // Built in UTC (not via local-time setters) so the date sent to the
    // backend can't shift to the previous day depending on the browser's
    // timezone and the time of day this is clicked - the API client
    // serializes this via toISOString(), which is UTC-based.
    return new Date(Date.UTC(year, month, 1));
  }

  function onClickRebuild() {
    setCheckingBankingData(true);
    api
      .paymentsApiMembersNeedingBankingDataForRebuildList({
        from: getSelectedMonthDate(),
      })
      .then((response) => {
        setMembersNeedingBankingData(response);
        if (response.length > 0) {
          setShowBankingDataWarningModal(true);
        } else {
          setShowConfirmationModal(true);
        }
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler bei der Prüfung der Bankdaten",
          setToastDatas,
        ),
      )
      .finally(() => setCheckingBankingData(false));
  }

  function onConfirmRebuild() {
    setLoading(true);

    api
      .paymentsApiRebuildSubscriptionPaymentsCreate({
        from: getSelectedMonthDate(),
      })
      .then((response) => {
        if (response.orderConfirmed) {
          setError("");
          afterRebuild();
        } else {
          setError(response.error!);
        }
        setShowConfirmationModal(false);
      })
      .catch((error) =>
        handleRequestError(error, "Fehler beim neu erzeugen", setToastDatas),
      )
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    setError("");
  }, [show]);

  return (
    <>
      <Modal
        show={show && !showConfirmationModal && !showBankingDataWarningModal}
        onHide={onHide}
        centered={true}
        size={"xl"}
      >
        <Modal.Header closeButton>
          <Modal.Title>Vertragszahlungen neu exportieren</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <p>
            Vertragszahlungsdaten (CSV und XML) ab dem unten angegebenen Monat
            werden gelöscht und neu erzeugt. Bitte wähle hier immer nur den
            laufenden Monat aus. Die neu erzeugten Vertragszahlungsdaten
            beziehen die aktuell gültigen Verträge ein, d.h. auch nachträgliche
            Vertragsänderungen des laufenden Monats, die sich auf die
            Zahlungsreihe im aktuellen Monat auswirken, sind berücksichtigt.
          </p>
          <p>
            Dieses Aktion kann nicht rückgängig gemacht werden. Wenn die Dateien
            einmal neu erzeugt wurden, sind die alten Dateien für die
            entsprechenden Monate nicht mehr zugänglich.
          </p>
          {error && <Alert variant={"danger"}>{error}</Alert>}
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
            onClick={onClickRebuild}
            loading={checkingBankingData}
          />
        </Modal.Footer>
      </Modal>
      <ConfirmModal
        message={
          <>
            <p>
              Bist du sicher das du die Lastschrift-Dateien ab{" "}
              {getMonthDisplay(month)} {year} neu erzeugen willst?
            </p>
            {membersNeedingBankingData.length > 0 && (
              <MembersNeedingBankingDataDetails
                members={membersNeedingBankingData}
              />
            )}
          </>
        }
        title={"Bitte bestätigen"}
        open={showConfirmationModal}
        confirmButtonText={"Neu erzeugen bestätigen"}
        confirmButtonVariant={"primary"}
        confirmButtonIcon={"redo"}
        onConfirm={() => onConfirmRebuild()}
        onCancel={() => setShowConfirmationModal(false)}
        loading={loading}
        size={membersNeedingBankingData.length > 0 ? "lg" : undefined}
      />
      <MembersNeedingBankingDataRebuildWarningModal
        show={showBankingDataWarningModal}
        members={membersNeedingBankingData}
        onCancel={() => setShowBankingDataWarningModal(false)}
        onContinue={() => {
          setShowBankingDataWarningModal(false);
          setShowConfirmationModal(true);
        }}
      />
    </>
  );
};

export default RebuildSubscriptionPaymentsModal;
