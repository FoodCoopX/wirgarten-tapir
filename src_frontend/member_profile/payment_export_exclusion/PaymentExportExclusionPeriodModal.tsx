import React, { useEffect, useState } from "react";
import { Alert, Form, Modal, Spinner, Table } from "react-bootstrap";
import { PaymentExportExclusionPeriod, PaymentsApi } from "../../api-client";
import TapirButton from "../../components/TapirButton.tsx";
import TapirHelpButton from "../../components/TapirHelpButton.tsx";
import TapirMonthInput, {
  YearAndMonth,
} from "../../components/TapirMonthInput.tsx";
import { useApi } from "../../hooks/useApi.ts";
import { ToastData } from "../../types/ToastData.ts";
import { fromApiDate, toApiDate } from "../../utils/apiDate.ts";
import { formatDateMonthAndYear } from "../../utils/formatDateMonthAndYear.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import PaymentExportExclusionExplanation from "./PaymentExportExclusionExplanation.tsx";

interface PaymentExportExclusionPeriodModalProps {
  memberId: string;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
  show: boolean;
  onHide: () => void;
}

type ModalContent = "list" | "form" | "confirmDelete";

function toYearAndMonth(date: string): YearAndMonth {
  const dateObject = fromApiDate(date);
  return { year: dateObject.getFullYear(), month: dateObject.getMonth() };
}

function getCurrentYearAndMonth(): YearAndMonth {
  const today = new Date();
  return { year: today.getFullYear(), month: today.getMonth() };
}

function getFirstDayOfMonth(value: YearAndMonth): string {
  return toApiDate(new Date(value.year, value.month, 1));
}

function getLastDayOfMonth(value: YearAndMonth): string {
  return toApiDate(new Date(value.year, value.month + 1, 0));
}

function formatPeriod(period: PaymentExportExclusionPeriod): string {
  const end = period.endDate
    ? formatDateMonthAndYear(period.endDate)
    : "unbefristet";
  return `${formatDateMonthAndYear(period.startDate)} – ${end}`;
}

const PaymentExportExclusionPeriodModal: React.FC<
  PaymentExportExclusionPeriodModalProps
