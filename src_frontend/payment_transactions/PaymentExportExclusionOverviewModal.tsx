import React, { useEffect, useState } from "react";
import { Badge, Form, Modal, Spinner, Table } from "react-bootstrap";
import {
  PaymentExportExclusionPeriodOverview,
  PaymentsApi,
} from "../api-client";
import BootstrapPagination from "../components/pagination/BootstrapPagination.tsx";
import TapirHelpButton from "../components/TapirHelpButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import PaymentExportExclusionExplanation from "../member_profile/payment_export_exclusion/PaymentExportExclusionExplanation.tsx";
import { ToastData } from "../types/ToastData.ts";
import { toApiDate } from "../utils/apiDate.ts";
import { formatDateMonthAndYear } from "../utils/formatDateMonthAndYear.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import { DEFAULT_PAGE_SIZE } from "../utils/pagination.ts";

interface PaymentExportExclusionOverviewModalProps {
  show: boolean;
  onHide: () => void;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

function buildStatusBadge(period: PaymentExportExclusionPeriodOverview) {
  if (period.isActive) {
    return <Badge bg={"success"}>aktiv</Badge>;
  }
  if (period.startDate > toApiDate(new Date())) {
    return <Badge bg={"info"}>geplant</Badge>;
  }
  return <Badge bg={"secondary"}>abgelaufen</Badge>;
}

const PaymentExportExclusionOverviewModal: React.FC<
  PaymentExportExclusionOverviewModalProps
> = ({ show, onHide, setToastDatas }) => {
  const api = useApi(PaymentsApi, "unused");
  const [loading, setLoading] = useState(true);
  const [includeExpired, setIncludeExpired] = useState(false);
  const [periods, setPeriods] = useState<
    PaymentExportExclusionPeriodOverview[]
  >([]);
  const [currentPage, setCurrentPage] = useState(0);
  const [totalNumberOfPeriods, setTotalNumberOfPeriods] = useState(0);

  useEffect(() => {
    if (!show) return;

    setLoading(true);
    api
      .paymentsApiPaymentExportExclusionPeriodsOverviewList({
        includeExpired: includeExpired,
        limit: DEFAULT_PAGE_SIZE,
        offset: currentPage * DEFAULT_PAGE_SIZE,
      })
      .then((response) => {
        setPeriods(response.results);
        setTotalNumberOfPeriods(response.count);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Ausschlüsse vom Zahlungsexport",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }, [show, includeExpired, currentPage]);

  function buildTable() {
    if (periods.length === 0) {
      return <p className={"mb-0"}>Keine Zeiträume eingetragen.</p>;
    }

    return (
      <Table responsive hover striped bordered className={"mb-0"}>
        <thead>
          <tr>
            <th>Mitgliedsnummer</th>
            <th>Name</th>
            <th>Zeitraum</th>
            <th>Kommentar</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {periods.map((period) => (
            <tr key={period.id}>
              <td>
                <a href={period.memberUrl}>{period.memberNo ?? "-"}</a>
              </td>
              <td>
                {period.firstName} {period.lastName}
              </td>
              <td>
                {formatDateMonthAndYear(period.startDate)} –{" "}
                {period.endDate
                  ? formatDateMonthAndYear(period.endDate)
                  : "unbefristet"}
              </td>
              <td style={{ whiteSpace: "pre-line" }}>{period.comment}</td>
              <td>{buildStatusBadge(period)}</td>
            </tr>
          ))}
        </tbody>
      </Table>
    );
  }

  return (
    <Modal show={show} onHide={onHide} centered={true} size={"lg"}>
      <Modal.Header closeButton>
        <div
          className={
            "d-flex flex-row gap-2 align-items-center justify-content-between"
          }
          style={{ width: "100%" }}
        >
          <Modal.Title>
            Vom Zahlungsexport ausgeschlossene Mitglieder
          </Modal.Title>
          <TapirHelpButton
            text={
              <div className={"d-flex flex-column gap-2"}>
                <PaymentExportExclusionExplanation />
                <p className={"mb-0"}>
                  Um die Ausschlüsse eines Mitglieds zu ändern, öffne sein
                  Profil, Karte „Bankverbindung“.
                </p>
              </div>
            }
          />
        </div>
      </Modal.Header>
      <Modal.Body className={"d-flex flex-column gap-3"}>
        <Form.Switch
          id={"paymentExportExclusionOverviewIncludeExpired"}
          label={"Abgelaufene Zeiträume anzeigen"}
          checked={includeExpired}
          onChange={(event) => {
            setIncludeExpired(event.target.checked);
            setCurrentPage(0);
          }}
        />
        {loading ? <Spinner /> : buildTable()}
      </Modal.Body>
      {totalNumberOfPeriods > DEFAULT_PAGE_SIZE && (
        <Modal.Footer className={"justify-content-center"}>
          <BootstrapPagination
            currentPage={currentPage}
            pageSize={DEFAULT_PAGE_SIZE}
            itemCount={totalNumberOfPeriods}
            goToPage={setCurrentPage}
          />
        </Modal.Footer>
      )}
    </Modal>
  );
};

export default PaymentExportExclusionOverviewModal;