> = ({ memberId, setToastDatas, show, onHide }) => {
  const api = useApi(PaymentsApi);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [periods, setPeriods] = useState<PaymentExportExclusionPeriod[]>([]);
  const [content, setContent] = useState<ModalContent>("list");
  const [selectedPeriod, setSelectedPeriod] =
    useState<PaymentExportExclusionPeriod>();
  const [startMonth, setStartMonth] = useState<YearAndMonth>(
    getCurrentYearAndMonth(),
  );
  const [endMonth, setEndMonth] = useState<YearAndMonth>(
    getCurrentYearAndMonth(),
  );
  const [openEnded, setOpenEnded] = useState(false);
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!show) return;

    setContent("list");
    setLoading(true);

    api
      .paymentsApiPaymentExportExclusionPeriodsList({ memberId: memberId })
      .then(setPeriods)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Ausschlüsse vom Zahlungsexport",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }, [show]);

  function openForm(period: PaymentExportExclusionPeriod | undefined) {
    setSelectedPeriod(period);
    setStartMonth(
      period ? toYearAndMonth(period.startDate) : getCurrentYearAndMonth(),
    );
    setEndMonth(
      period?.endDate
        ? toYearAndMonth(period.endDate)
        : getCurrentYearAndMonth(),
    );
    setOpenEnded(period !== undefined && !period.endDate);
    setComment(period?.comment ?? "");
    setError("");
    setContent("form");
  }

  function openDeleteConfirmation(period: PaymentExportExclusionPeriod) {
    setSelectedPeriod(period);
    setContent("confirmDelete");
  }

  function onSave() {
    if (
      Number.isNaN(startMonth.year) ||
      (!openEnded && Number.isNaN(endMonth.year))
    ) {
      setError("Bitte ein gültiges Jahr angeben");
      return;
    }

    const startDate = getFirstDayOfMonth(startMonth);
    const endDate = openEnded ? null : getLastDayOfMonth(endMonth);

    setSaving(true);

    const request = selectedPeriod
      ? api.paymentsApiPaymentExportExclusionPeriodsUpdate({
          paymentExportExclusionPeriodUpdateRequestRequest: {
            periodId: selectedPeriod.id!,
            startDate: startDate,
            endDate: endDate,
            comment: comment,
          },
        })
      : api.paymentsApiPaymentExportExclusionPeriodsCreate({
          paymentExportExclusionPeriodCreateRequestRequest: {
            memberId: memberId,
            startDate: startDate,
            endDate: endDate,
            comment: comment,
          },
        });

    request
      .then((response) => {
        if (!response.orderConfirmed) {
          setError(response.error ?? "");
          return;
        }
        globalThis.location.reload();
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Speichern des Zeitraums",
          setToastDatas,
        ),
      )
      .finally(() => setSaving(false));
  }

  function onDelete() {
    if (!selectedPeriod) return;

    setSaving(true);

    api
      .paymentsApiPaymentExportExclusionPeriodsDestroy({
        periodId: selectedPeriod.id,
      })
      .then(() => globalThis.location.reload())
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Löschen des Zeitraums",
          setToastDatas,
        ),
      )
      .finally(() => setSaving(false));
  }

  function buildListBody() {
    if (periods.length === 0) {
      return <p className={"mb-0"}>Keine Zeiträume eingetragen.</p>;
    }

    return (
      <Table striped hover responsive className={"mb-0"}>
        <thead>
          <tr>
            <th>Zeitraum</th>
            <th>Kommentar</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {periods.map((period) => (
            <tr key={period.id}>
              <td>{formatPeriod(period)}</td>
              <td style={{ whiteSpace: "pre-line" }}>{period.comment}</td>
              <td>
                <div className={"d-flex gap-2 justify-content-end"}>
                  <TapirButton
                    variant={"outline-primary"}
                    icon={"edit"}
                    size={"sm"}
                    onClick={() => openForm(period)}
                  />
                  <TapirButton
                    variant={"outline-danger"}
                    icon={"delete"}
                    size={"sm"}
                    onClick={() => openDeleteConfirmation(period)}
                  />
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    );
  }

  function buildFormBody() {
    return (
      <div className={"d-flex flex-column gap-2"}>
        <Form.Group>
          <Form.Label>Ab Monat</Form.Label>
          <TapirMonthInput
            value={startMonth}
            onChange={setStartMonth}
            ariaLabel={"Ab Monat"}
          />
        </Form.Group>
        <Form.Group>
          <Form.Label>Bis einschließlich Monat</Form.Label>
          <TapirMonthInput
            value={endMonth}
            onChange={setEndMonth}
            ariaLabel={"Bis einschließlich Monat"}
            disabled={openEnded}
          />
          <Form.Check
            id={"paymentExportExclusionOpenEnded"}
            className={"mt-1"}
            label={"Unbefristet"}
            checked={openEnded}
            onChange={(event) => setOpenEnded(event.target.checked)}
          />
        </Form.Group>
        <Form.Group controlId={"paymentExportExclusionComment"}>
          <Form.Label>Kommentar</Form.Label>
          <Form.Control
            as={"textarea"}
            rows={3}
            value={comment}
            onChange={(event) => setComment(event.target.value)}
          />
        </Form.Group>
        {error && (
          <Alert variant={"danger"} className={"mb-0"}>
            {error}
          </Alert>
        )}
      </div>
    );
  }

  function buildBody() {
    if (loading) {
      return <Spinner />;
    }
    switch (content) {
      case "list":
        return buildListBody();
      case "form":
        return buildFormBody();
      case "confirmDelete":
        return (
          <p className={"mb-0"}>
            Soll der Zeitraum{" "}
            <strong>{selectedPeriod && formatPeriod(selectedPeriod)}</strong>{" "}
            gelöscht werden? Bereits exportierte Zahlungen sind davon nicht
            betroffen.
          </p>
        );
    }
  }

  function buildFooter() {
    switch (content) {
      case "list":
        return (
          <TapirButton
            variant={"outline-primary"}
            icon={"add"}
            text={"Zeitraum hinzufügen"}
            onClick={() => openForm(undefined)}
            disabled={loading}
          />
        );
      case "form":
        return (
          <>
            <TapirButton
              variant={"outline-secondary"}
              text={"Zurück"}
              onClick={() => setContent("list")}
              disabled={saving}
            />
            <TapirButton
              variant={"primary"}
              icon={"save"}
              text={"Speichern"}
              onClick={onSave}
              loading={saving}
            />
          </>
        );
      case "confirmDelete":
        return (
          <>
            <TapirButton
              variant={"outline-secondary"}
              text={"Zurück"}
              onClick={() => setContent("list")}
              disabled={saving}
            />
            <TapirButton
              variant={"danger"}
              icon={"delete"}
              text={"Löschen"}
              onClick={onDelete}
              loading={saving}
            />
          </>
        );
    }
  }

  return (
    <Modal show={show} onHide={onHide} centered size={"lg"}>
      <Modal.Header closeButton>
        <div
          className={
            "d-flex flex-row gap-2 align-items-center justify-content-between"
          }
          style={{ width: "100%" }}
        >
          <h5 className={"mb-0"}>Ausschluss vom Zahlungsexport</h5>
          <TapirHelpButton text={<PaymentExportExclusionExplanation />} />
        </div>
      </Modal.Header>
      <Modal.Body>{buildBody()}</Modal.Body>
      <Modal.Footer>{buildFooter()}</Modal.Footer>
    </Modal>
  );
};

export default PaymentExportExclusionPeriodModal;
